"""
Jobs Routes - Endpoints para gestión de jobs asíncronos de generación de audio.

Estos endpoints permiten:
1. Crear jobs de generación de audio asíncronos
2. Consultar el estado de un job
3. Conectarse a un stream SSE para recibir progreso en tiempo real
4. Listar, cancelar y eliminar jobs
"""

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse

from app.schemas.requests import (
    CreateJobRequest,
    CreateJobResponse,
    JobStatusResponse,
    JobListResponse,
    JobInfo,
    JobResultResponse,
    JobCancelResponse,
    JobKillResponse,
    JobDeleteResponse,
    QueueStatusResponse
)
from app.services.job_manager import job_manager, JobStatus
from app.services.job_processors import get_processor

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/jobs",
    response_model=CreateJobResponse,
    summary="Crear job de generación de audio asíncrono",
    description="""
    Crea un nuevo job de generación de audio que se procesará en background.
    
    Los jobs se encolan y se procesan en orden FIFO (primero en entrar, primero en salir).
    Esto garantiza que:
    - Múltiples peticionarios pueden enviar trabajos simultáneamente
    - Los trabajos se ejecutan uno a uno (o con concurrencia controlada)
    - No se sobrecarga el servidor con procesamiento simultáneo
    
    El cliente recibe inmediatamente un job_id y URLs para:
    1. Consultar el estado del job
    2. Conectarse al stream de progreso SSE
    
    Tipos de job soportados:
    - custom_voice: Voz preestablecida (Sohee, Vivian, etc.)
    - voice_design: Diseño de voz por descripción
    - voice_clone_url: Clonación desde URL de audio
    - voice_clone_file: Clonación desde archivo base64
    - cloned_voice_generate: Generar usando voz clonada guardada
    """,
    tags=["Async Jobs"]
)
async def create_job(request: CreateJobRequest):
    """
    Crea un nuevo job de generación de audio y lo encola para procesamiento FIFO.
    """
    try:
        # Asegurar que los workers estén iniciados
        await job_manager._start_workers()
        
        # Crear el job
        job = job_manager.create_job(
            job_type=request.job_type,
            request_data=request.request_data
        )
        
        # Obtener el procesador
        processor = get_processor(request.job_type)
        
        # Encolar el job para procesamiento FIFO
        await job_manager._queue.put((job, processor))
        
        # Obtener posición en la cola
        queue_size = job_manager._queue.qsize()
        
        logger.info(f"Job creado y encolado: {job.id} (posición en cola: {queue_size})")
        
        return CreateJobResponse(
            success=True,
            job_id=job.id,
            job=JobInfo(**job.to_dict()),
            stream_url=f"/api/v1/jobs/{job.id}/stream",
            status_url=f"/api/v1/jobs/{job.id}/status"
        )
        
    except ValueError as e:
        logger.error(f"Error validando job: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creando job: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get(
    "/jobs/queue/status",
    response_model=QueueStatusResponse,
    summary="Estado de la cola de jobs",
    description="""
    Obtiene información sobre el estado actual de la cola de procesamiento.
    Muestra cuántos jobs están pendientes, procesando, y la capacidad del sistema.
    """,
    tags=["Async Jobs"]
)
async def get_queue_status():
    """
    Obtiene el estado de la cola de procesamiento FIFO.
    """
    # Manejar caso cuando la cola no está inicializada
    pending = job_manager._queue.qsize() if job_manager._queue is not None else 0
    processing = job_manager._processing_count
    max_concurrent = job_manager._max_concurrent
    
    # Contar jobs por estado
    all_jobs = job_manager.list_jobs()
    completed = len([j for j in all_jobs if j['status'] == 'completed'])
    failed = len([j for j in all_jobs if j['status'] == 'failed'])
    
    return {
        "queue": {
            "pending": pending,
            "processing": processing,
            "max_concurrent": max_concurrent
        },
        "jobs": {
            "total": len(all_jobs),
            "completed": completed,
            "failed": failed
        },
        "system_status": "busy" if processing >= max_concurrent else "available"
    }


@router.get(
    "/jobs/{job_id}/status",
    response_model=JobStatusResponse,
    summary="Obtener estado de un job",
    description="Retorna el estado actual y progreso de un job específico.",
    tags=["Async Jobs"]
)
async def get_job_status(job_id: str):
    """
    Obtiene el estado de un job.
    """
    job = job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job no encontrado: {job_id}")
    
    return JobStatusResponse(
        job=JobInfo(**job.to_dict())
    )


@router.get(
    "/jobs/{job_id}/stream",
    summary="Stream SSE de progreso del job",
    description="""
    Conecta a un stream Server-Sent Events (SSE) para recibir actualizaciones
    de progreso en tiempo real del job.
    
    El stream envía eventos:
    - progress: Actualización de progreso (stage, percent, message)
    - heartbeat: Ping cada segundo para mantener la conexión viva
    - completed: Job completado exitosamente (incluye resultado)
    - error: Error durante el procesamiento
    - cancelled: Job cancelado suavemente
    - killed: Job matado forzosamente
    
    Ejemplo de uso con JavaScript:
    ```javascript
    const eventSource = new EventSource('/api/v1/jobs/{job_id}/stream');
    
    eventSource.addEventListener('progress', (e) => {
        const data = JSON.parse(e.data);
        console.log(`${data.percent}% - ${data.message}`);
    });
    
    eventSource.addEventListener('completed', (e) => {
        const data = JSON.parse(e.data);
        console.log('Audio generado:', data.result);
        eventSource.close();
    });
    
    eventSource.addEventListener('error', (e) => {
        console.error('Error:', e.data);
        eventSource.close();
    });
    ```
    """,
    tags=["Async Jobs"],
    responses={
        200: {
            "description": "Stream de eventos SSE",
            "content": {
                "text/event-stream": {
                    "schema": {"type": "string"},
                    "example": """event: progress\ndata: {"stage": "generating", "percent": 50, "message": "Generando audio..."}\n\nevent: completed\ndata: {"result": {"audio_base64": "...", "duration_seconds": 3.5}}\n\n"""
                }
            }
        },
        404: {"description": "Job no encontrado"}
    }
)
async def stream_job_progress(job_id: str):
    """
    Stream de progreso del job usando Server-Sent Events.
    """
    job = job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job no encontrado: {job_id}")
    
    async def event_generator():
        """Generador de eventos SSE."""
        async for event in job_manager.stream_progress(job_id):
            yield event
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Deshabilitar buffering de nginx
        }
    )


