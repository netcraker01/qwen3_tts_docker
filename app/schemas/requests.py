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
# PARÁMETROS DE GENERACIÓN COMUNES
# ============================================================

class GenerationParams(BaseModel):
    """
    Parámetros de generación para afinar la calidad de la voz.
    Estos parámetros se pasan directamente al modelo de generación.
    """
    temperature: float = Field(
        default=0.9,
        ge=0.1,
        le=2.0,
        description="Controla la creatividad/aleatoriedad de la generación. Valores más bajos = más determinístico, valores más altos = más variado",
        example=0.9
    )
    top_p: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling. Filtra tokens considerando solo los que acumulan hasta top_p de probabilidad",
        example=0.95
    )
    top_k: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Top-k sampling. Considera solo los k tokens más probables",
        example=50
    )
    repetition_penalty: float = Field(
        default=1.05,
        ge=1.0,
        le=2.0,
        description="Penaliza la repetición de tokens. 1.0 = sin penalización, valores más altos = menos repetición",
        example=1.05
    )
    do_sample: bool = Field(
        default=True,
        description="Si usar sampling (True) o greedy decoding (False)"
    )
    max_new_tokens: int = Field(
        default=4096,
        ge=100,
        le=8192,
        description="Número máximo de tokens a generar",
        example=4096
    )
    
    # Parámetros específicos del subtalker (para control de prosodia)
    subtalker_temperature: float = Field(
        default=0.9,
        ge=0.1,
        le=2.0,
        description="Temperature específico para el subtalker (control de prosodia)",
        example=0.9
    )
    subtalker_top_p: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Top-p específico para el subtalker",
        example=0.95
    )
    subtalker_top_k: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Top-k específico para el subtalker",
        example=50
    )
    subtalker_dosample: bool = Field(
        default=True,
        description="Do sample específico para el subtalker"
    )
    
    def to_generation_kwargs(self) -> dict:
        """Convierte los parámetros a un diccionario para pasar al modelo."""
        return {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "repetition_penalty": self.repetition_penalty,
            "do_sample": self.do_sample,
            "max_new_tokens": self.max_new_tokens,
            "subtalker_temperature": self.subtalker_temperature,
            "subtalker_top_p": self.subtalker_top_p,
            "subtalker_top_k": self.subtalker_top_k,
            "subtalker_dosample": self.subtalker_dosample,
        }

# ============================================================
# REQUESTS - CUSTOM VOICE
# ============================================================

class CustomVoiceRequest(GenerationParams):
    """
    Request para generar voz usando voces preestablecidas.
    Hereda GenerationParams para incluir parámetros de afinación.
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

class VoiceDesignRequest(GenerationParams):
    """
    Request para crear voz mediante descripción de texto.
    Hereda GenerationParams para incluir parámetros de afinación.
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

class VoiceCloneRequest(GenerationParams):
    """
    Request para clonar voz desde audio de referencia.
    Hereda GenerationParams para incluir parámetros de afinación.
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
    model_size: str = Field(
        default="1.7B",
        description="Tamaño del modelo a usar (0.6B más rápido, 1.7B mejor calidad)",
        example="1.7B"
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
    
    @validator('model_size')
    def validate_model_size(cls, v):
        if v not in MODEL_SIZES:
            raise ValueError(f"Tamaño de modelo '{v}' no válido. Opciones: {MODEL_SIZES}")
        return v


class VoiceCloneFromFileRequest(GenerationParams):
    """
    Request para clonar voz subiendo un archivo de audio.
    Hereda GenerationParams para incluir parámetros de afinación.
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
    available_models: dict = Field(description="Diccionario de modelos disponibles por tamaño")
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

class CreateClonedVoiceRequest(GenerationParams):
    """Request para crear una voz clonada persistente.
    Hereda GenerationParams para guardar parámetros de generación por defecto.
    """
    name: str = Field(..., min_length=1, max_length=50, description="Nombre identificativo de la voz")
    description: str = Field(default="", max_length=200, description="Descripción de la voz")
    ref_audio_url: str = Field(..., description="URL del audio de referencia")
    ref_text: str = Field(..., min_length=1, description="Texto correspondiente al audio de referencia")
    language: str = Field(default="Spanish", description="Idioma principal de la voz")


class UpdateClonedVoiceRequest(BaseModel):
    """Request para actualizar una voz clonada."""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    # Permite actualizar los parámetros de generación por defecto
    generation_params: Optional[dict] = Field(None, description="Parámetros de generación por defecto")


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
    generation_params: Optional[dict] = Field(None, description="Parámetros de generación por defecto")


class ClonedVoiceListResponse(BaseModel):
    """Respuesta con lista de voces clonadas."""
    voices: List[ClonedVoiceInfo]
    total: int


class GenerateFromClonedVoiceRequest(GenerationParams):
    """Request para generar audio usando una voz clonada guardada.
    Hereda GenerationParams para permitir override de parámetros.
    Si no se especifican, usa los guardados con la voz clonada.
    """
    text: str = Field(..., min_length=1, description="Texto a convertir")
    voice_id: str = Field(..., description="ID de la voz clonada a usar")
    language: Optional[str] = Field(None, description="Idioma (opcional, usa el de la voz por defecto)")
    output_format: str = Field(default="wav", description="Formato de salida")
    model_size: str = Field(default="1.7B", description="Tamaño del modelo (0.6B o 1.7B)")
    use_voice_defaults: bool = Field(
        default=True,
        description="Si usar los parámetros guardados con la voz (True) o los de esta petición (False)"
    )
    
    @validator('model_size')
    def validate_model_size(cls, v):
        if v not in MODEL_SIZES:
            raise ValueError(f"Tamaño de modelo '{v}' no válido. Opciones: {MODEL_SIZES}")
        return v
