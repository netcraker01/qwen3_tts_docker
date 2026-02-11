"""
Job Processors - Procesadores de jobs para generación de audio.
Cada tipo de job tiene su propio procesador que maneja el progreso.
"""

import time
import logging
from typing import Callable, Dict, Any

from app.services.job_manager import Job
from app.dependencies import get_tts_service

logger = logging.getLogger(__name__)


def process_custom_voice_job(job: Job, progress_callback: Callable[[str, int, str], None]) -> Dict[str, Any]:
    """
    Procesa un job de Custom Voice.
    
    Args:
        job: El job a procesar
        progress_callback: Función para reportar progreso (stage, percent, message)
    
    Returns:
        Diccionario con el resultado del procesamiento
    """
    from app.schemas.requests import CustomVoiceRequest
    
    data = job.request_data
    tts_service = get_tts_service()
    
    try:
        progress_callback("validating", 5, "Validando parámetros...")
        
        # Crear request para validación
        request = CustomVoiceRequest(**data)
        
        progress_callback("loading_model", 15, "Cargando modelo de Custom Voice...")
        
        progress_callback("preparing", 25, "Preparando generación...")
        
        progress_callback("generating", 50, "Generando audio con voz personalizada...")
        start_time = time.time()
        
        # Generar audio
        audio_result = tts_service.generate_custom_voice(
            text=request.text,
            speaker=request.speaker,
            language=request.language,
            instruction=request.instruction,
            generation_params=request.to_generation_kwargs()
        )
        
        progress_callback("encoding", 80, "Codificando audio a base64...")
        
        # Convertir a base64
        audio_base64 = tts_service.audio_to_base64(audio_result, request.output_format)
        
        processing_time = time.time() - start_time
        
        progress_callback("finalizing", 95, "Finalizando...")
        
        return {
            "success": True,
            "audio_base64": audio_base64,
            "sample_rate": audio_result.sample_rate,
            "duration_seconds": audio_result.duration_seconds,
            "model_used": audio_result.model_used,
            "processing_time_seconds": processing_time
        }
        
    except Exception as e:
        logger.error(f"Error en process_custom_voice_job: {e}")
        raise


def process_voice_design_job(job: Job, progress_callback: Callable[[str, int, str], None]) -> Dict[str, Any]:
    """
    Procesa un job de Voice Design.
    
    Args:
        job: El job a procesar
        progress_callback: Función para reportar progreso
    
    Returns:
        Diccionario con el resultado
    """
    from app.schemas.requests import VoiceDesignRequest
    
    data = job.request_data
    tts_service = get_tts_service()
    
    try:
        progress_callback("validating", 5, "Validando parámetros...")
        
        request = VoiceDesignRequest(**data)
        
        progress_callback("loading_model", 15, "Cargando modelo de Voice Design...")
        
        progress_callback("preparing", 25, "Preparando descripción de voz...")
        
        progress_callback("generating", 50, "Diseñando y generando voz...")
        start_time = time.time()
        
        audio_result = tts_service.generate_voice_design(
            text=request.text,
            voice_description=request.voice_description,
            language=request.language,
            generation_params=request.to_generation_kwargs()
        )
        
        progress_callback("encoding", 80, "Codificando audio...")
        
        audio_base64 = tts_service.audio_to_base64(audio_result, request.output_format)
        
        processing_time = time.time() - start_time
        
        progress_callback("finalizing", 95, "Finalizando...")
        
        return {
            "success": True,
            "audio_base64": audio_base64,
            "sample_rate": audio_result.sample_rate,
            "duration_seconds": audio_result.duration_seconds,
            "model_used": audio_result.model_used,
            "processing_time_seconds": processing_time
        }
        
    except Exception as e:
        logger.error(f"Error en process_voice_design_job: {e}")
        raise


