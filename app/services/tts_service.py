

















































































































































































































































































































































"""
TTSService - Gestión de modelos Qwen3-TTS y generación de audio.
"""

import os
import io
import time
import base64
import logging
import tempfile
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass

import torch
import soundfile as sf
import numpy as np
from pydub import AudioSegment

# Qwen3-TTS imports
try:
    from qwen_tts import Qwen3TTSModel
except ImportError:
    # Mock para desarrollo sin GPU
    Qwen3TTSModel = None

logger = logging.getLogger(__name__)


@dataclass
class AudioResult:
    """Resultado de generación de audio."""
    audio_data: np.ndarray
    sample_rate: int
    duration_seconds: float
    model_used: str


class TTSService:
    """
    Servicio para gestión de modelos TTS y generación de audio.
    Implementa lazy loading de modelos para optimizar memoria.
    """
    
    # Model IDs de HuggingFace
    MODELS = {
        "1.7B": {
            "custom_voice": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
            "voice_design": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
            "voice_clone": "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
        },
        "0.6B": {
            "custom_voice": "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
            "voice_design": "Qwen/Qwen3-TTS-12Hz-0.6B-VoiceDesign",
            "voice_clone": "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
        }
    }
    
    def __init__(
        self,
        cache_dir: str = None,
        default_model_size: str = "1.7B",
        use_flash_attention: bool = True
    ):
        # Usar HF_HOME si está definido, o caché estándar de HuggingFace
        if cache_dir is None:
            cache_dir = os.getenv("HF_HOME", "/root/.cache/huggingface/hub")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_model_size = default_model_size
        # Flash attention requiere compilación con nvcc, deshabilitado por defecto
        self.use_flash_attention = False  # use_flash_attention and torch.cuda.is_available()
        
        # Cache de modelos cargados
        self._models: Dict[str, Any] = {}
        self._voice_clone_prompts: Dict[str, Any] = {}
        
        # Configuración de device
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.dtype = torch.bfloat16 if self.device == "cuda" else torch.float32
        
        logger.info(f"TTSService inicializado - Device: {self.device}, Dtype: {self.dtype}")
        logger.info(f"Flash Attention: {self.use_flash_attention}")
        logger.info(f"Cache dir: {self.cache_dir}")
    
    def _get_model(self, model_type: str, model_size: Optional[str] = None) -> Any:
        """
        Obtiene un modelo, cargándolo si es necesario (lazy loading).
        
        Args:
            model_type: Tipo de modelo ('custom_voice', 'voice_design', 'voice_clone')
            model_size: Tamaño del modelo ('1.7B' o '0.6B')
        
        Returns:
            Modelo Qwen3TTS cargado
        """
        if Qwen3TTSModel is None:
            raise RuntimeError("qwen-tts no está instalado")
        
        size = model_size or self.default_model_size
        cache_key = f"{size}_{model_type}"
        
        if cache_key not in self._models:
            model_id = self.MODELS[size][model_type]
            logger.info(f"Cargando modelo: {model_id}")
            
            try:
                model = Qwen3TTSModel.from_pretrained(
                    model_id,
                    cache_dir=str(self.cache_dir),
                    device_map="auto",
                    dtype=self.dtype,
                    attn_implementation="flash_attention_2" if self.use_flash_attention else None,
                )
                self._models[cache_key] = model
                logger.info(f"Modelo {model_id} cargado exitosamente")
                
            except Exception as e:
                logger.error(f"Error cargando modelo {model_id}: {e}")
                raise RuntimeError(f"No se pudo cargar el modelo {model_id}: {e}")
        
        return self._models[cache_key]
    
    def get_loaded_models(self) -> List[str]:
        """Retorna lista de modelos actualmente cargados."""
        return list(self._models.keys())
    
    def cleanup(self):
        """Libera recursos y modelos cargados."""
        logger.info("Limpiando recursos...")
        self._models.clear()
        self._voice_clone_prompts.clear()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info("Recursos liberados")
    
    # ============================================================
    # CUSTOM VOICE
    # ============================================================
    
    def generate_custom_voice(
        self,
        text: str,
        speaker: str,
        language: str = "Auto",
        instruction: Optional[str] = None,
        model_size: Optional[str] = None
    ) -> AudioResult:
        """
        Genera voz usando un personaje preestablecido.
        
        Args:
            text: Texto a convertir
            speaker: Nombre del speaker (Vivian, Ryan, etc.)
            language: Idioma del texto
            instruction: Instrucción opcional para modificar estilo/emoción
            model_size: Tamaño del modelo a usar
        
        Returns:
            AudioResult con el audio generado
        """
        model = self._get_model("custom_voice", model_size)
        
        logger.info(f"Generando Custom Voice - Speaker: {speaker}, Lang: {language}")
        start_time = time.time()
        
        try:
            wavs, sr = model.generate_custom_voice(
                text=text,
                language=language,
                speaker=speaker,
                instruct=instruction
            )
            
            audio_data = wavs[0]
            duration = len(audio_data) / sr
            processing_time = time.time() - start_time
            
            logger.info(f"Audio generado: {duration:.2f}s en {processing_time:.2f}s")
            
            return AudioResult(
                audio_data=audio_data,
                sample_rate=sr,
                duration_seconds=duration,
                model_used=f"{model_size or self.default_model_size}_custom_voice"
            )
            
        except Exception as e:
            logger.error(f"Error en generate_custom_voice: {e}")
            raise
    
    # ============================================================
    # VOICE DESIGN
    # ============================================================
    
    def generate_voice_design(
        self,
        text: str,
        voice_description: str,
        language: str = "Spanish",
        model_size: Optional[str] = None
    ) -> AudioResult:
        """
        Genera voz mediante descripción de texto.
        
        Args:
            text: Texto a convertir
            voice_description: Descripción detallada de la voz deseada
            language: Idioma del texto
            model_size: Tamaño del modelo a usar
        
        Returns:
            AudioResult con el audio generado
        """
        model = self._get_model("voice_design", model_size)
        
        logger.info(f"Generando Voice Design - Lang: {language}")
        logger.debug(f"Voice description: {voice_description[:100]}...")
        start_time = time.time()
        
        try:
            wavs, sr = model.generate_voice_design(
                text=text,
                language=language,
                instruct=voice_description
            )
            
            audio_data = wavs[0]
            duration = len(audio_data) / sr
            processing_time = time.time() - start_time
            
            logger.info(f"Audio generado: {duration:.2f}s en {processing_time:.2f}s")
            
            return AudioResult(
                audio_data=audio_data,
                sample_rate=sr,
                duration_seconds=duration,
                model_used=f"{model_size or self.default_model_size}_voice_design"
            )
            
        except Exception as e:
            logger.error(f"Error en generate_voice_design: {e}")
            raise
    
    # ============================================================
    # VOICE CLONE
    # ============================================================
    
    def create_voice_clone_prompt(
        self,
        ref_audio_path: str,
        ref_text: str,
        model_size: Optional[str] = None
    ) -> str:
        """
        Crea un prompt de clonación de voz desde audio de referencia.
        
        Args:
            ref_audio_path: Ruta al audio de referencia (URL o archivo local)
            ref_text: Texto correspondiente al audio
            model_size: Tamaño del modelo a usar
        
        Returns:
            ID del prompt creado (para reuso)
        """
        model = self._get_model("voice_clone", model_size)
        
        prompt_id = f"{hash(ref_audio_path)}_{hash(ref_text)}"
        
        if prompt_id not in self._voice_clone_prompts:
            logger.info(f"Creando voice clone prompt: {prompt_id}")
            
            try:
                # Descargar si es URL
                if ref_audio_path.startswith("http"):
                    audio_path = self._download_audio(ref_audio_path)
                else:
                    audio_path = ref_audio_path
                
                prompt = model.create_voice_clone_prompt(
                    ref_audio=audio_path,
                    ref_text=ref_text
                )
                
                self._voice_clone_prompts[prompt_id] = prompt
                logger.info(f"Voice clone prompt creado: {prompt_id}")
                
            except Exception as e:
                logger.error(f"Error creando voice clone prompt: {e}")
                raise
        
        return prompt_id
    
    def generate_voice_clone(
        self,
        text: str,
        voice_clone_prompt_id: str,
        language: str = "Spanish",
        model_size: Optional[str] = None
    ) -> AudioResult:
        """
        Genera voz clonada usando un prompt previamente creado.
        
        Args:
            text: Texto a convertir
            voice_clone_prompt_id: ID del prompt de clonación
            language: Idioma del texto
            model_size: Tamaño del modelo a usar
        
        Returns:
            AudioResult con el audio generado
        """
        model = self._get_model("voice_clone", model_size)
        
        if voice_clone_prompt_id not in self._voice_clone_prompts:
            raise ValueError(f"Voice clone prompt no encontrado: {voice_clone_prompt_id}")
        
        prompt = self._voice_clone_prompts[voice_clone_prompt_id]
        
        logger.info(f"Generando Voice Clone - Lang: {language}")
        start_time = time.time()
        
        try:
            wavs, sr = model.generate_voice_clone(
                text=text,
                language=language,
                voice_clone_prompt=prompt
            )
            
            audio_data = wavs[0]
            duration = len(audio_data) / sr
            processing_time = time.time() - start_time
            
            logger.info(f"Audio generado: {duration:.2f}s en {processing_time:.2f}s")
            
            return AudioResult(
                audio_data=audio_data,
                sample_rate=sr,
                duration_seconds=duration,
                model_used=f"{model_size or self.default_model_size}_voice_clone"
            )
            
        except Exception as e:
            logger.error(f"Error en generate_voice_clone: {e}")
            raise
    
    def generate_voice_clone_from_file(
        self,
        text: str,
        ref_audio_file: bytes,
        ref_text: str,
        language: str = "Spanish",
        model_size: Optional[str] = None
    ) -> AudioResult:
        """
        Genera voz clonada subiendo directamente un archivo de audio.
        
        Args:
            text: Texto a convertir
            ref_audio_file: Contenido del archivo de audio (bytes)
            ref_text: Texto correspondiente al audio
            language: Idioma del texto
            model_size: Tamaño del modelo a usar
        
        Returns:
            AudioResult con el audio generado
        """
        # Guardar archivo temporal
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(ref_audio_file)
            tmp_path = tmp.name
        
        try:
            # Crear prompt y generar
            prompt_id = self.create_voice_clone_prompt(tmp_path, ref_text, model_size)
            result = self.generate_voice_clone(text, prompt_id, language, model_size)
            return result
            
        finally:
            # Limpiar archivo temporal
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    # ============================================================
    # UTILIDADES
    # ============================================================
    
    def _download_audio(self, url: str) -> str:
        """Descarga audio desde URL y retorna ruta temporal."""
        import httpx
        
        logger.info(f"Descargando audio desde: {url}")
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            with httpx.Client() as client:
                response = client.get(url, timeout=30.0)
                response.raise_for_status()
                tmp.write(response.content)
                return tmp.name
    
    def audio_to_base64(self, audio_result: AudioResult, output_format: str = "wav") -> str:
        """
        Convierte AudioResult a string base64 con formatos compatibles WhatsApp.
        
        Args:
            audio_result: Resultado de generación
            output_format: Formato de salida (wav, mp3, ogg, opus)
        
        Returns:
            Audio codificado en base64
        """
        import tempfile
        import subprocess
        import numpy as np
        
        # Asegurar que los datos estén en el rango correcto
        audio_data = audio_result.audio_data
        if audio_data.dtype != np.int16:
            # Convertir a int16 si es necesario
            if audio_data.max() <= 1.0:
                audio_data = (audio_data * 32767).astype(np.int16)
            else:
                audio_data = audio_data.astype(np.int16)
        
        # Crear archivo temporal para salida
        with tempfile.NamedTemporaryFile(suffix=f".{output_format}", delete=False) as tmp:
            output_path = tmp.name
        
        try:
            if output_format.lower() == "wav":
                # Guardar directamente como WAV
                sf.write(output_path, audio_data, audio_result.sample_rate, subtype='PCM_16')
                with open(output_path, 'rb') as f:
                    return base64.b64encode(f.read()).decode('utf-8')
            
            # Para otros formatos, usar ffmpeg desde raw PCM
            # Primero guardar como raw PCM
            raw_path = output_path + ".raw"
            audio_data.tofile(raw_path)
            
            # Usar ffmpeg para convertir desde raw PCM
            cmd = [
                "ffmpeg", "-y",
                "-f", "s16le",  # Formato: signed 16-bit little endian
                "-ar", str(audio_result.sample_rate),  # Sample rate
                "-ac", "1",  # Mono
                "-i", raw_path,  # Input
                "-ar", "24000",  # Resample a 24kHz
                "-ac", "1"  # Asegurar mono
            ]
            
            if output_format.lower() == "mp3":
                cmd.extend(["-b:a", "128k", output_path])
            elif output_format.lower() in ["ogg", "opus"]:
                cmd.extend(["-c:a", "libopus", "-b:a", "24k", output_path])
            else:
                cmd.extend([output_path])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Limpiar archivo raw
            os.remove(raw_path)
            
            if result.returncode != 0:
                logger.error(f"ffmpeg error: {result.stderr}")
                raise RuntimeError(f"ffmpeg conversion failed: {result.stderr[:200]}")
            
            # Leer el archivo convertido
            with open(output_path, 'rb') as f:
                audio_bytes = f.read()
            
            return base64.b64encode(audio_bytes).decode('utf-8')
            
        finally:
            # Limpiar archivo de salida si existe
            if os.path.exists(output_path):
                os.remove(output_path)
    
    def save_audio(
        self,
        audio_result: AudioResult,
        output_path: str,
        output_format: str = "wav"
    ) -> str:
        """
        Guarda audio en archivo.
        
        Args:
            audio_result: Resultado de generación
            output_path: Ruta de salida
            output_format: Formato de salida
        
        Returns:
            Ruta del archivo guardado
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Guardar en formato original
        temp_path = output_path.with_suffix('.wav')
        sf.write(str(temp_path), audio_result.audio_data, audio_result.sample_rate)
        
        # Convertir si es necesario
        if output_format != "wav":
            audio = AudioSegment.from_wav(str(temp_path))
            final_path = output_path.with_suffix(f'.{output_format}')
            audio.export(str(final_path), format=output_format)
            temp_path.unlink()  # Eliminar temporal
            return str(final_path)
        
        return str(temp_path)