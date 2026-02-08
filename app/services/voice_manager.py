"""
VoiceManager - Gestión persistente de voces clonadas
"""
import os
import json
import time
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ClonedVoice:
    """Representa una voz clonada almacenada."""
    id: str
    name: str
    description: str
    ref_audio_path: str
    ref_text: str
    language: str
    created_at: str
    last_used: str
    use_count: int = 0
    prompt_data: Any = None  # El objeto prompt de Qwen3TTS (opcional, no se serializa)
    generation_params: Optional[Dict] = None  # Parámetros de generación por defecto
    
    def to_dict(self) -> Dict:
        """Convierte a diccionario (el prompt_data no se serializa)."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "ref_audio_path": self.ref_audio_path,
            "ref_text": self.ref_text,
            "language": self.language,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "use_count": self.use_count,
            "generation_params": self.generation_params
        }


class VoiceManager:
    """
    Gestiona el almacenamiento persistente de voces clonadas.
    Las voces se guardan en un archivo JSON y los prompts en memoria.
    """
    
    def __init__(self, storage_dir: str = "/app/data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.voices_file = self.storage_dir / "cloned_voices.json"
        self.voices: Dict[str, ClonedVoice] = {}
        self._prompts: Dict[str, Any] = {}  # Cache en memoria de los prompts
        
        self._load_voices()
        logger.info(f"VoiceManager inicializado. Voces cargadas: {len(self.voices)}")
    
    def _load_voices(self):
        """Carga las voces desde el archivo JSON."""
        if self.voices_file.exists():
            try:
                with open(self.voices_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for voice_data in data.get("voices", []):
                        # Asegurar que prompt_data existe (aunque sea None)
                        if "prompt_data" not in voice_data:
                            voice_data["prompt_data"] = None
                        voice = ClonedVoice(**voice_data)
                        self.voices[voice.id] = voice
                logger.info(f"Cargadas {len(self.voices)} voces clonadas desde {self.voices_file}")
            except Exception as e:
                logger.error(f"Error cargando voces: {e}")
                import traceback
                logger.error(traceback.format_exc())
                self.voices = {}
    
    def _save_voices(self):
        """Guarda las voces en el archivo JSON."""
        try:
            data = {
                "voices": [voice.to_dict() for voice in self.voices.values()],
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(self.voices_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Guardadas {len(self.voices)} voces clonadas")
        except Exception as e:
            logger.error(f"Error guardando voces: {e}")
            raise
    
    def create_voice(
        self,
        name: str,
        description: str,
        ref_audio_path: str,
        ref_text: str,
        language: str,
        prompt_data: Any,
        generation_params: Optional[Dict] = None
    ) -> ClonedVoice:
        """
        Crea una nueva voz clonada y la guarda.
        
        Args:
            name: Nombre identificativo de la voz
            description: Descripción de la voz
            ref_audio_path: Ruta al audio de referencia
            ref_text: Texto del audio de referencia
            language: Idioma principal
            prompt_data: El objeto prompt generado por Qwen3TTS
            generation_params: Parámetros de generación por defecto
        
        Returns:
            La voz clonada creada
        """
        # Generar ID único basado en nombre y timestamp
        voice_id = f"{name.lower().replace(' ', '_')}_{int(time.time())}"
        
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        
        voice = ClonedVoice(
            id=voice_id,
            name=name,
            description=description,
            ref_audio_path=ref_audio_path,
            ref_text=ref_text,
            language=language,
            prompt_data=prompt_data,
            generation_params=generation_params,
            created_at=now,
            last_used=now,
            use_count=0
        )
        
        # Guardar en memoria
        self.voices[voice_id] = voice
        self._prompts[voice_id] = prompt_data
        
        # Persistir
        self._save_voices()
        
        logger.info(f"Voz clonada creada: {name} (ID: {voice_id})")
        return voice
    
    def get_voice(self, voice_id: str) -> Optional[ClonedVoice]:
        """
        Obtiene una voz clonada por su ID.
        
        Args:
            voice_id: ID de la voz
        
        Returns:
            La voz clonada o None si no existe
        """
        voice = self.voices.get(voice_id)
        if voice:
            # Actualizar estadísticas de uso
            voice.last_used = time.strftime("%Y-%m-%d %H:%M:%S")
            voice.use_count += 1
            self._save_voices()
        return voice
    
    def get_prompt(self, voice_id: str) -> Optional[Any]:
        """
        Obtiene el prompt de una voz clonada.
        
        Args:
            voice_id: ID de la voz
        
        Returns:
            El objeto prompt o None
        """
        # Primero verificar en cache de memoria
        if voice_id in self._prompts:
            return self._prompts[voice_id]
        
        # Si no está en memoria, la voz no está disponible
        # (los prompts no se pueden serializar, hay que recrearlos)
        return None
    
    def list_voices(self) -> List[Dict]:
        """
        Lista todas las voces clonadas.
        
        Returns:
            Lista de diccionarios con información de las voces
        """
        return [voice.to_dict() for voice in self.voices.values()]
    
    def update_voice(
        self,
        voice_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        generation_params: Optional[Dict] = None
    ) -> Optional[ClonedVoice]:
        """
        Actualiza la información de una voz clonada.
        
        Args:
            voice_id: ID de la voz
            name: Nuevo nombre (opcional)
            description: Nueva descripción (opcional)
            generation_params: Nuevos parámetros de generación (opcional)
        
        Returns:
            La voz actualizada o None si no existe
        """
        voice = self.voices.get(voice_id)
        if not voice:
            return None
        
        if name:
            voice.name = name
        if description:
            voice.description = description
        if generation_params is not None:
            voice.generation_params = generation_params
        
        self._save_voices()
        logger.info(f"Voz actualizada: {voice_id}")
        return voice
    
    def delete_voice(self, voice_id: str) -> bool:
        """
        Elimina una voz clonada.
        
        Args:
            voice_id: ID de la voz a eliminar
        
        Returns:
            True si se eliminó, False si no existía
        """
        if voice_id not in self.voices:
            return False
        
        # Eliminar de memoria y cache
        del self.voices[voice_id]
        if voice_id in self._prompts:
            del self._prompts[voice_id]
        
        # Persistir cambios
        self._save_voices()
        
        logger.info(f"Voz eliminada: {voice_id}")
        return True
    
    def get_voice_stats(self) -> Dict:
        """
        Obtiene estadísticas de las voces clonadas.
        
        Returns:
            Diccionario con estadísticas
        """
        total_voices = len(self.voices)
        total_uses = sum(v.use_count for v in self.voices.values())
        
        return {
            "total_voices": total_voices,
            "total_uses": total_uses,
            "most_used": max(
                (v.to_dict() for v in self.voices.values()),
                key=lambda x: x["use_count"],
                default=None
            ) if self.voices else None,
            "recently_created": sorted(
                (v.to_dict() for v in self.voices.values()),
                key=lambda x: x["created_at"],
                reverse=True
            )[:5]
        }