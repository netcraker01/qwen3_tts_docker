"""
Job Manager - Gestión de trabajos de generación de audio asíncronos.
Permite procesar solicitudes largas sin bloquear al cliente.
"""

import os
import time
import uuid
import asyncio
import logging
from typing import Dict, Optional, Callable, Any, AsyncGenerator, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import threading

logger = logging.getLogger(__name__)


class JobCancellationError(Exception):
    """Excepción lanzada cuando un job es cancelado."""
    pass


class JobStatus(str, Enum):
    """Estados posibles de un job."""
    PENDING = "pending"           # Creado, esperando procesamiento
    PROCESSING = "processing"     # En proceso de generación
    COMPLETED = "completed"       # Completado exitosamente
    FAILED = "failed"             # Falló
    CANCELLED = "cancelled"       # Cancelado por el usuario
    KILLED = "killed"             # Matado forzosamente


@dataclass
class JobProgress:
    """Progreso de un job."""
    stage: str                    # Etapa actual (ej: "loading_model", "generating_audio", "encoding")
    percent: int                  # Porcentaje (0-100)
    message: str                  # Mensaje descriptivo
    timestamp: float = field(default_factory=time.time)


@dataclass
class Job:
    """Representa un trabajo de generación de audio."""
    id: str
    job_type: str                 # Tipo: custom_voice, voice_design, voice_clone
    status: JobStatus
    created_at: float
    updated_at: float
    
    # Datos de entrada
    request_data: Dict[str, Any]
    
    # Progreso
    progress: JobProgress = field(default_factory=lambda: JobProgress(
        stage="created", percent=0, message="Job creado"
    ))
    
    # Resultado
    result: Optional[Dict] = None
    error: Optional[str] = None
    
    # Control de cancelación
    _cancelled: bool = field(default=False)
    _processing_task: Optional[asyncio.Task] = field(default=None)
    
    # Callbacks de progreso
    _progress_callbacks: list = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    def to_dict(self) -> dict:
        """Convierte el job a diccionario."""
        return {
            "id": self.id,
            "type": self.job_type,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "progress": {
                "stage": self.progress.stage,
                "percent": self.progress.percent,
                "message": self.progress.message,
                "timestamp": self.progress.timestamp
            },
            "result": self.result,
            "error": self.error,
            "elapsed_seconds": time.time() - self.created_at
        }
    
    def update_progress(self, stage: str, percent: int, message: str):
        """Actualiza el progreso del job."""
        with self._lock:
            self.progress = JobProgress(
                stage=stage,
                percent=percent,
                message=message,
                timestamp=time.time()
            )
            self.updated_at = time.time()
        
        # Notificar callbacks
        for callback in self._progress_callbacks:
            try:
                callback(self.progress)
            except Exception as e:
                logger.error(f"Error en progress callback: {e}")
    
    def add_progress_callback(self, callback: Callable[[JobProgress], None]):
        """Añade un callback de progreso."""
        with self._lock:
            self._progress_callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable[[JobProgress], None]):
        """Elimina un callback de progreso."""
        with self._lock:
            if callback in self._progress_callbacks:
                self._progress_callbacks.remove(callback)
    
    def is_cancelled(self) -> bool:
        """Verifica si el job ha sido marcado para cancelación."""
        with self._lock:
            return self._cancelled or self.status in [JobStatus.CANCELLED, JobStatus.KILLED]
    
    def request_cancellation(self):
        """Marca el job para ser cancelado."""
        with self._lock:
            self._cancelled = True


