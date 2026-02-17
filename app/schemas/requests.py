"""
Pydantic models for API requests and responses.
"""

from typing import Optional, Literal, List, Dict, Any, Union
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
    Response de verificación de salud del sistema.
    """
    status: str = Field(
        description="Estado del servicio: healthy, degraded, unhealthy",
        example="healthy"
    )
    timestamp: float = Field(
        description="Timestamp de la verificación en segundos desde epoch",
        example=1704067200.0
    )
    cuda_available: bool = Field(
        description="Si CUDA/GPU está disponible",
        example=True
    )
    models_ready: bool = Field(
        description="Si los modelos esenciales están disponibles",
        example=True
    )
    cache_dir: str = Field(
        description="Directorio de caché de modelos",
        example="/app/models"
    )


class RootResponse(BaseModel):
    """
    Response del endpoint raíz.
    """
    service: str = Field(
        description="Nombre del servicio",
        example="Qwen3-TTS Service API"
    )
    version: str = Field(
        description="Versión del servicio",
        example="1.0.0"
    )
    status: str = Field(
        description="Estado del servicio",
        example="running"
    )
    docs: str = Field(
        description="URL de la documentación Swagger",
        example="/docs"
    )
    health: str = Field(
        description="URL del health check",
        example="/api/v1/health"
    )


class SpeakerInfo(BaseModel):
    """
    Información de un speaker preestablecido.
    """
    gender: str = Field(description="Género de la voz", example="Female")
    language: str = Field(description="Idioma principal", example="Korean")
    style: str = Field(description="Estilo de la voz", example="Natural")


class SpeakersResponse(BaseModel):
    """
    Response con lista de speakers disponibles.
    """
    speakers: List[str] = Field(
        description="Lista de nombres de speakers",
        example=["Vivian", "Serena", "Sohee"]
    )
    details: Dict[str, SpeakerInfo] = Field(
        description="Detalles de cada speaker"
    )


class LanguagesResponse(BaseModel):
    """
    Response con lista de idiomas soportados.
    """
    languages: List[str] = Field(
        description="Lista de idiomas soportados",
        example=["Auto", "Spanish", "English", "Chinese"]
    )
    notes: str = Field(
        description="Notas sobre el uso de idiomas",
        example="Use 'Auto' para detección automática del idioma"
    )


class ModelStatusInfo(BaseModel):
    """
    Información del estado de un modelo.
    """
    model_id: str = Field(description="ID del modelo", example="Qwen/Qwen3-TTS-12Hz-1.7B-Base")
    installed: bool = Field(description="Si el modelo está instalado", example=True)
    path: Optional[str] = Field(default=None, description="Ruta del modelo", example="/app/models/Qwen3-TTS-12Hz-1.7B-Base")
    size_gb: Optional[float] = Field(default=None, description="Tamaño en GB", example=3.5)


class ModelsStatusResponse(BaseModel):
    """
    Response con estado de todos los modelos.
    """
    models: Dict[str, Dict[str, ModelStatusInfo]] = Field(description="Estado de todos los modelos")
    cache_dir: str = Field(description="Directorio de caché", example="/app/models")


class DownloadModelResponse(BaseModel):
    """
    Response de descarga de modelo.
    """
    success: bool = Field(description="Si la descarga fue exitosa", example=True)
    message: str = Field(description="Mensaje descriptivo", example="Modelo 1.7B/voice_clone descargado correctamente")


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


class ClonedVoiceDetailResponse(BaseModel):
    """Respuesta con detalle de una voz clonada."""
    voice: ClonedVoiceInfo


class ClonedVoiceCreateResponse(BaseModel):
    """Respuesta al crear una voz clonada."""
    success: bool = Field(description="Si la creación fue exitosa")
    voice: ClonedVoiceInfo
    message: str = Field(description="Mensaje descriptivo")


class ClonedVoiceUpdateResponse(BaseModel):
    """Respuesta al actualizar una voz clonada."""
    success: bool
    voice: ClonedVoiceInfo
    message: str


class ClonedVoiceDeleteResponse(BaseModel):
    """Respuesta al eliminar una voz clonada."""
    success: bool
    message: str


class ClonedVoicesStatsResponse(BaseModel):
    """Respuesta con estadísticas de voces clonadas."""
    total_voices: int = Field(description="Total de voces clonadas")
    total_generations: int = Field(description="Total de generaciones realizadas")
    most_used_voice: Optional[str] = Field(default=None, description="ID de la voz más usada")
    storage_size_mb: float = Field(description="Tamaño total en MB")


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


# ============================================================
# SCHEMAS - JOBS ASÍNCRONOS
# ============================================================

class CreateJobRequest(BaseModel):
    """Request para crear un job de generación de audio asíncrono."""
    job_type: str = Field(
        ...,
        description="Tipo de job: custom_voice, voice_design, voice_clone_url, voice_clone_file, cloned_voice_generate",
        example="custom_voice"
    )
    request_data: Dict[str, Any] = Field(
        ...,
        description="Datos específicos del request según el tipo de job"
    )
    
    @validator('job_type')
    def validate_job_type(cls, v):
        valid_types = ["custom_voice", "voice_design", "voice_clone_url", "voice_clone_file", "cloned_voice_generate"]
        if v not in valid_types:
            raise ValueError(f"Tipo de job '{v}' no válido. Opciones: {valid_types}")
        return v


class JobProgressInfo(BaseModel):
    """Información de progreso de un job."""
    stage: str = Field(description="Etapa actual del procesamiento", example="generating")
    percent: int = Field(description="Porcentaje de progreso (0-100)", example=75)
    message: str = Field(description="Mensaje descriptivo", example="Generando audio...")
    timestamp: float = Field(description="Timestamp de la última actualización", example=1704067200.0)


class JobInfo(BaseModel):
    """Información de un job."""
    id: str = Field(description="ID único del job", example="job_abc123")
    type: str = Field(description="Tipo de job", example="custom_voice")
    status: str = Field(description="Estado: pending, processing, completed, failed, cancelled, killed", example="processing")
    created_at: float = Field(description="Timestamp de creación", example=1704067200.0)
    updated_at: float = Field(description="Timestamp de última actualización", example=1704067200.0)
    progress: JobProgressInfo = Field(description="Progreso actual")
    result: Optional[Dict] = Field(default=None, description="Resultado si está completado")
    error: Optional[str] = Field(default=None, description="Mensaje de error si falló")
    elapsed_seconds: float = Field(description="Tiempo transcurrido en segundos", example=5.3)


class CreateJobResponse(BaseModel):
    """Response al crear un job."""
    success: bool = Field(description="Si el job fue creado exitosamente")
    job_id: str = Field(description="ID del job creado")
    job: JobInfo = Field(description="Información completa del job")
    stream_url: str = Field(description="URL para conectarse al stream SSE de progreso")
    status_url: str = Field(description="URL para consultar el estado del job")


class JobListResponse(BaseModel):
    """Response con lista de jobs."""
    jobs: List[JobInfo] = Field(description="Lista de jobs")
    total: int = Field(description="Total de jobs")


class JobStatusResponse(BaseModel):
    """Response con estado de un job."""
    job: JobInfo = Field(description="Información del job")


class JobResultResponse(BaseModel):
    """Response con resultado de un job completado."""
    success: bool = Field(description="Si el job fue exitoso")
    job_id: str = Field(description="ID del job")
    result: Dict = Field(description="Resultado del job")


class JobCancelResponse(BaseModel):
    """Response de cancelación de job."""
    success: bool = Field(description="Si la cancelación fue exitosa")
    message: str = Field(description="Mensaje descriptivo")
    job_status: str = Field(description="Estado actual del job")


class JobKillResponse(BaseModel):
    """Response de kill de job."""
    success: bool = Field(description="Si el kill fue exitoso")
    message: str = Field(description="Mensaje descriptivo")
    job_id: str = Field(description="ID del job")
    previous_status: str = Field(description="Estado anterior del job")
    current_status: str = Field(description="Estado actual del job")


class QueueStatusResponse(BaseModel):
    """Response con estado de la cola de jobs."""
    queue: Dict[str, int] = Field(description="Estado de la cola: pending, processing, max_concurrent")
    jobs: Dict[str, int] = Field(description="Estadísticas de jobs: total, completed, failed")
    system_status: str = Field(description="Estado del sistema: available, busy", example="available")


class JobDeleteResponse(BaseModel):
    """Response de eliminación de job."""
    success: bool = Field(description="Si la eliminación fue exitosa")
    message: str = Field(description="Mensaje descriptivo")


# ============================================================
# SCHEMAS - DESCARGA DE ARCHIVOS
# ============================================================

class DownloadFileResponse(BaseModel):
    """
    Response para descarga de archivos de audio.
    Nota: Este endpoint retorna el archivo directamente, no un JSON.
    """
    filename: str = Field(description="Nombre del archivo", example="audio_generated.wav")
    content_type: str = Field(description="Tipo MIME del archivo", example="audio/wav")
    
    class Config:
        json_schema_extra = {
            "description": "Este endpoint retorna el archivo de audio directamente como binary/octet-stream"
        }
