"""
ModelManager - Gestión robusta de modelos Qwen3-TTS con descarga lazy y progreso.
"""
import os
import json
import time
import logging
import threading
from pathlib import Path
from typing import Dict, Optional, Callable, List
from dataclasses import dataclass, asdict
from datetime import datetime

import requests

logger = logging.getLogger(__name__)


@dataclass
class DownloadProgress:
    """Estado de descarga de un modelo."""
    model_id: str
    status: str  # "pending", "downloading", "completed", "error"
    progress_percent: float
    current_file: str
    bytes_downloaded: int
    bytes_total: int
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class ModelManager:
    """
    Gestiona la descarga y verificación de modelos Qwen3-TTS.
    Implementa descarga lazy (bajo demanda) y reporte de progreso.
    """
    
    # Modelos soportados con sus configuraciones
    MODELS_CONFIG = {
        "1.7B": {
            "voice_clone": {
                "repo_id": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
                "files": ["config.json", "generation_config.json", "model.safetensors", 
                         "model.safetensors.index.json", "tokenizer_config.json"],
                "speech_tokenizer_files": ["preprocessor_config.json", "configuration.json", "model.safetensors"]
            },
            "custom_voice": {
                "repo_id": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
                "files": ["config.json", "generation_config.json", "model.safetensors",
                         "model.safetensors.index.json", "tokenizer_config.json"],
                "speech_tokenizer_files": ["preprocessor_config.json", "configuration.json", "model.safetensors"]
            },
            "voice_design": {
                "repo_id": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
                "files": ["config.json", "generation_config.json", "model.safetensors",
                         "model.safetensors.index.json", "tokenizer_config.json"],
                "speech_tokenizer_files": ["preprocessor_config.json", "configuration.json", "model.safetensors"]
            }
        },
        "0.6B": {
            "voice_clone": {
                "repo_id": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
                "files": ["config.json", "generation_config.json", "model.safetensors",
                         "tokenizer_config.json"],
                "speech_tokenizer_files": ["preprocessor_config.json", "configuration.json", "model.safetensors"]
            },
            "custom_voice": {
                "repo_id": "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
                "files": ["config.json", "generation_config.json", "model.safetensors",
                         "tokenizer_config.json"],
                "speech_tokenizer_files": ["preprocessor_config.json", "configuration.json", "model.safetensors"]
            },
            "voice_design": {
                "repo_id": "Qwen/Qwen3-TTS-12Hz-0.6B-VoiceDesign",
                "files": ["config.json", "generation_config.json", "model.safetensors",
                         "tokenizer_config.json"],
                "speech_tokenizer_files": ["preprocessor_config.json", "configuration.json", "model.safetensors"]
            }
        }
    }
    
    def __init__(self, cache_dir: str = None):
        # Usar ruta proporcionada, HF_HOME, o /app/models por defecto
        self.cache_dir = Path(cache_dir or os.getenv("HF_HOME", "/app/models"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Estado de descargas
        self._download_progress: Dict[str, DownloadProgress] = {}
        self._progress_callbacks: List[Callable] = []
        self._lock = threading.Lock()
        
        logger.info(f"ModelManager inicializado - Cache: {self.cache_dir}")
    
    def register_progress_callback(self, callback: Callable):
        """Registra una función callback para recibir actualizaciones de progreso."""
        self._progress_callbacks.append(callback)
    
    def _notify_progress(self, progress: DownloadProgress):
        """Notifica a todos los callbacks del progreso."""
        for callback in self._progress_callbacks:
            try:
                callback(progress)
            except Exception as e:
                logger.error(f"Error en callback de progreso: {e}")
    
    def _update_progress(self, model_id: str, **kwargs):
        """Actualiza el progreso de un modelo."""
        with self._lock:
            if model_id not in self._download_progress:
                self._download_progress[model_id] = DownloadProgress(
                    model_id=model_id,
                    status="pending",
                    progress_percent=0,
                    current_file="",
                    bytes_downloaded=0,
                    bytes_total=0
                )
            
            progress = self._download_progress[model_id]
            for key, value in kwargs.items():
                if hasattr(progress, key):
                    setattr(progress, key, value)
            
            self._notify_progress(progress)
    
    def get_model_status(self, model_size: str, model_type: str) -> Dict:
        """Obtiene el estado de un modelo específico."""
        config = self.MODELS_CONFIG[model_size][model_type]
        repo_id = config["repo_id"]
        model_name = repo_id.split("/")[-1]
        
        model_dir = self._get_model_dir(model_name)
        
        if not model_dir:
            return {
                "installed": False,
                "model_size": model_size,
                "model_type": model_type,
                "repo_id": repo_id,
                "progress": None
            }
        
        # Verificar archivos
        speech_tokenizer_dir = model_dir / "speech_tokenizer"
        has_tokenizer = (speech_tokenizer_dir / "model.safetensors").exists()
        has_main_model = (model_dir / "model.safetensors").exists() or \
                        (model_dir / "model.safetensors.index.json").exists()
        
        # Si el modelo existe pero falta el tokenizer, intentar corregir automáticamente
        if has_main_model and not has_tokenizer:
            logger.warning(f"Modelo {repo_id} encontrado pero falta speech_tokenizer. Intentando corrección automática...")
            if self._fix_speech_tokenizer(model_size, model_type):
                # Verificar de nuevo después de la corrección
                has_tokenizer = (speech_tokenizer_dir / "model.safetensors").exists()
                logger.info(f"Corrección automática {'exitosa' if has_tokenizer else 'fallida'}")
        
        return {
            "installed": has_tokenizer and has_main_model,
            "model_size": model_size,
            "model_type": model_type,
            "repo_id": repo_id,
            "path": str(model_dir),
            "has_tokenizer": has_tokenizer,
            "has_main_model": has_main_model,
            "progress": asdict(self._download_progress.get(repo_id)) if repo_id in self._download_progress else None
        }
    
    def get_all_models_status(self) -> List[Dict]:
        """Obtiene el estado de todos los modelos."""
        statuses = []
        for model_size in ["1.7B", "0.6B"]:
            for model_type in ["voice_clone", "custom_voice", "voice_design"]:
                statuses.append(self.get_model_status(model_size, model_type))
        return statuses
    
    def _get_model_dir(self, model_name: str) -> Optional[Path]:
        """Encuentra el directorio de un modelo en el caché."""
        model_pattern = self.cache_dir / f"models--Qwen--{model_name}"
        if not model_pattern.exists():
            return None
        
        # Buscar directorio de snapshot
        snapshots_dir = model_pattern / "snapshots"
        if not snapshots_dir.exists():
            return None
        
        snapshots = list(snapshots_dir.iterdir())
        if not snapshots:
            return None
        
        return snapshots[0]

    def _fix_speech_tokenizer(self, model_size: str, model_type: str) -> bool:
        """
        Intenta corregir los archivos faltantes del speech_tokenizer.
        Se ejecuta automáticamente si detecta que faltan archivos.
        """
        try:
            import shutil
            from huggingface_hub import hf_hub_download
            
            config = self.MODELS_CONFIG[model_size][model_type]
            repo_id = config["repo_id"]
            model_name = repo_id.split("/")[-1]
            
            logger.info(f"Intentando corregir speech_tokenizer para {repo_id}...")
            
            model_dir = self._get_model_dir(model_name)
            if not model_dir:
                logger.warning(f"No se encontró directorio del modelo {model_name}")
                return False
            
            tokenizer_dir = model_dir / "speech_tokenizer"
            tokenizer_dir.mkdir(parents=True, exist_ok=True)
            
            required_files = config.get("speech_tokenizer_files", [])
            all_ok = True
            
            for filename in required_files:
                dest_path = tokenizer_dir / filename
                if dest_path.exists():
                    continue
                
                logger.info(f"  Descargando speech_tokenizer/{filename}...")
                try:
                    downloaded_path = hf_hub_download(
                        repo_id=repo_id,
                        filename=f"speech_tokenizer/{filename}",
                        cache_dir=self.cache_dir,
                        local_dir_use_symlinks=False,
                        force_download=True
                    )
                    
                    downloaded_path = Path(downloaded_path).resolve()
                    if downloaded_path.exists():
                        shutil.copy2(str(downloaded_path), str(dest_path))
                        logger.info(f"  ✓ {filename} descargado")
                    else:
                        logger.error(f"  ✗ No se pudo descargar {filename}")
                        all_ok = False
                        
                except Exception as e:
                    logger.error(f"  ✗ Error descargando {filename}: {e}")
                    all_ok = False
            
            return all_ok
            
        except Exception as e:
            logger.error(f"Error corrigiendo speech_tokenizer: {e}")
            return False
    
    def ensure_model_downloaded(self, model_size: str, model_type: str, 
                                progress_callback: Callable = None) -> bool:
        """
        Asegura que un modelo esté descargado. Descarga si es necesario.
        
        Args:
            model_size: "1.7B" o "0.6B"
            model_type: "voice_clone", "custom_voice", "voice_design"
            progress_callback: Función opcional para recibir progreso
        
        Returns:
            True si el modelo está listo, False en caso de error
        """
        config = self.MODELS_CONFIG[model_size][model_type]
        repo_id = config["repo_id"]
        model_name = repo_id.split("/")[-1]
        
        # Registrar callback temporal si se proporciona
        if progress_callback:
            self.register_progress_callback(progress_callback)
        
        try:
            # Verificar si ya está descargado
            status = self.get_model_status(model_size, model_type)
            if status["installed"]:
                logger.info(f"Modelo {repo_id} ya está instalado")
                return True
            
            # Iniciar descarga
            logger.info(f"Descargando modelo {repo_id}...")
            self._update_progress(repo_id, status="downloading", started_at=datetime.now().isoformat())
            
            # Descargar archivos principales
            model_dir = self._download_model_files(repo_id, config)
            
            if model_dir:
                self._update_progress(repo_id, status="completed", progress_percent=100,
                                     completed_at=datetime.now().isoformat())
                logger.info(f"Modelo {repo_id} descargado correctamente")
                return True
            else:
                self._update_progress(repo_id, status="error", 
                                     error_message="No se pudo descargar el modelo")
                return False
                
        except Exception as e:
            logger.error(f"Error descargando modelo {repo_id}: {e}")
            self._update_progress(repo_id, status="error", error_message=str(e))
            return False
        finally:
            # Desregistrar callback temporal
            if progress_callback and progress_callback in self._progress_callbacks:
                self._progress_callbacks.remove(progress_callback)
    
    def _download_model_files(self, repo_id: str, config: Dict) -> Optional[Path]:
        """Descarga los archivos de un modelo."""
        model_name = repo_id.split("/")[-1]
        
        # Crear estructura de directorios
        snapshot_id = datetime.now().strftime("%Y%m%d%H%M%S")
        model_dir = self.cache_dir / f"models--Qwen--{model_name}" / "snapshots" / snapshot_id
        model_dir.mkdir(parents=True, exist_ok=True)
        
        base_url = f"https://huggingface.co/{repo_id}/resolve/main"
        
        # Descargar archivos principales
        files_to_download = config.get("files", [])
        for i, filename in enumerate(files_to_download):
            progress = (i / len(files_to_download)) * 50  # 50% para archivos principales
            self._update_progress(repo_id, progress_percent=progress, current_file=filename)
            
            url = f"{base_url}/{filename}"
            dest_path = model_dir / filename
            
            if not self._download_file(url, dest_path):
                logger.warning(f"No se pudo descargar {filename}, continuando...")
        
        # Descargar archivos del speech_tokenizer
        tokenizer_files = config.get("speech_tokenizer_files", [])
        tokenizer_dir = model_dir / "speech_tokenizer"
        tokenizer_dir.mkdir(exist_ok=True)
        
        for i, filename in enumerate(tokenizer_files):
            progress = 50 + (i / len(tokenizer_files)) * 50  # 50-100% para speech_tokenizer
            self._update_progress(repo_id, progress_percent=progress, 
                                 current_file=f"speech_tokenizer/{filename}")
            
            url = f"{base_url}/speech_tokenizer/{filename}"
            dest_path = tokenizer_dir / filename
            
            if not self._download_file(url, dest_path):
                logger.error(f"No se pudo descargar speech_tokenizer/{filename}")
                return None
        
        return model_dir
    
    def _download_file(self, url: str, dest_path: Path) -> bool:
        """Descarga un archivo individual con reintentos."""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                response = requests.get(url, stream=True, timeout=60)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(dest_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                
                # Verificar tamaño
                if total_size > 0 and downloaded != total_size:
                    logger.warning(f"Tamaño descargado no coincide: {downloaded} vs {total_size}")
                
                return True
                
            except Exception as e:
                logger.warning(f"Intento {attempt + 1} fallido para {url}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Backoff exponencial
                else:
                    logger.error(f"No se pudo descargar {url} después de {max_retries} intentos")
        
        return False
    
    def predownload_all_models(self, model_size: str = "1.7B") -> bool:
        """Descarga todos los modelos de un tamaño específico al inicio."""
        logger.info(f"Pre-descargando modelos {model_size}...")
        
        all_success = True
        for model_type in ["voice_clone", "custom_voice", "voice_design"]:
            if not self.ensure_model_downloaded(model_size, model_type):
                logger.error(f"No se pudo descargar {model_type}")
                all_success = False
        
        return all_success


# Singleton instance
_model_manager = None

def get_model_manager(cache_dir: str = None) -> ModelManager:
    """Obtiene la instancia singleton del ModelManager."""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager(cache_dir)
    return _model_manager