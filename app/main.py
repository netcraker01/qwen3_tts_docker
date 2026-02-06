"""
Qwen3-TTS Service API
Servicio de Texto a Voz basado en Qwen3-TTS
"""
import os
import logging
from contextlib import asynccontextmanager

import torch
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

# Configuración de logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuración de variables de entorno
MODEL_CACHE_DIR = os.getenv("MODEL_CACHE_DIR", "/app/models")
DEFAULT_MODEL_SIZE = os.getenv("DEFAULT_MODEL_SIZE", "1.7B")

# Información de la aplicación
APP_TITLE = "Qwen3-TTS Service API"
APP_VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestión del ciclo de vida de la aplicación.
    """
    logger.info("Iniciando Qwen3-TTS Service...")
    logger.info(f"Device: {'CUDA' if torch.cuda.is_available() else 'CPU'}")
    if torch.cuda.is_available():
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
    
    # Inicializar servicio TTS (se carga bajo demanda)
    from app.dependencies import get_tts_service
    try:
        tts_service = get_tts_service()
        logger.info("Servicio TTS inicializado correctamente")
    except Exception as e:
        logger.error(f"Error al inicializar el servicio TTS: {e}")
        raise
    
    yield
    
    # Cleanup
    logger.info("Cerrando Qwen3-TTS Service...")


# Crear aplicación FastAPI
app = FastAPI(
    title=APP_TITLE,
    description="API REST para síntesis de voz utilizando Qwen3-TTS",
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Importar y registrar rutas
from app.api.routes import router as api_router
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
    from app.dependencies import get_tts_service
    
    tts_service = get_tts_service()
    health_status = {
        "status": "healthy",
        "cuda_available": torch.cuda.is_available(),
        "models_loaded": tts_service.get_loaded_models(),
        "default_model_size": DEFAULT_MODEL_SIZE
    }
    
    if torch.cuda.is_available():
        health_status["gpu_name"] = torch.cuda.get_device_name(0)
    
    return health_status


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Manejador global de excepciones."""
    logger.error(f"Error no manejado: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor", "error": str(exc)}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Manejador personalizado para errores de validación."""
    # Convertir errores a strings para evitar problemas de serialización con bytes
    errors = []
    for error in exc.errors():
        error_dict = {}
        for key, value in error.items():
            if isinstance(value, bytes):
                error_dict[key] = f"<binary: {len(value)} bytes>"
            else:
                error_dict[key] = str(value) if not isinstance(value, (str, int, float, bool, list, dict, type(None))) else value
        errors.append(error_dict)
    
    return JSONResponse(
        status_code=422,
        content={"detail": errors}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)