def process_voice_clone_url_job(job: Job, progress_callback: Callable[[str, int, str], None]) -> Dict[str, Any]:
    """
    Procesa un job de Voice Clone desde URL.
    
    Args:
        job: El job a procesar
        progress_callback: Función para reportar progreso
    
    Returns:
        Diccionario con el resultado
    """
    from app.schemas.requests import VoiceCloneRequest
    
    data = job.request_data
    tts_service = get_tts_service()
    
    try:
        progress_callback("validating", 5, "Validando parámetros...")
        
        request = VoiceCloneRequest(**data)
        
        if not request.ref_audio_url:
            raise ValueError("Se requiere ref_audio_url")
        
        progress_callback("loading_model", 15, "Cargando modelo de Voice Clone...")
        
        progress_callback("downloading", 25, "Descargando audio de referencia...")
        
        progress_callback("creating_prompt", 35, "Creando prompt de clonación...")
        
        # Crear prompt de clonación
        prompt_id = tts_service.create_voice_clone_prompt(
            ref_audio_path=request.ref_audio_url,
            ref_text=request.ref_text
        )
        
        progress_callback("generating", 60, "Generando audio clonado...")
        start_time = time.time()
        
        audio_result = tts_service.generate_voice_clone(
            text=request.text,
            voice_clone_prompt_id=prompt_id,
            language=request.language,
            generation_params=request.to_generation_kwargs()
        )
        
        progress_callback("encoding", 85, "Codificando audio...")
        
        audio_base64 = tts_service.audio_to_base64(audio_result, request.output_format)
        
        processing_time = time.time() - start_time
        
        progress_callback("finalizing", 95, "Finalizando...")
        
        return {
            "success": True,
            "audio_base64": audio_base64,
            "sample_rate": audio_result.sample_rate,
            "duration_seconds": audio_result.duration_seconds,
            "model_used": audio_result.model_used,
            "processing_time_seconds": processing_time
        }
        
    except Exception as e:
        logger.error(f"Error en process_voice_clone_url_job: {e}")
        raise


def process_voice_clone_file_job(job: Job, progress_callback: Callable[[str, int, str], None]) -> Dict[str, Any]:
    """
    Procesa un job de Voice Clone desde archivo.
    
    Args:
        job: El job a procesar
        progress_callback: Función para reportar progreso
    
    Returns:
        Diccionario con el resultado
    """
    data = job.request_data
    tts_service = get_tts_service()
    
    try:
        progress_callback("validating", 5, "Validando parámetros...")
        
        # Extraer datos del archivo base64
        ref_audio_base64 = data.get("ref_audio_base64")
        ref_text = data.get("ref_text")
        text = data.get("text")
        language = data.get("language", "Spanish")
        output_format = data.get("output_format", "wav")
        model_size = data.get("model_size", "0.6B")
        generation_params = data.get("generation_params", {})
        
        if not ref_audio_base64:
            raise ValueError("Se requiere ref_audio_base64")
        
        import base64
        
        progress_callback("decoding", 15, "Decodificando audio...")
        
        # Decodificar base64
        try:
            if "," in ref_audio_base64:
                ref_audio_base64 = ref_audio_base64.split(",")[1]
            ref_audio_bytes = base64.b64decode(ref_audio_base64)
        except Exception as e:
            raise ValueError(f"Error decodificando audio base64: {e}")
        
        progress_callback("loading_model", 25, "Cargando modelo de Voice Clone...")
        
        progress_callback("converting", 35, "Convirtiendo audio a formato WAV...")
        
        progress_callback("creating_prompt", 45, "Creando prompt de clonación...")
        
        progress_callback("generating", 65, "Generando audio clonado...")
        start_time = time.time()
        
        audio_result = tts_service.generate_voice_clone_from_file(
            text=text,
            ref_audio_file=ref_audio_bytes,
            ref_text=ref_text,
            language=language,
            model_size=model_size
        )
        
        progress_callback("encoding", 85, "Codificando audio...")
        
        audio_base64 = tts_service.audio_to_base64(audio_result, output_format)
        
        processing_time = time.time() - start_time
        
        progress_callback("finalizing", 95, "Finalizando...")
        
        return {
            "success": True,
            "audio_base64": audio_base64,
            "sample_rate": audio_result.sample_rate,
            "duration_seconds": audio_result.duration_seconds,
            "model_used": audio_result.model_used,
            "processing_time_seconds": processing_time
        }
        
    except Exception as e:
        logger.error(f"Error en process_voice_clone_file_job: {e}")
        raise


