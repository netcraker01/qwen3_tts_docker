"""
Pydantic models for API requests and responses.
"""

from typing import Optional, Literal, List
from pydantic import BaseModel, Field, validator

# ============================================================
# ENUMERACIONES Y CONSTANTES
# ============================================================

SUPPORTED_LANGUAGES = [
    "Auto", "Spanish", "English", "Chinese", "Japanese", "Korean", 
    "German", "French", "Russian", "Portuguese", "Italian"
]

AVAILABLE_SPEAKERS = [
    "Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric", 
    "Ryan", "Aiden", "Ono_Anna", "Sohee"
]

MODEL_SIZES = ["0.6B", "1.7B"]

OUTPUT_FORMATS = ["wav", "mp3", "ogg", "opus"]

# ============================================================
# REQUESTS - CUSTOM VOICE
# ============================================================

class CustomVoiceRequest(BaseModel):
    """
    Request para generar voz usando voces preestablecidas.
    """
    text: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Texto a convertir en voz",
        example="¡Hola! Esta es una demostración de Qwen3-TTS."
    )
    speaker: str = Field(
        ...,
        description="Nombre del personaje preestablecido",
        example="Sohee"
    )
    language: str = Field(
        default="Auto",
        description="Idioma del texto (Auto detecta automáticamente)",
        example="Spanish"
    )
    instruction: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Instrucción para modificar emoción/estilo (ej: 'Feliz y enérgica')",
        example="Feliz y enérgica"
    )
    output_format: str = Field(
        default="wav",
        description="Formato de salida del audio",
        example="wav"
    )
    
    @validator('speaker')
    def validate_speaker(cls, v):
        if v not in AVAILABLE_SPEAKERS:
            raise ValueError(f"Speaker '{v}' no disponible. Opciones: {AVAILABLE_SPEAKERS}")
        return v
    
    @validator('language')
    def validate_language(cls, v):
        if v not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Idioma '{v}' no soportado. Opciones: {SUPPORTED_LANGUAGES}")
        return v
    
    @validator('output_format')
    def validate_format(cls, v):
        if v not in OUTPUT_FORMATS:
            raise ValueError(f"Formato '{v}' no soportado. Opciones: {OUTPUT_FORMATS}")
        return v


# ============================================================
# REQUESTS - VOICE DESIGN
# ============================================================

class VoiceDesignRequest(BaseModel):
    """
    Request para crear voz mediante descripción de texto.
    """
    text: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Texto a convertir en voz",
        example="No puedo creer que finalmente llegamos a la cima de la montaña."
    )
    voice_description: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Descripción detallada de la voz deseada en inglés",
        example="""gender: Male
pitch: Deep and resonant with subtle downward inflections
speed: Deliberately slow with extended pauses
volume: Moderate to soft
age: Middle-aged to older adult
emotion: Contemplative and intriguing
tone: Mysterious and atmospheric"""
    )
    language: str = Field(
        default="Spanish",
        description="Idioma del texto a generar",
        example="Spanish"
    )
    output_format: str = Field(
        default="wav",
        description="Formato de salida del audio",
        example="wav"
    )
    
    @validator('language')
    def validate_language(cls, v):
        if v not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Idioma '{v}' no soportado. Opciones: {SUPPORTED_LANGUAGES}")
        return v
    
    @validator('output_format')
    def validate_format(cls, v):
        if v not in OUTPUT_FORMATS:
            raise ValueError(f"Formato '{v}' no soportado. Opciones: {OUTPUT_FORMATS}")
        return v


# ============================================================
# REQUESTS - VOICE CLONE
# ============================================================

class VoiceCloneRequest(BaseModel):
    """
    Request para clonar voz desde audio de referencia.
    """
    text: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Texto a convertir en voz clonada",
        example="Esto es lo que sucede cuando clonas una voz."
    )
    ref_audio_url: Optional[str] = Field(
        default=None,
        description="URL del audio de referencia",
        example="https://ejemplo.com/audio.wav"
    )
    ref_text: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Texto correspondiente al audio de referencia",
        example="Hola, esta es una prueba de mi voz..."
    )
    language: str = Field(
        default="Spanish",
        description="Idioma del texto a generar",
        example="Spanish"
    )
    output_format: str = Field(
        default="wav",
        description="Formato de salida del audio",
        example="wav"
    )
    
    @validator('language')
    def validate_language(cls, v):
        if v not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Idioma '{v}' no soportado. Opciones: {SUPPORTED_LANGUAGES}")
        return v
    
    @validator('output_format')
    def validate_format(cls, v):
        if v not in OUTPUT_FORMATS:
            raise ValueError(f"Formato '{v}' no soportado. Opciones: {OUTPUT_FORMATS}")
        return v


