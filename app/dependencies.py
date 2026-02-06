"""
Dependencies - Gestión de dependencias globales
"""
import os
from app.services.tts_service import TTSService

# Singleton global del servicio TTS
_tts_service = None

def get_tts_service() -> TTSService:
    """Obtiene o inicializa el servicio TTS (singleton)."""
    global _tts_service
    if _tts_service is None:
        # Usar caché estándar de HuggingFace donde se descargaron los modelos
        cache_dir = os.getenv("HF_HOME", "/app/models")
        _tts_service = TTSService(cache_dir=cache_dir)
    return _tts_service