def process_cloned_voice_generate_job(job: Job, progress_callback: Callable[[str, int, str], None]) -> Dict[str, Any]:
    """
    Procesa un job de generación desde voz clonada guardada.
    
    Args:
        job: El job a procesar
        progress_callback: Función para reportar progreso
    
    Returns:
        Diccionario con el resultado
    """
    from app.services.voice_manager import VoiceManager
    
    data = job.request_data
    tts_service = get_tts_service()
    voice_manager = VoiceManager(storage_dir="/app/data")
    
    try:
        progress_callback("validating", 5, "Validando parámetros...")
        
        voice_id = data.get("voice_id")
        text = data.get("text")
        language = data.get("language")
        output_format = data.get("output_format", "wav")
        model_size = data.get("model_size", "1.7B")
        use_voice_defaults = data.get("use_voice_defaults", True)
        generation_params = data.get("generation_params", {})
        
        progress_callback("loading_voice", 20, "Cargando voz clonada...")
        
        voice = voice_manager.get_voice(voice_id)
        if not voice:
            raise ValueError(f"Voz clonada no encontrada: {voice_id}")
        
        prompt_data = voice_manager.get_prompt(voice_id)
        if not prompt_data:
            raise ValueError("Prompt de voz no disponible. Recree la voz.")
        
        progress_callback("loading_model", 35, "Cargando modelo...")
        
        language = language or voice.language
        
        # Determinar parámetros de generación
        if use_voice_defaults and voice.generation_params:
            final_generation_params = voice.generation_params
        else:
            final_generation_params = generation_params
        
        progress_callback("preparing", 45, "Preparando generación...")
        
        # Crear prompt temporal
        temp_prompt_id = f"temp_{voice_id}_{int(time.time())}"
        tts_service._voice_clone_prompts[temp_prompt_id] = prompt_data
        
        try:
            progress_callback("generating", 65, "Generando audio...")
            start_time = time.time()
            
            audio_result = tts_service.generate_voice_clone(
                text=text,
                voice_clone_prompt_id=temp_prompt_id,
                language=language,
                model_size=model_size,
                generation_params=final_generation_params
            )
            
            progress_callback("encoding", 85, "Codificando audio...")
            
            audio_base64 = tts_service.audio_to_base64(audio_result, output_format)
            
            processing_time = time.time() - start_time
            
        finally:
            # Limpiar prompt temporal
            if temp_prompt_id in tts_service._voice_clone_prompts:
                del tts_service._voice_clone_prompts[temp_prompt_id]
        
        progress_callback("finalizing", 95, "Finalizando...")
        
        return {
            "success": True,
            "audio_base64": audio_base64,
            "sample_rate": audio_result.sample_rate,
            "duration_seconds": audio_result.duration_seconds,
            "model_used": audio_result.model_used,
            "processing_time_seconds": processing_time
        }
        
    except Exception as e:
        logger.error(f"Error en process_cloned_voice_generate_job: {e}")
        raise


# Mapeo de tipos de job a sus procesadores
JOB_PROCESSORS = {
    "custom_voice": process_custom_voice_job,
    "voice_design": process_voice_design_job,
    "voice_clone_url": process_voice_clone_url_job,
    "voice_clone_file": process_voice_clone_file_job,
    "cloned_voice_generate": process_cloned_voice_generate_job,
}


def get_processor(job_type: str) -> Callable:
    """
    Obtiene el procesador para un tipo de job.
    
    Args:
        job_type: Tipo de job
    
    Returns:
        Función procesadora
    
    Raises:
        ValueError: Si no existe procesador para el tipo de job
    """
    processor = JOB_PROCESSORS.get(job_type)
    if not processor:
        raise ValueError(f"No existe procesador para el tipo de job: {job_type}")
    return processor