class VoiceCloneFromFileRequest(BaseModel):
    """
    Request para clonar voz subiendo un archivo de audio.
    """
    text: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Texto a convertir en voz clonada"
    )
    ref_text: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Texto correspondiente al audio de referencia"
    )
    language: str = Field(
        default="Spanish",
        description="Idioma del texto a generar"
    )
    output_format: str = Field(
        default="wav",
        description="Formato de salida del audio"
    )


# ============================================================
# RESPONSES
# ============================================================

class TTSResponse(BaseModel):
    """
    Response estándar para generación de voz.
    """
    success: bool = Field(description="Indica si la generación fue exitosa")
    audio_base64: Optional[str] = Field(
        default=None, 
        description="Audio codificado en base64"
    )
    audio_url: Optional[str] = Field(
        default=None,
        description="URL para descargar el audio generado"
    )
    sample_rate: int = Field(
        default=24000,
        description="Frecuencia de muestreo del audio"
    )
    duration_seconds: Optional[float] = Field(
        default=None,
        description="Duración del audio en segundos"
    )
    model_used: str = Field(description="Modelo utilizado para la generación")
    processing_time_seconds: float = Field(
        description="Tiempo de procesamiento en segundos"
    )
    error: Optional[str] = Field(
        default=None,
        description="Mensaje de error si la generación falló"
    )


class ModelsInfoResponse(BaseModel):
    """
    Response con información de modelos disponibles.
    """
    available_models: list = Field(description="Lista de modelos disponibles")
    available_speakers: list = Field(description="Lista de speakers preestablecidos")
    supported_languages: list = Field(description="Lista de idiomas soportados")
    loaded_models: list = Field(description="Modelos actualmente cargados en memoria")
    cuda_available: bool = Field(description="Si CUDA está disponible")
    gpu_info: Optional[dict] = Field(
        default=None,
        description="Información de la GPU si está disponible"
    )


class HealthResponse(BaseModel):
    """
    Response de verificación de salud.
    """
    status: str = Field(description="Estado del servicio")
    version: str = Field(description="Versión del servicio")
    cuda_available: bool = Field(description="Si CUDA está disponible")
    models_loaded: list = Field(description="Modelos cargados en memoria")


# ============================================================
# SCHEMAS - GESTIÓN DE VOCES CLONADAS PERSISTENTES
# ============================================================

class CreateClonedVoiceRequest(BaseModel):
    """Request para crear una voz clonada persistente."""
    name: str = Field(..., min_length=1, max_length=50, description="Nombre identificativo de la voz")
    description: str = Field(default="", max_length=200, description="Descripción de la voz")
    ref_audio_url: str = Field(..., description="URL del audio de referencia")
    ref_text: str = Field(..., min_length=1, description="Texto correspondiente al audio de referencia")
    language: str = Field(default="Spanish", description="Idioma principal de la voz")


class UpdateClonedVoiceRequest(BaseModel):
    """Request para actualizar una voz clonada."""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)


class ClonedVoiceInfo(BaseModel):
    """Información de una voz clonada."""
    id: str
    name: str
    description: str
    ref_text: str
    language: str
    created_at: str
    last_used: str
    use_count: int


class ClonedVoiceListResponse(BaseModel):
    """Respuesta con lista de voces clonadas."""
    voices: List[ClonedVoiceInfo]
    total: int


class GenerateFromClonedVoiceRequest(BaseModel):
    """Request para generar audio usando una voz clonada guardada."""
    text: str = Field(..., min_length=1, description="Texto a convertir")
    voice_id: str = Field(..., description="ID de la voz clonada a usar")
    language: Optional[str] = Field(None, description="Idioma (opcional, usa el de la voz por defecto)")
    output_format: str = Field(default="wav", description="Formato de salida")