class JobManager:
    """
    Gestiona jobs de generación de audio con cola FIFO.
    Implementa el patrón singleton para acceso global.
    """
    _instance: Optional['JobManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, max_jobs: int = 100, cleanup_interval: int = 300, max_concurrent: int = 1):
        """
        Inicializa el JobManager.
        
        Args:
            max_jobs: Máximo número de jobs a mantener en memoria
            cleanup_interval: Intervalo en segundos para limpieza de jobs antiguos
            max_concurrent: Máximo de jobs procesando simultáneamente (1 = secuencial FIFO)
        """
        # Evitar reinicialización del singleton
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        self._jobs: Dict[str, Job] = {}
        self._max_jobs = max_jobs
        self._cleanup_interval = cleanup_interval
        self._max_concurrent = max_concurrent
        self._lock = threading.Lock()
        
        # Cola FIFO para jobs pendientes
        self._queue: Optional[asyncio.Queue] = None
        self._processing_count = 0
        self._queue_lock = None
        self._workers: List[asyncio.Task] = []
        self._workers_started = False
        
        # Iniciar tarea de limpieza en background
        self._cleanup_task = None
        
        logger.info(f"JobManager inicializado (max_jobs={max_jobs}, max_concurrent={max_concurrent})")
    
    def _ensure_queue(self):
        """Asegura que la cola y el lock estén inicializados."""
        if self._queue is None:
            self._queue = asyncio.Queue()
            self._queue_lock = asyncio.Lock()
    
    async def _start_workers(self):
        """Inicia los workers que procesan la cola."""
        if self._workers_started:
            return
        
        self._ensure_queue()
        
        for i in range(self._max_concurrent):
            worker = asyncio.create_task(self._worker_loop(f"worker-{i}"))
            self._workers.append(worker)
            logger.info(f"Worker {i} iniciado")
        
        self._workers_started = True
    
    async def _worker_loop(self, worker_id: str):
        """
        Loop de trabajo que procesa jobs de la cola FIFO.
        
        Args:
            worker_id: Identificador del worker
        """
        logger.info(f"{worker_id}: Esperando jobs...")
        
        while True:
            try:
                # Obtener job de la cola (bloquea hasta que haya uno)
                job, processor = await self._queue.get()
                
                async with self._queue_lock:
                    self._processing_count += 1
                
                logger.info(f"{worker_id}: Procesando job {job.id[:8]}... (cola: {self._queue.qsize()} pendientes)")
                
                try:
                    # Procesar el job
                    await self._process_job_internal(job, processor)
                except Exception as e:
                    logger.error(f"{worker_id}: Error procesando job {job.id}: {e}")
                finally:
                    async with self._queue_lock:
                        self._processing_count -= 1
                    
                    # Marcar como completado en la cola
                    self._queue.task_done()
                    
            except asyncio.CancelledError:
                logger.info(f"{worker_id}: Cancelado")
                break
            except Exception as e:
                logger.error(f"{worker_id}: Error en loop: {e}")
    
    async def _process_job_internal(self, job: Job, processor: Callable):
        """Procesa un job internamente con soporte para cancelación."""
        # Crear la tarea de procesamiento para poder cancelarla
        loop = asyncio.get_event_loop()
        
        async def process_with_cancellation():
            """Wrapper que verifica cancelación durante el procesamiento."""
            # Verificar si fue cancelado antes de empezar
            if job.is_cancelled():
                raise JobCancellationError("Job cancelado antes de iniciar")
            
            job.status = JobStatus.PROCESSING
            job.update_progress("starting", 0, "Iniciando procesamiento...")
            
            # Función de progreso que verifica cancelación
            def progress_callback(stage: str, percent: int, message: str):
                if job.is_cancelled():
                    raise JobCancellationError("Job cancelado durante el procesamiento")
                job.update_progress(stage, percent, message)
            
            # Ejecutar el procesador en thread pool
            result = await loop.run_in_executor(
                None,
                lambda: processor(job, progress_callback)
            )
            
            return result
        
        # Guardar referencia a la tarea para poder cancelarla
        job._processing_task = asyncio.create_task(process_with_cancellation())
        
        try:
            # Esperar a que termine la tarea
            result = await job._processing_task
            
            # Verificar si fue cancelado durante la ejecución
            if job.is_cancelled():
                job.status = JobStatus.KILLED
                job.error = "Job cancelado durante el procesamiento"
                job.update_progress("killed", 0, "Job cancelado")
                logger.info(f"Job cancelado: {job.id}")
                return
            
            # Marcar como completado
            job.result = result
            job.status = JobStatus.COMPLETED
            job.update_progress("completed", 100, "Procesamiento completado")
            logger.info(f"Job completado: {job.id}")
            
        except asyncio.CancelledError:
            # Job fue cancelado externamente (vía kill_job)
            job.status = JobStatus.KILLED
            job.error = "Job matado por el usuario"
            job.update_progress("killed", 0, "Job matado")
            logger.info(f"Job matado: {job.id}")
            
        except JobCancellationError as e:
            # Job fue cancelado durante el procesamiento
            job.status = JobStatus.CANCELLED
            job.error = str(e)
            job.update_progress("cancelled", 0, "Job cancelado")
            logger.info(f"Job cancelado: {job.id} - {e}")
            
        except Exception as e:
            logger.error(f"Error procesando job {job.id}: {e}")
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.update_progress("error", 0, f"Error: {str(e)}")
        finally:
            job._processing_task = None
    
    def create_job(self, job_type: str, request_data: Dict[str, Any]) -> Job:
        """
        Crea un nuevo job.
        
        Args:
            job_type: Tipo de job (custom_voice, voice_design, voice_clone)
            request_data: Datos de la solicitud
        
        Returns:
            El job creado
        """
        job_id = str(uuid.uuid4())
        now = time.time()
        
        job = Job(
            id=job_id,
            job_type=job_type,
            status=JobStatus.PENDING,
            created_at=now,
            updated_at=now,
            request_data=request_data
        )
        
        with self._lock:
            # Limpiar jobs antiguos si estamos al límite
            if len(self._jobs) >= self._max_jobs:
                self._cleanup_old_jobs()
            
            self._jobs[job_id] = job
        
        logger.info(f"Job creado: {job_id} (tipo: {job_type})")
        return job
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Obtiene un job por su ID."""
        return self._jobs.get(job_id)
    
    def list_jobs(self, status: Optional[JobStatus] = None) -> list:
        """Lista todos los jobs, opcionalmente filtrados por estado."""
        jobs = list(self._jobs.values())
        if status:
            jobs = [j for j in jobs if j.status == status]
        return [j.to_dict() for j in jobs]
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancela un job pendiente o en proceso (cancelación suave).
        Para jobs en ejecución, se recomienda usar kill_job().
        """
        job = self._jobs.get(job_id)
        if not job:
            return False
        
        if job.status == JobStatus.PENDING:
            # Si está pendiente, simplemente marcar como cancelado
            job.status = JobStatus.CANCELLED
            job.request_cancellation()
            job.updated_at = time.time()
            logger.info(f"Job cancelado (pendiente): {job_id}")
            return True
        
        if job.status == JobStatus.PROCESSING:
            # Si está en proceso, marcar para cancelación
            job.request_cancellation()
            logger.info(f"Job marcado para cancelación (en ejecución): {job_id}")
            return True
        
        return False
    
    async def kill_job(self, job_id: str, timeout: float = 5.0) -> Dict[str, Any]:
        """
        Mata un job en ejecución o pendiente de forma forzosa.
        
        Args:
            job_id: ID del job a matar
            timeout: Tiempo máximo de espera para que el job termine gracefulmente
            
        Returns:
            Diccionario con el resultado de la operación
        """
        job = self._jobs.get(job_id)
        if not job:
            return {"success": False, "error": f"Job no encontrado: {job_id}"}
        
        # Si ya está en estado final, no hacer nada
        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.KILLED]:
            return {
                "success": False, 
                "error": f"El job ya está en estado final: {job.status.value}",
                "job_status": job.status.value
            }
        
        # Marcar para cancelación
        job.request_cancellation()
        previous_status = job.status
        
        if job.status == JobStatus.PENDING:
            # Si está pendiente, simplemente marcar como killed
            job.status = JobStatus.KILLED
            job.updated_at = time.time()
            job.error = "Job matado por el usuario (estaba en cola)"
            logger.info(f"Job matado (pendiente): {job_id}")
            return {
                "success": True, 
                "message": f"Job {job_id} matado exitosamente (estaba pendiente)",
                "previous_status": previous_status.value,
                "current_status": job.status.value
            }
        
        if job.status == JobStatus.PROCESSING:
            # Si está en ejecución, intentar cancelar la tarea
            if job._processing_task and not job._processing_task.done():
                try:
                    job._processing_task.cancel()
                    # Esperar un poco a que se cancele
                    await asyncio.wait_for(
                        asyncio.shield(job._processing_task), 
                        timeout=timeout
                    )
                except asyncio.CancelledError:
                    logger.info(f"Job {job_id} cancelado correctamente")
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout esperando cancelación del job {job_id}")
                except Exception as e:
                    logger.error(f"Error cancelando job {job_id}: {e}")
            
            # Marcar como killed independientemente del resultado
            job.status = JobStatus.KILLED
            job.updated_at = time.time()
            job.error = "Job matado por el usuario"
            logger.info(f"Job matado (en ejecución): {job_id}")
            return {
                "success": True, 
                "message": f"Job {job_id} matado exitosamente (estaba en ejecución)",
                "previous_status": previous_status.value,
                "current_status": job.status.value
            }
        
        # Si está cancelado, actualizar a killed
        if job.status == JobStatus.CANCELLED:
            job.status = JobStatus.KILLED
            job.updated_at = time.time()
            logger.info(f"Job matado (previamente cancelado): {job_id}")
            return {
                "success": True, 
                "message": f"Job {job_id} matado exitosamente",
                "previous_status": previous_status.value,
                "current_status": job.status.value
            }
        
        return {"success": False, "error": f"Estado no manejado: {job.status.value}"}
    
    def delete_job(self, job_id: str) -> bool:
        """Elimina un job."""
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                logger.info(f"Job eliminado: {job_id}")
                return True
        return False
    
    def _cleanup_old_jobs(self):
        """Limpia jobs antiguos completados, fallidos, cancelados o matados."""
        now = time.time()
        max_age = 3600  # 1 hora
        
        to_delete = []
        for job_id, job in self._jobs.items():
            # Eliminar jobs completados/fallidos/cancelados/killed con más de 1 hora
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.KILLED]:
                if now - job.updated_at > max_age:
                    to_delete.append(job_id)
        
        for job_id in to_delete:
            del self._jobs[job_id]
        
        if to_delete:
            logger.info(f"Limpiados {len(to_delete)} jobs antiguos")
    
    async def process_job(
        self,
        job: Job,
        processor: Callable[[Job, Callable], Any]
    ):
        """
        Procesa un job ejecutando la función processor.
        
        Args:
            job: El job a procesar
            processor: Función que procesa el job. Recibe el job y una función de progreso.
        """
        try:
            job.status = JobStatus.PROCESSING
            job.update_progress("starting", 0, "Iniciando procesamiento...")
            
            # Función de progreso que actualiza el job
            def progress_callback(stage: str, percent: int, message: str):
                job.update_progress(stage, percent, message)
            
            # Ejecutar el procesador
            result = await asyncio.get_event_loop().run_in_executor(
                None,  # ThreadPoolExecutor por defecto
                lambda: processor(job, progress_callback)
            )
            
            # Marcar como completado
            job.result = result
            job.status = JobStatus.COMPLETED
            job.update_progress("completed", 100, "Procesamiento completado")
            logger.info(f"Job completado: {job.id}")
            
        except Exception as e:
            logger.error(f"Error procesando job {job.id}: {e}")
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.update_progress("error", 0, f"Error: {str(e)}")
    
    async def stream_progress(self, job_id: str) -> AsyncGenerator[str, None]:
        """
        Genera un stream de eventos SSE con el progreso del job.
        
        Yields:
            Eventos SSE con el progreso
        """
        job = self._jobs.get(job_id)
        if not job:
            yield f"event: error\ndata: {{'error': 'Job no encontrado'}}\n\n"
            return
        
        # Cola para recibir actualizaciones de progreso
        queue = asyncio.Queue()
        
        def on_progress(progress: JobProgress):
            try:
                asyncio.get_event_loop().call_soon_threadsafe(
                    queue.put_nowait, progress
                )
            except Exception as e:
                logger.error(f"Error enviando progreso a queue: {e}")
        
        # Registrar callback
        job.add_progress_callback(on_progress)
        
        try:
            # Enviar estado inicial
            yield f"event: progress\ndata: {self._progress_to_json(job.progress)}\n\n"
            
            # Esperar actualizaciones hasta que el job termine
            while job.status in [JobStatus.PENDING, JobStatus.PROCESSING]:
                try:
                    progress = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield f"event: progress\ndata: {self._progress_to_json(progress)}\n\n"
                except asyncio.TimeoutError:
                    # Enviar heartbeat para mantener la conexión viva
                    yield f"event: heartbeat\ndata: {{'timestamp': {time.time()}}}\n\n"
                    continue
            
            # Enviar resultado final
            if job.status == JobStatus.COMPLETED:
                result_data = {
                    "status": "completed",
                    "result": job.result
                }
                yield f"event: completed\ndata: {self._dict_to_json(result_data)}\n\n"
            elif job.status == JobStatus.FAILED:
                error_data = {
                    "status": "failed",
                    "error": job.error
                }
                yield f"event: error\ndata: {self._dict_to_json(error_data)}\n\n"
            elif job.status == JobStatus.CANCELLED:
                yield f"event: cancelled\ndata: {{'status': 'cancelled'}}\n\n"
            elif job.status == JobStatus.KILLED:
                yield f"event: killed\ndata: {{'status': 'killed', 'error': '{job.error}'}}\n\n"
                
        finally:
            job.remove_progress_callback(on_progress)
    
    def _progress_to_json(self, progress: JobProgress) -> str:
        """Convierte JobProgress a JSON."""
        import json
        return json.dumps({
            "stage": progress.stage,
            "percent": progress.percent,
            "message": progress.message,
            "timestamp": progress.timestamp
        })
    
    def _dict_to_json(self, data: dict) -> str:
        """Convierte diccionario a JSON."""
        import json
        return json.dumps(data)


# Instancia global del JobManager
job_manager = JobManager()