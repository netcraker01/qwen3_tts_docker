"""
API Routes - Endpoints REST para Qwen3-TTS Service
"""

import os
import time
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
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

# Usar dependencias globales
from app.dependencies import get_tts_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Directorio para archivos de salida
OUTPUT_DIR = "/app/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


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
        
        # Generar audio
        audio_result = tts_service.generate_custom_voice(
            text=request.text,
            speaker=request.speaker,
            language=request.language,
            instruction=request.instruction
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
        
        # Generar audio
        audio_result = tts_service.generate_voice_design(
            text=request.text,
            voice_description=request.voice_description,
            language=request.language
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
        
        # Generar audio clonado
        audio_result = tts_service.generate_voice_clone(
            text=request.text,
            voice_clone_prompt_id=prompt_id,
            language=request.language
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
    text: str = Form(..., description="Texto a convertir"),
    ref_text: str = Form(..., description="Texto del audio de referencia"),
    language: str = Form(default="Spanish", description="Idioma del texto"),
    output_format: str = Form(default="wav", description="Formato de salida"),
    ref_audio: UploadFile = File(..., description="Archivo de audio de referencia")
):
    """
    Clona voz desde archivo de audio subido.
    """
    try:
        start_time = time.time()
        tts_service = get_tts_service()
        
        # Validar formato del archivo
        allowed_types = ["audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3", "audio/ogg"]
        if ref_audio.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Formato no soportado: {ref_audio.content_type}. Use WAV, MP3 u OGG."
            )
        
        # Leer contenido del archivo
        audio_content = await ref_audio.read()
        
        if len(audio_content) > 10 * 1024 * 1024:  # 10MB max
            raise HTTPException(status_code=400, detail="Archivo demasiado grande (max 10MB)")
        
        # Generar audio clonado (con liberación automática de memoria)
        audio_result = tts_service.generate_voice_clone_from_file(
            text=text,
            ref_audio_file=audio_content,
            ref_text=ref_text,
            language=language
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
    """,
    tags=["Cloned Voices Management"]
)
async def create_cloned_voice(request: CreateClonedVoiceRequest):
    """
    Crea una voz clonada persistente desde URL de audio.
    """
    try:
        tts_service = get_tts_service()
        
        # Crear el prompt de clonación
        prompt_id = tts_service.create_voice_clone_prompt(
            ref_audio_path=request.ref_audio_url,
            ref_text=request.ref_text
        )
        
        # Obtener el objeto prompt real del servicio
        prompt_data = tts_service._voice_clone_prompts.get(prompt_id)
        
        if not prompt_data:
            raise HTTPException(status_code=500, detail="No se pudo crear el prompt de voz")
        
        # Guardar en el VoiceManager
        voice = voice_manager.create_voice(
            name=request.name,
            description=request.description,
            ref_audio_path=request.ref_audio_url,
            ref_text=request.ref_text,
            language=request.language,
            prompt_data=prompt_data
        )
        
        return {
            "success": True,
            "voice": voice.to_dict(),
            "message": f"Voz '{request.name}' creada exitosamente. Use el ID '{voice.id}' para generar audio."
        }
        
    except Exception as e:
        logger.error(f"Error creando voz clonada: {e}")
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
    description="Actualiza el nombre o descripción de una voz clonada.",
    tags=["Cloned Voices Management"]
)
async def update_cloned_voice(voice_id: str, request: UpdateClonedVoiceRequest):
    """
    Actualiza información de una voz clonada.
    """
    voice = voice_manager.update_voice(
        voice_id=voice_id,
        name=request.name,
        description=request.description
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
        
        # Obtener la voz y su prompt
        voice = voice_manager.get_voice(request.voice_id)
        if not voice:
            raise HTTPException(
                status_code=404, 
                detail=f"Voz clonada no encontrada: {request.voice_id}. "
                       f"Cree la voz primero con POST /cloned-voices"
            )
        
        prompt_data = voice_manager.get_prompt(request.voice_id)
        if not prompt_data:
            raise HTTPException(
                status_code=500,
                detail="Prompt de voz no disponible en memoria. Es posible que el servidor se haya reiniciado. Recree la voz."
            )
        
        # Usar el idioma de la voz si no se especificó otro
        language = request.language or voice.language
        
        # Cargar modelo voice_clone si es necesario
        model = tts_service._get_model("voice_clone")
        
        # Generar audio directamente con el prompt guardado
        wavs, sr = model.generate_voice_clone(
            text=request.text,
            language=language,
            voice_clone_prompt=prompt_data
        )
        
        audio_data = wavs[0]
        duration = len(audio_data) / sr
        
        # Crear AudioResult
        from app.services.tts_service import AudioResult
        audio_result = AudioResult(
            audio_data=audio_data,
            sample_rate=sr,
            duration_seconds=duration,
            model_used="1.7B_cloned_voice_reused"
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generando desde voz clonada: {e}")
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
