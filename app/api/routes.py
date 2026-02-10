"""
API Routes - Endpoints REST para Qwen3-TTS Service
"""

import os
import time
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Request
from fastapi.responses import JSONResponse, FileResponse

from app.schemas.requests import (
    CustomVoiceRequest,
    VoiceDesignRequest,
    VoiceCloneRequest,
    VoiceCloneFromFileRequest,
    TTSResponse,
    ModelsInfoResponse,
    CreateClonedVoiceRequest,
    UpdateClonedVoiceRequest,
    ClonedVoiceListResponse,
    GenerateFromClonedVoiceRequest,
    AVAILABLE_SPEAKERS,
    SUPPORTED_LANGUAGES,
    MODEL_SIZES,
    OUTPUT_FORMATS
)

from app.services.voice_manager import VoiceManager
from app.services.model_manager import get_model_manager

# Usar dependencias globales
from app.dependencies import get_tts_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Directorio para archivos de salida
OUTPUT_DIR = "/app/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ModelManager para gestión de descargas
model_manager = get_model_manager()


# ============================================================
# ENDPOINTS - ESTADO Y PROGRESO DE MODELOS
# ============================================================

@router.get(
    "/models/status",
    summary="Estado de todos los modelos",
    description="Obtiene el estado de instalación de todos los modelos disponibles.",
    tags=["Models"]
)
async def get_models_status():
    """
    Retorna el estado de todos los modelos.
    """
    return {
        "models": model_manager.get_all_models_status(),
        "cache_dir": str(model_manager.cache_dir)
    }


@router.get(
    "/models/status/{model_size}/{model_type}",
    summary="Estado de un modelo específico",
    description="Obtiene el estado de un modelo específico (ej: 1.7B/voice_clone).",
    tags=["Models"]
)
async def get_model_status(model_size: str, model_type: str):
    """
    Retorna el estado de un modelo específico.
    """
    if model_size not in ["1.7B", "0.6B"]:
        raise HTTPException(status_code=400, detail="model_size debe ser '1.7B' o '0.6B'")
    
    if model_type not in ["voice_clone", "custom_voice", "voice_design"]:
        raise HTTPException(status_code=400, detail="model_type inválido")
    
    return model_manager.get_model_status(model_size, model_type)


@router.post(
    "/models/download/{model_size}/{model_type}",
    summary="Descargar un modelo",
    description="Inicia la descarga de un modelo específico si no está instalado.",
    tags=["Models"]
)
async def download_model(model_size: str, model_type: str):
    """
    Inicia la descarga de un modelo.
    """
    if model_size not in ["1.7B", "0.6B"]:
        raise HTTPException(status_code=400, detail="model_size debe ser '1.7B' o '0.6B'")
    
    if model_type not in ["voice_clone", "custom_voice", "voice_design"]:
        raise HTTPException(status_code=400, detail="model_type inválido")
    
    # Iniciar descarga en background
    def progress_callback(progress):
        logger.info(f"Descarga {progress.model_id}: {progress.progress_percent}% - {progress.current_file}")
    
    success = model_manager.ensure_model_downloaded(model_size, model_type, progress_callback)
    
    if success:
        return {
            "success": True,
            "message": f"Modelo {model_size}/{model_type} descargado correctamente"
        }
    else:
        raise HTTPException(status_code=500, detail="Error descargando el modelo")


@router.get(
    "/health",
    summary="Health check",
    description="Verifica que el servicio está funcionando y retorna información básica.",
    tags=["System"]
)
async def health_check():
    """
    Health check del servicio.
    """
    import torch
    
    # Verificar si los modelos esenciales están disponibles
    voice_clone_status = model_manager.get_model_status("1.7B", "voice_clone")
    
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "cuda_available": torch.cuda.is_available(),
        "models_ready": voice_clone_status["installed"],
        "cache_dir": str(model_manager.cache_dir)
    }


# ============================================================
# ENDPOINTS - CUSTOM VOICE
# ============================================================

