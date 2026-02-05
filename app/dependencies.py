"""
Dependencies - Gestión de dependencias globales
"""
from app.services.tts_service import TTSService

# Singleton global del servicio TTS
_tts_service = None

def get_tts_service() -> TTSService:
    """Obtiene o inicializa el servicio TTS (singleton)."""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service