@router.get(
    "/jobs",
    response_model=JobListResponse,
    summary="Listar todos los jobs",
    description="Retorna la lista de todos los jobs activos y recientes.",
    tags=["Async Jobs"]
)
async def list_jobs(status: Optional[str] = None):
    """
    Lista todos los jobs, opcionalmente filtrados por estado.
    """
    # Validar estado si se proporciona
    job_status = None
    if status:
        try:
            job_status = JobStatus(status)
        except ValueError:
            valid_statuses = [s.value for s in JobStatus]
            raise HTTPException(
                status_code=400,
                detail=f"Estado inválido: {status}. Opciones válidas: {valid_statuses}"
            )
    
    jobs = job_manager.list_jobs(status=job_status)
    
    return JobListResponse(
        jobs=[JobInfo(**job) for job in jobs],
        total=len(jobs)
    )


@router.post(
    "/jobs/{job_id}/cancel",
    response_model=JobCancelResponse,
    summary="Cancelar un job (suave)",
    description="""
    Cancela un job que está pendiente o en proceso.
    
    Para jobs en ejecución, esto marca el job para cancelación pero no lo detiene inmediatamente.
    El job se detendrá en el próximo punto de verificación de cancelación.
    
    Para una cancelación forzosa inmediata, use el endpoint /kill.
    """,
    tags=["Async Jobs"]
)
async def cancel_job(job_id: str):
    """
    Cancela un job de forma suave.
    """
    success = job_manager.cancel_job(job_id)
    
    if not success:
        job = job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job no encontrado: {job_id}")
        else:
            raise HTTPException(
                status_code=400,
                detail=f"No se puede cancelar el job. Estado actual: {job.status.value}"
            )
    
    job = job_manager.get_job(job_id)
    return JobCancelResponse(
        success=True,
        message=f"Job {job_id} marcado para cancelación",
        job_status=job.status.value if job else "unknown"
    )


@router.post(
    "/jobs/{job_id}/kill",
    response_model=JobKillResponse,
    summary="Matar un job (forzoso)",
    description="""
    Mata un job de forma forzosa, deteniéndolo inmediatamente.
    
    Este endpoint intenta:
    1. Cancelar la tarea asyncio del job si está en ejecución
    2. Marcar el job como 'killed'
    
    Funciona para jobs en cualquier estado:
    - **PENDING**: Se marca como killed y se elimina de la cola
    - **PROCESSING**: Se intenta cancelar la tarea y se marca como killed
    - **CANCELLED**: Se actualiza a killed
    
    Nota: Los jobs que están procesando audio en el modelo de ML pueden tardar
    unos segundos en detenerse completamente debido a la naturaleza del procesamiento.
    """,
    tags=["Async Jobs"]
)
async def kill_job(job_id: str, timeout: float = 5.0):
    """
    Mata un job de forma forzosa.
    
    Args:
        job_id: ID del job a matar
        timeout: Tiempo máximo de espera para cancelación graceful (default: 5s)
    """
    # Obtener el estado anterior antes del kill
    job = job_manager.get_job(job_id)
    previous_status = job.status.value if job else "unknown"
    
    result = await job_manager.kill_job(job_id, timeout=timeout)
    
    if not result.get("success", False):
        error_msg = result.get("error", "Error desconocido")
        job_status = result.get("job_status")
        
        if "no encontrado" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)
    
    # Obtener el estado actual después del kill
    job = job_manager.get_job(job_id)
    current_status = job.status.value if job else "unknown"
    
    return JobKillResponse(
        success=True,
        message=result.get("message", f"Job {job_id} eliminado"),
        job_id=job_id,
        previous_status=previous_status,
        current_status=current_status
    )


@router.delete(
    "/jobs/{job_id}",
    response_model=JobDeleteResponse,
    summary="Eliminar un job",
    description="Elimina permanentemente un job y sus datos asociados.",
    tags=["Async Jobs"]
)
async def delete_job(job_id: str):
    """
    Elimina un job.
    """
    success = job_manager.delete_job(job_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Job no encontrado: {job_id}")
    
    return JobDeleteResponse(
        success=True,
        message=f"Job {job_id} eliminado exitosamente"
    )


@router.get(
    "/jobs/{job_id}/result",
    response_model=JobResultResponse,
    summary="Obtener resultado de un job completado",
    description="""
    Obtiene el resultado de un job que ha sido completado.
    Equivalente a consultar /jobs/{job_id}/status pero solo para jobs completados.
    """,
    tags=["Async Jobs"]
)
async def get_job_result(job_id: str):
    """
    Obtiene el resultado de un job completado.
    """
    job = job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job no encontrado: {job_id}")
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"El job no está completado. Estado actual: {job.status.value}"
        )
    
    return JobResultResponse(
        success=True,
        job_id=job_id,
        result=job.result
    )