@router.post(
    "/tts/custom",
    response_model=TTSResponse,
    summary="Generar voz con personaje preestablecido",
    description="""
    Genera audio de voz usando personajes preestablecidos como Vivian, Ryan, Sohee, etc.
    
    Los speakers disponibles son:
    - Vivian: Voz femenina en chino
    - Serena: Voz femenina
    - Uncle_Fu: Voz masculina madura
    - Dylan: Voz masculina joven
    - Eric: Voz masculina profesional
    - Ryan: Voz masculina en inglés
    - Aiden: Voz masculina versátil
    - Ono_Anna: Voz femenina japonesa
    - Sohee: Voz femenina coreana
    """,
    tags=["Text-to-Speech"]
)
async def generate_custom_voice(request: CustomVoiceRequest):
    """
    Genera voz usando un personaje preestablecido.
    """
    try:
        start_time = time.time()
        tts_service = get_tts_service()
        
        # Generar audio con parámetros de generación
        audio_result = tts_service.generate_custom_voice(
            text=request.text,
            speaker=request.speaker,
            language=request.language,
            instruction=request.instruction,
            generation_params=request.to_generation_kwargs()
        )
        
        # Convertir a base64
        audio_base64 = tts_service.audio_to_base64(audio_result, request.output_format)
        
        processing_time = time.time() - start_time
        
        return TTSResponse(
            success=True,
            audio_base64=audio_base64,
            sample_rate=audio_result.sample_rate,
            duration_seconds=audio_result.duration_seconds,
            model_used=audio_result.model_used,
            processing_time_seconds=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error en custom voice: {e}")
        return TTSResponse(
            success=False,
            error=str(e),
            model_used="custom_voice",
            processing_time_seconds=0
        )


# ============================================================
# ENDPOINTS - VOICE DESIGN
# ============================================================

@router.post(
    "/tts/design",
    response_model=TTSResponse,
    summary="Diseñar voz por descripción",
    description="""
    Crea una voz personalizada mediante descripción de texto en lenguaje natural.
    
    La descripción debe incluir características como:
    - gender: Male/Female
    - pitch: High/Medium/Low/Deep
    - speed: Fast/Moderate/Slow
    - age: Child/Young/Middle-aged/Older
    - emotion: Happy/Sad/Excited/Calm/etc.
    - tone: Formal/Casual/Friendly/Authoritative/etc.
    
    Ejemplo de descripción:
    "gender: Male, pitch: Deep and resonant, speed: Slow and deliberate, 
    age: Middle-aged, emotion: Contemplative, tone: Mysterious"
    """,
    tags=["Text-to-Speech"]
)
async def generate_voice_design(request: VoiceDesignRequest):
    """
    Genera voz mediante descripción de texto.
    """
    try:
        start_time = time.time()
        tts_service = get_tts_service()
        
        # Generar audio con parámetros de generación
        audio_result = tts_service.generate_voice_design(
            text=request.text,
            voice_description=request.voice_description,
            language=request.language,
            generation_params=request.to_generation_kwargs()
        )
        
        # Convertir a base64
        audio_base64 = tts_service.audio_to_base64(audio_result, request.output_format)
        
        processing_time = time.time() - start_time
        
        return TTSResponse(
            success=True,
            audio_base64=audio_base64,
            sample_rate=audio_result.sample_rate,
            duration_seconds=audio_result.duration_seconds,
            model_used=audio_result.model_used,
            processing_time_seconds=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error en voice design: {e}")
        return TTSResponse(
            success=False,
            error=str(e),
            model_used="voice_design",
            processing_time_seconds=0
        )


# ============================================================
# ENDPOINTS - VOICE CLONE
# ============================================================

@router.post(
    "/tts/clone/url",
    response_model=TTSResponse,
    summary="Clonar voz desde URL",
    description="""
    Clona una voz usando un archivo de audio de referencia desde una URL.
    El audio de referencia debe ser claro, sin música de fondo, de 3-10 segundos.
    """,
    tags=["Voice Cloning"]
)
async def clone_voice_from_url(request: VoiceCloneRequest):
    """
    Clona voz desde audio de referencia en URL.
    """
    try:
        if not request.ref_audio_url:
            raise HTTPException(status_code=400, detail="Se requiere ref_audio_url")
        
        start_time = time.time()
        tts_service = get_tts_service()
        
        # Crear prompt de clonación (con liberación de memoria)
        prompt_id = tts_service.create_voice_clone_prompt(
            ref_audio_path=request.ref_audio_url,
            ref_text=request.ref_text
        )
        
        # Generar audio clonado con parámetros de generación
        audio_result = tts_service.generate_voice_clone(
            text=request.text,
            voice_clone_prompt_id=prompt_id,
            language=request.language,
            generation_params=request.to_generation_kwargs()
        )
        
        # Convertir a base64
        audio_base64 = tts_service.audio_to_base64(audio_result, request.output_format)
        
        processing_time = time.time() - start_time
        
        return TTSResponse(
            success=True,
            audio_base64=audio_base64,
            sample_rate=audio_result.sample_rate,
            duration_seconds=audio_result.duration_seconds,
            model_used=audio_result.model_used,
            processing_time_seconds=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error en voice clone URL: {e}")
        return TTSResponse(
            success=False,
            error=str(e),
            model_used="voice_clone",
            processing_time_seconds=0
        )


@router.post(
    "/tts/clone/upload",
    response_model=TTSResponse,
    summary="Clonar voz subiendo archivo",
    description="""
    Clona una voz subiendo directamente un archivo de audio de referencia.
    Formatos soportados: WAV, MP3, OGG.
    El audio debe ser claro, sin música de fondo, de 3-10 segundos.
    """,
    tags=["Voice Cloning"]
)
async def clone_voice_from_upload(
    request: Request,
    text: str = Form(..., description="Texto a convertir"),
    ref_text: str = Form(..., description="Texto del audio de referencia"),
    language: str = Form(default="Spanish", description="Idioma del texto"),
    output_format: str = Form(default="wav", description="Formato de salida"),
    model_size: str = Form(default="1.7B", description="Tamaño del modelo (0.6B o 1.7B)"),
    ref_audio: UploadFile = File(..., description="Archivo de audio de referencia")
):
    """
    Clona voz desde archivo de audio subido.
    """
    try:
        start_time = time.time()
        tts_service = get_tts_service()
        
        logger.info(f"Recibiendo archivo: {ref_audio.filename}, content-type: {ref_audio.content_type}, modelo: {model_size}")
        
        # Leer contenido del archivo
        audio_content = await ref_audio.read()
        file_size = len(audio_content)
        logger.info(f"Archivo leído: {file_size} bytes")
        
        if file_size > 10 * 1024 * 1024:  # 10MB max
            raise HTTPException(status_code=400, detail="Archivo demasiado grande (max 10MB)")
        
        if file_size == 0:
            raise HTTPException(status_code=400, detail="Archivo vacío")
        
        # Generar audio clonado (con liberación automática de memoria)
        # Usar el modelo seleccionado o el default
        audio_result = tts_service.generate_voice_clone_from_file(
            text=text,
            ref_audio_file=audio_content,
            ref_text=ref_text,
            language=language,
            model_size=model_size
        )
        
        # Convertir a base64
        audio_base64 = tts_service.audio_to_base64(audio_result, output_format)
        
        processing_time = time.time() - start_time
        
        return TTSResponse(
            success=True,
            audio_base64=audio_base64,
            sample_rate=audio_result.sample_rate,
            duration_seconds=audio_result.duration_seconds,
            model_used=audio_result.model_used,
            processing_time_seconds=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en voice clone upload: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return TTSResponse(
            success=False,
            error=str(e),
            model_used="voice_clone",
            processing_time_seconds=0
        )


# ============================================================
# ENDPOINTS - INFO Y UTILIDADES
# ============================================================

@router.get(
    "/models",
    response_model=ModelsInfoResponse,
    summary="Información de modelos",
    description="Obtiene información sobre los modelos disponibles, speakers, idiomas y estado actual.",
    tags=["Information"]
)
async def get_models_info():
    """
    Retorna información de modelos y configuración.
    """
    import torch
    import os
    
    gpu_info = None
    if torch.cuda.is_available():
        gpu_info = {
            "name": torch.cuda.get_device_name(0),
            "total_memory_gb": round(torch.cuda.get_device_properties(0).total_memory / 1e9, 2),
            "allocated_memory_gb": round(torch.cuda.memory_allocated() / 1e9, 2),
            "reserved_memory_gb": round(torch.cuda.memory_reserved() / 1e9, 2)
        }
    
    return ModelsInfoResponse(
        available_models={
            "1.7B": {
                "custom_voice": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
                "voice_design": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
                "voice_clone": "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
            }
        },
        available_speakers=AVAILABLE_SPEAKERS,
        supported_languages=SUPPORTED_LANGUAGES,
        loaded_models=get_tts_service().get_loaded_models(),
        cuda_available=torch.cuda.is_available(),
        gpu_info=gpu_info
    )


@router.get(
    "/speakers",
    summary="Listar speakers disponibles",
    description="Retorna la lista de personajes preestablecidos disponibles para Custom Voice.",
    tags=["Information"]
)
async def get_speakers():
    """
    Lista speakers disponibles.
    """
    speaker_info = {
        "Vivian": {"gender": "Female", "language": "Chinese", "style": "Natural"},
        "Serena": {"gender": "Female", "language": "English", "style": "Professional"},
        "Uncle_Fu": {"gender": "Male", "language": "Chinese", "style": "Mature"},
        "Dylan": {"gender": "Male", "language": "English", "style": "Young"},
        "Eric": {"gender": "Male", "language": "English", "style": "Professional"},
        "Ryan": {"gender": "Male", "language": "English", "style": "Conversational"},
        "Aiden": {"gender": "Male", "language": "English", "style": "Versatile"},
        "Ono_Anna": {"gender": "Female", "language": "Japanese", "style": "Anime"},
        "Sohee": {"gender": "Female", "language": "Korean", "style": "Natural"}
    }
    
    return {
        "speakers": AVAILABLE_SPEAKERS,
        "details": {k: v for k, v in speaker_info.items() if k in AVAILABLE_SPEAKERS}
    }


@router.get(
    "/languages",
    summary="Listar idiomas soportados",
    description="Retorna la lista de idiomas soportados por el servicio.",
    tags=["Information"]
)
async def get_languages():
    """
    Lista idiomas soportados.
    """
    return {
        "languages": SUPPORTED_LANGUAGES,
        "notes": "Use 'Auto' para detección automática del idioma"
    }


@router.post(
    "/tts/custom/file",
    response_model=TTSResponse,
    summary="Generar voz y descargar archivo",
    description="""
    Genera voz con personaje preestablecido y retorna el archivo de audio directamente.
    El archivo se guarda temporalmente y se proporciona una URL de descarga.
    """,
    tags=["Text-to-Speech"]
)
async def generate_custom_voice_file(request: CustomVoiceRequest):
    """
    Genera voz y guarda en archivo para descarga.
    """
    try:
        start_time = time.time()
        tts_service = get_tts_service()
        
        # Generar audio
        audio_result = tts_service.generate_custom_voice(
            text=request.text,
            speaker=request.speaker,
            language=request.language,
            instruction=request.instruction
        )
        
        # Guardar en archivo
        filename = f"custom_{request.speaker}_{int(time.time())}.{request.output_format}"
        output_path = os.path.join(OUTPUT_DIR, filename)
        
        saved_path = tts_service.save_audio(
            audio_result=audio_result,
            output_path=output_path,
            output_format=request.output_format
        )
        
        processing_time = time.time() - start_time
        
        return TTSResponse(
            success=True,
            audio_url=f"/api/v1/download/{filename}",
            sample_rate=audio_result.sample_rate,
            duration_seconds=audio_result.duration_seconds,
            model_used=audio_result.model_used,
            processing_time_seconds=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error en custom voice file: {e}")
        return TTSResponse(
            success=False,
            error=str(e),
            model_used="custom_voice",
            processing_time_seconds=0
        )


@router.get(
    "/download/{filename}",
    summary="Descargar archivo de audio",
    description="Descarga un archivo de audio generado previamente.",
    tags=["Utilities"]
)
async def download_file(filename: str):
    """
    Descarga archivo de audio generado.
    """
    file_path = os.path.join(OUTPUT_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="audio/wav" if filename.endswith(".wav") else "audio/mpeg"
    )


# ============================================================
# ENDPOINTS - GESTIÓN DE VOCES CLONADAS PERSISTENTES
# ============================================================

# Instancia global del VoiceManager
voice_manager = VoiceManager(storage_dir="/app/data")


@router.post(
    "/cloned-voices",
    response_model=dict,
    summary="Crear voz clonada persistente",
    description="""
    Crea una voz clonada y la guarda para uso futuro.
    La voz se almacena en disco y puede reusarse múltiples veces.
    Acepta URL de audio o data URL base64 (data:audio/wav;base64,...).
    """,
    tags=["Cloned Voices Management"]
)
async def create_cloned_voice(request: CreateClonedVoiceRequest):
    """
    Crea una voz clonada persistente desde URL de audio o data URL base64.
    """
    try:
        tts_service = get_tts_service()
        
        ref_audio_url = request.ref_audio_url
        
        # Si es data URL base64, guardar temporalmente
        if ref_audio_url.startswith("data:audio") and ";base64," in ref_audio_url:
            logger.info("Detectado data URL base64, procesando...")
            import base64
            import tempfile
            import os
            
            # Extraer la parte base64
            base64_data = ref_audio_url.split(";base64,")[1]
            audio_bytes = base64.b64decode(base64_data)
            
            # Guardar temporalmente
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_bytes)
                ref_audio_url = tmp.name
                logger.info(f"Audio base64 guardado temporalmente en: {ref_audio_url}")
        
        # Crear el prompt de clonación
        prompt_id = tts_service.create_voice_clone_prompt(
            ref_audio_path=ref_audio_url,
            ref_text=request.ref_text
        )
        
        # Obtener el objeto prompt real del servicio
        prompt_data = tts_service._voice_clone_prompts.get(prompt_id)
        
        if not prompt_data:
            raise HTTPException(status_code=500, detail="No se pudo crear el prompt de voz")
        
        # Guardar en el VoiceManager (usar una URL placeholder ya que el audio ya se procesó)
        # Guardar los parámetros de generación por defecto
        voice = voice_manager.create_voice(
            name=request.name,
            description=request.description,
            ref_audio_path="internal://voice_prompt/" + prompt_id,  # URL interna
            ref_text=request.ref_text,
            language=request.language,
            prompt_data=prompt_data,
            generation_params=request.to_generation_kwargs()
        )
        
        # Limpiar archivo temporal si era data URL
        if ref_audio_url.startswith("/tmp"):
            try:
                os.remove(ref_audio_url)
                logger.info(f"Archivo temporal eliminado: {ref_audio_url}")
            except:
                pass
        
        return {
            "success": True,
            "voice": voice.to_dict(),
            "message": f"Voz '{request.name}' creada exitosamente. Use el ID '{voice.id}' para generar audio."
        }
        
    except Exception as e:
        logger.error(f"Error creando voz clonada: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/cloned-voices",
    response_model=dict,
    summary="Listar voces clonadas",
    description="Obtiene la lista de todas las voces clonadas almacenadas.",
    tags=["Cloned Voices Management"]
)
async def list_cloned_voices():
    """
    Lista todas las voces clonadas guardadas.
    """
    voices = voice_manager.list_voices()
    return {
        "voices": voices,
        "total": len(voices)
    }


@router.get(
    "/cloned-voices/{voice_id}",
    response_model=dict,
    summary="Obtener información de una voz clonada",
    description="Obtiene los detalles de una voz clonada específica.",
    tags=["Cloned Voices Management"]
)
async def get_cloned_voice(voice_id: str):
    """
    Obtiene información de una voz clonada.
    """
    voice = voice_manager.get_voice(voice_id)
    if not voice:
        raise HTTPException(status_code=404, detail=f"Voz no encontrada: {voice_id}")
    
    return {
        "voice": voice.to_dict()
    }


@router.put(
    "/cloned-voices/{voice_id}",
    response_model=dict,
    summary="Actualizar voz clonada",
    description="Actualiza el nombre, descripción o parámetros de generación de una voz clonada.",
    tags=["Cloned Voices Management"]
)
async def update_cloned_voice(voice_id: str, request: UpdateClonedVoiceRequest):
    """
    Actualiza información de una voz clonada.
    """
    voice = voice_manager.update_voice(
        voice_id=voice_id,
        name=request.name,
        description=request.description,
        generation_params=request.generation_params
    )
    
    if not voice:
        raise HTTPException(status_code=404, detail=f"Voz no encontrada: {voice_id}")
    
    return {
        "success": True,
        "voice": voice.to_dict(),
        "message": "Voz actualizada exitosamente"
    }


@router.delete(
    "/cloned-voices/{voice_id}",
    response_model=dict,
    summary="Eliminar voz clonada",
    description="Elimina permanentemente una voz clonada almacenada.",
    tags=["Cloned Voices Management"]
)
async def delete_cloned_voice(voice_id: str):
    """
    Elimina una voz clonada.
    """
    deleted = voice_manager.delete_voice(voice_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Voz no encontrada: {voice_id}")
    
    return {
        "success": True,
        "message": f"Voz '{voice_id}' eliminada exitosamente"
    }


@router.post(
    "/tts/cloned-voice/generate",
    response_model=TTSResponse,
    summary="Generar audio usando voz clonada guardada",
    description="""
    Genera audio de texto usando una voz clonada previamente guardada.
    Es más rápido que crear el clone desde cero cada vez.
    """,
    tags=["Cloned Voices Management"]
)
async def generate_from_cloned_voice(request: GenerateFromClonedVoiceRequest):
    """
    Genera audio usando una voz clonada almacenada.
    """
    try:
        start_time = time.time()
        tts_service = get_tts_service()
        
        logger.info(f"=== INICIO generate_from_cloned_voice ===")
        logger.info(f"Voice ID: {request.voice_id}")
        logger.info(f"Model size: {request.model_size}")
        logger.info(f"Language: {request.language}")
        logger.info(f"Text length: {len(request.text)}")
        
        # Obtener la voz y su prompt
        voice = voice_manager.get_voice(request.voice_id)
        logger.info(f"Voice encontrada: {voice is not None}")
        
        if not voice:
            raise HTTPException(
                status_code=404, 
                detail=f"Voz clonada no encontrada: {request.voice_id}. "
                       f"Cree la voz primero con POST /cloned-voices"
            )
        
        prompt_data = voice_manager.get_prompt(request.voice_id)
        logger.info(f"Prompt data encontrado: {prompt_data is not None}")
        logger.info(f"Tipo de prompt_data: {type(prompt_data)}")
        
        if not prompt_data:
            raise HTTPException(
                status_code=500,
                detail="Prompt de voz no disponible en memoria. Es posible que el servidor se haya reiniciado. Recree la voz."
            )
        
        # Usar el idioma de la voz si no se especificó otro
        language = request.language or voice.language
        logger.info(f"Language final: {language}")
        
        # Determinar tamaño del modelo
        model_size = request.model_size or "1.7B"
        logger.info(f"Model size final: {model_size}")
        
        # LIMPIEZA AGRESIVA antes de empezar
        logger.info("Iniciando limpieza de memoria...")
        tts_service._immediate_cleanup()
        logger.info("Limpieza completada")
        
        # Crear un prompt_id temporal para reusar el prompt existente
        temp_prompt_id = f"temp_{request.voice_id}_{int(time.time())}"
        logger.info(f"Temp prompt ID: {temp_prompt_id}")
        
        tts_service._voice_clone_prompts[temp_prompt_id] = prompt_data
        logger.info(f"Prompt guardado en servicio. Total prompts: {len(tts_service._voice_clone_prompts)}")
        
        try:
            # Determinar parámetros de generación
            logger.info(f"Request use_voice_defaults: {request.use_voice_defaults}")
            logger.info(f"Voice generation_params: {voice.generation_params}")
            
            if request.use_voice_defaults and voice.generation_params:
                # Usar los parámetros guardados con la voz
                generation_params = voice.generation_params
                logger.info(f"✅ Usando parámetros GUARDADOS con la voz: {generation_params}")
            else:
                # Usar los parámetros de esta petición
                generation_params = request.to_generation_kwargs()
                logger.info(f"✅ Usando parámetros de la PETICIÓN: {generation_params}")
            
            # Usar el método del servicio que ya maneja limpieza automática
            logger.info("Llamando a generate_voice_clone...")
            audio_result = tts_service.generate_voice_clone(
                text=request.text,
                voice_clone_prompt_id=temp_prompt_id,
                language=language,
                model_size=model_size,
                generation_params=generation_params
            )
            logger.info(f"Audio generado exitosamente: {audio_result.duration_seconds}s")
            
            # Convertir a base64
            logger.info("Convirtiendo a base64...")
            audio_base64 = tts_service.audio_to_base64(audio_result, request.output_format)
            logger.info("Conversión completada")
            
            processing_time = time.time() - start_time
            logger.info(f"=== FIN generate_from_cloned_voice - ÉXITO ===")
            
            return TTSResponse(
                success=True,
                audio_base64=audio_base64,
                sample_rate=audio_result.sample_rate,
                duration_seconds=audio_result.duration_seconds,
                model_used=audio_result.model_used,
                processing_time_seconds=processing_time
            )
            
        finally:
            # Limpiar prompt temporal
            logger.info("Limpiando prompt temporal...")
            if temp_prompt_id in tts_service._voice_clone_prompts:
                del tts_service._voice_clone_prompts[temp_prompt_id]
                logger.info("Prompt temporal eliminado")
        
    except HTTPException:
        logger.error("HTTPException capturada")
        raise
    except Exception as e:
        logger.error(f"=== ERROR en generate_from_cloned_voice: {e} ===")
        import traceback
        logger.error(traceback.format_exc())
        return TTSResponse(
            success=False,
            error=str(e),
            model_used="cloned_voice_reused",
            processing_time_seconds=0
        )


@router.get(
    "/cloned-voices/stats",
    response_model=dict,
    summary="Estadísticas de voces clonadas",
    description="Obtiene estadísticas de uso de las voces clonadas.",
    tags=["Cloned Voices Management"]
)
async def get_cloned_voices_stats():
    """
    Obtiene estadísticas de las voces clonadas.
    """
    stats = voice_manager.get_voice_stats()
    return stats
