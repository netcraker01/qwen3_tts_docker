"""
Qwen3-TTS Service API
Servicio de Texto a Voz basado en Qwen3-TTS con soporte para:
- Custom Voice (voces preestablecidas)
- Voice Design (diseño de voces por descripción)
- Voice Clone (clonación de voz Zero-Shot)
"""

import os
import logging
from contextlib import asynccontextmanager

import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router as api_router
from app.services.tts_service import TTSService

# Configuración de logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuración de variables de entorno
MODEL_CACHE_DIR = os.getenv("MODEL_CACHE_DIR", "/app/models")
DEFAULT_MODEL_SIZE = os.getenv("DEFAULT_MODEL_SIZE", "1.7B")
USE_FLASH_ATTENTION = os.getenv("USE_FLASH_ATTENTION", "true").lower() == "true"

# Información de la aplicación
APP_TITLE = "Qwen3-TTS Service API"
APP_DESCRIPTION = """
API REST para síntesis de voz utilizando Qwen3-TTS.

## Funcionalidades

* **Custom Voice**: Genera voz usando personajes preestablecidos (Vivian, Ryan, Sohee, etc.)
* **Voice Design**: Crea voces personalizadas mediante descripciones de texto
* **Voice Clone**: Clona voces desde audio de referencia (Zero-Shot)

## Modelos Disponibles

* Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice
* Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign  
* Qwen/Qwen3-TTS-12Hz-1.7B-Base

## Soporte de Idiomas

Español, Inglés, Chino, Japonés, Coreano, Alemán, Francés, Ruso, Portugués, Italiano
"""
APP_VERSION = "1.0.0"

# Servicio TTS global
tts_service: TTSService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestión del ciclo de vida de la aplicación.
    Inicializa y limpia recursos del servicio TTS.
    """
    global tts_service
    
    logger.info("Iniciando Qwen3-TTS Service...")
    logger.info(f"Device: {'CUDA' if torch.cuda.is_available() else 'CPU'}")
    if torch.cuda.is_available():
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
        logger.info(f"VRAM disponible: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    
    try:
        # Inicializar servicio (sin cargar modelos todavía - lazy loading)
        tts_service = TTSService(
            cache_dir=MODEL_CACHE_DIR,
            default_model_size=DEFAULT_MODEL_SIZE,
            use_flash_attention=USE_FLASH_ATTENTION
        )
        logger.info("Servicio TTS inicializado correctamente")
    except Exception as e:
        logger.error(f"Error al inicializar el servicio TTS: {e}")
        raise
    
    yield
    
    # Cleanup
    logger.info("Cerrando Qwen3-TTS Service...")
    if tts_service:
        tts_service.cleanup()
        logger.info("Recursos liberados")


# Crear aplicación FastAPI
app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas de la API
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Endpoint raíz con información básica del servicio."""
    return {
        "service": APP_TITLE,
        "version": APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


@app.get("/api/v1/health")
async def health_check():
    """Endpoint de verificación de salud del servicio."""
    health_status = {
        "status": "healthy",
        "cuda_available": torch.cuda.is_available(),
        "models_loaded": tts_service.get_loaded_models() if tts_service else [],
        "default_model_size": DEFAULT_MODEL_SIZE
    }
    
    if torch.cuda.is_available():
        health_status["gpu_name"] = torch.cuda.get_device_name(0)
        health_status["gpu_memory_allocated"] = f"{torch.cuda.memory_allocated() / 1e9:.2f} GB"
        health_status["gpu_memory_reserved"] = f"{torch.cuda.memory_reserved() / 1e9:.2f} GB"
    
    return health_status


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Manejador global de excepciones."""
    logger.error(f"Error no manejado: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor", "error": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)