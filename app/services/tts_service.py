

















































































































































































































































































































































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
        # Usar HF_HOME si está definido, o /app/models (ruta de los modelos pre-descargados)
        if cache_dir is None:
            cache_dir = os.getenv("HF_HOME", "/app/models")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_model_size = default_model_size
        # Flash attention requiere compilación con nvcc, deshabilitado por defecto
        self.use_flash_attention = False  # use_flash_attention and torch.cuda.is_available()
        
        # Cache de modelos cargados
        self._models: Dict[str, Any] = {}
        self._voice_clone_prompts: Dict[str, Any] = {}
        
        # Configuración de device - optimizaciones para velocidad máxima
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # Usar float16 para máxima velocidad en RTX 3060/3060Ti 12GB
        # Cuando se usa CPU offload, float16 sigue funcionando bien
        self.dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        
        # Configuración de memoria
        self.cpu_offload_enabled = True  # Habilitar offload a CPU por defecto
        self.vram_safety_margin = 1.0    # Margen de seguridad en GB
        
        # Optimizaciones de PyTorch para máximo rendimiento
        if self.device == "cuda":
            # Habilitar cudnn benchmarking para operaciones más rápidas
            torch.backends.cudnn.benchmark = True
            # Permitir operaciones TF32 para más velocidad en Ampere+
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
            # Optimizaciones adicionales de memoria
            torch.backends.cuda.sdp_kernel(
                enable_flash=True,
                enable_math=True,
                enable_mem_efficient=True
            )
        
        # Pool de workers para procesamiento paralelo de I/O
        self._executor = None
        self._batch_queue = []
        self._batch_size = 4  # Procesar hasta 4 requests en batch
        
        logger.info(f"TTSService inicializado - Device: {self.device}, Dtype: {self.dtype}")
        logger.info(f"Flash Attention: {self.use_flash_attention}")
        logger.info(f"Cache dir: {self.cache_dir}")
        logger.info(f"Batch size: {self._batch_size}")
    
    def _fix_speech_tokenizer_for_model(self, model_id: str) -> bool:
        """
        Verifica y corrige los archivos del speech_tokenizer para un modelo específico.
        Retorna True si la corrección fue exitosa o no era necesaria.
        """
        try:
            import shutil
            from huggingface_hub import hf_hub_download
            from pathlib import Path
            
            model_name = model_id.split("/")[-1]
            
            # Buscar el directorio del modelo en el caché
            cache_path = Path(self.cache_dir)
            model_dirs = list(cache_path.glob(f"models--Qwen--{model_name}/snapshots/*"))
            
            if not model_dirs:
                logger.info(f"Modelo {model_name} no descargado aún, no se requiere corrección")
                return True
            
            snapshot_dir = model_dirs[0]
            tokenizer_dir = snapshot_dir / "speech_tokenizer"
            
            # Archivos necesarios
            required_files = ["preprocessor_config.json", "configuration.json", "model.safetensors"]
            missing_files = []
            
            for filename in required_files:
                filepath = tokenizer_dir / filename
                if not filepath.exists():
                    missing_files.append(filename)
            
            if not missing_files:
                logger.info(f"✓ speech_tokenizer completo para {model_name}")
                return True
            
            logger.warning(f"Faltan archivos en speech_tokenizer para {model_name}: {missing_files}")
            logger.info(f"Descargando archivos faltantes...")
            
            # Crear directorio si no existe
            tokenizer_dir.mkdir(parents=True, exist_ok=True)
            
            all_ok = True
            for filename in missing_files:
                try:
                    logger.info(f"  Descargando speech_tokenizer/{filename}...")
                    downloaded_path = hf_hub_download(
                        repo_id=model_id,
                        filename=f"speech_tokenizer/{filename}",
                        cache_dir=self.cache_dir,
                        local_dir_use_symlinks=False,
                        force_download=True
                    )
                    
                    downloaded_path = Path(downloaded_path)
                    dest_path = tokenizer_dir / filename
                    
                    # Si el archivo descargado es el mismo que el destino (symlink), ya está listo
                    if downloaded_path.resolve() == dest_path.resolve():
                        logger.info(f"  ✓ {filename} ya está en el lugar correcto")
                    elif downloaded_path.exists():
                        shutil.copy2(str(downloaded_path), str(dest_path))
                        logger.info(f"  ✓ {filename} descargado y copiado")
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

    def _estimate_model_memory(self, model_size: str) -> float:
        """
        Estima la memoria VRAM necesaria para un modelo en GB.
        
        Args:
            model_size: "1.7B" o "0.6B"
            
        Returns:
            Memoria estimada en GB
        """
        # Estimaciones basadas en el tamaño del modelo en FP16
        # 1.7B params ~ 3.4GB + overhead (~0.5GB) = ~4GB
        # 0.6B params ~ 1.2GB + overhead (~0.3GB) = ~1.5GB
        memory_estimates = {
            "1.7B": 4.0,  # GB
            "0.6B": 1.5   # GB
        }
        return memory_estimates.get(model_size, 4.0)
    
    def _get_available_vram(self) -> float:
        """
        Obtiene la VRAM disponible en GB.
        
        Returns:
            VRAM disponible en GB
        """
        if not torch.cuda.is_available():
            return 0.0
        
        # Obtener memoria libre en el dispositivo
        free_memory = torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_allocated(0)
        return free_memory / 1e9  # Convertir a GB
    
    def _should_use_cpu_offload(self, model_size: str, safety_margin: float = 1.0) -> bool:
        """
        Determina si se debe usar CPU offload basado en la VRAM disponible.
        
        Args:
            model_size: "1.7B" o "0.6B"
            safety_margin: Margen de seguridad adicional en GB
            
        Returns:
            True si se debe usar CPU offload
        """
        if not torch.cuda.is_available():
            return True
        
        available_vram = self._get_available_vram()
        required_memory = self._estimate_model_memory(model_size) + safety_margin
        
        logger.info(f"VRAM disponible: {available_vram:.2f} GB, Requerida: {required_memory:.2f} GB")
        
        return available_vram < required_memory
    
    def _get_model(self, model_type: str, model_size: Optional[str] = None, force_reload: bool = False) -> Any:
        """
        Obtiene un modelo, cargándolo si es necesario (lazy loading).
        Soporta offload a CPU/RAM automático cuando no hay suficiente VRAM.
        
        Args:
            model_type: Tipo de modelo ('custom_voice', 'voice_design', 'voice_clone')
            model_size: Tamaño del modelo a usar ('1.7B' o '0.6B')
            force_reload: Si es True, limpia memoria antes de cargar
        
        Returns:
            Modelo Qwen3TTS cargado
        """
        if Qwen3TTSModel is None:
            raise RuntimeError("qwen-tts no está instalado")
        
        size = model_size or self.default_model_size
        cache_key = f"{size}_{model_type}"
        
        # Siempre limpiar memoria antes de cargar un modelo para evitar OOM
        if torch.cuda.is_available():
            logger.info("Limpiando memoria CUDA antes de cargar modelo...")
            
            # Liberar TODOS los modelos anteriores para evitar acumulación de memoria
            if self._models:
                logger.info(f"Liberando {len(self._models)} modelos previos de memoria...")
                self._models.clear()
            
            # Forzar garbage collection y limpiar caché CUDA
            import gc
            gc.collect()
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            
            # Esperar un momento para que la memoria se libere completamente
            import time
            time.sleep(0.5)
            
            logger.info(f"Memoria CUDA después de limpieza: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
        
        if cache_key not in self._models:
            model_id = self.MODELS[size][model_type]
            logger.info(f"Cargando modelo: {model_id}")
            
            # Determinar si necesitamos CPU offload
            use_cpu_offload = self._should_use_cpu_offload(size)
            
            if use_cpu_offload and torch.cuda.is_available():
                logger.warning(f"VRAM insuficiente para modelo {size}. Usando CPU/RAM offload.")
                logger.warning(f"Esto será más lento pero permitirá usar el modelo.")
            
            # Intentar cargar con reintentos y corrección automática
            max_retries = 3
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    # Configuración de carga del modelo
                    load_kwargs = {
                        "cache_dir": str(self.cache_dir),
                        "dtype": self.dtype,  # Usar dtype en lugar de torch_dtype (deprecado)
                        "low_cpu_mem_usage": True,
                    }
                    
                    # Configurar device_map según la disponibilidad de VRAM
                    if torch.cuda.is_available():
                        if use_cpu_offload:
                            # Estrategia: Cargar completamente en CPU para evitar OOM
                            # Luego mover capas a GPU bajo demanda durante inferencia
                            logger.warning(f"Cargando modelo {size} en CPU debido a VRAM insuficiente...")
                            load_kwargs["device_map"] = "cpu"
                            load_kwargs["offload_folder"] = str(self.cache_dir / "offload")
                            
                            # Crear directorio de offload si no existe
                            offload_dir = self.cache_dir / "offload"
                            offload_dir.mkdir(parents=True, exist_ok=True)
                            
                            logger.info(f"Configuración CPU offload: device_map=cpu, offload_folder={offload_dir}")
                        else:
                            # Cargar completamente en GPU
                            load_kwargs["device_map"] = "cuda:0"
                    else:
                        # Sin GPU, cargar en CPU
                        load_kwargs["device_map"] = "cpu"
                    
                    model = Qwen3TTSModel.from_pretrained(
                        model_id,
                        **load_kwargs
                    )
                    
                    # Si cargamos en CPU pero hay GPU disponible, intentar usar GPU para inferencia
                    if use_cpu_offload and torch.cuda.is_available():
                        logger.info("Modelo cargado en CPU. Intentando optimizar para GPU...")
                        try:
                            # Algunos modelos soportan .to() después de cargar
                            # o tienen métodos para mover a device específico
                            if hasattr(model, 'to'):
                                # Mover solo si el modelo lo permite
                                logger.info("Moviendo modelo a GPU para inferencia más rápida...")
                                model = model.to("cuda")
                        except Exception as move_error:
                            logger.warning(f"No se pudo mover modelo a GPU: {move_error}")
                            logger.info("El modelo permanecerá en CPU. Será más lento pero funcionará.")
                    
                    self._models[cache_key] = model
                    
                    # Log de dónde se cargó el modelo
                    if hasattr(model, 'hf_device_map'):
                        logger.info(f"Modelo distribuido en dispositivos: {model.hf_device_map}")
                    
                    logger.info(f"Modelo {model_id} cargado exitosamente")
                    
                    if torch.cuda.is_available():
                        logger.info(f"Memoria CUDA después de carga: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
                    
                    return self._models[cache_key]
                    
                except Exception as e:
                    last_error = e
                    error_msg = str(e)
                    logger.error(f"Error cargando modelo {model_id} (intento {attempt + 1}/{max_retries}): {e}")
                    
                    # Si es error de memoria CUDA, intentar con CPU offload
                    if "CUDA out of memory" in error_msg and torch.cuda.is_available() and not use_cpu_offload:
                        logger.warning("Error de memoria CUDA detectado. Intentando con CPU offload...")
                        use_cpu_offload = True
                        # Limpiar memoria antes de reintentar
                        torch.cuda.empty_cache()
                        torch.cuda.synchronize()
                        import time
                        time.sleep(1)
                        continue
                    
                    # Si es error de speech_tokenizer, intentar corregir
                    if "speech_tokenizer" in error_msg and "preprocessor_config" in error_msg:
                        logger.info(f"Detectado error de speech_tokenizer. Intentando corrección...")
                        if self._fix_speech_tokenizer_for_model(model_id):
                            logger.info(f"Corrección aplicada. Reintentando carga...")
                            continue
                        else:
                            logger.error(f"No se pudo corregir speech_tokenizer")
                    
                    # Si es el último intento, salir del loop y lanzar error
                    if attempt == max_retries - 1:
                        break
                    
                    # Esperar antes de reintentar
                    import time
                    time.sleep(1)
            
            # Si llegamos aquí, todos los intentos fallaron
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            raise RuntimeError(f"No se pudo cargar el modelo {model_id} después de {max_retries} intentos: {last_error}")
        
        return self._models[cache_key]
    
    def get_loaded_models(self) -> List[str]:
        """Retorna lista de modelos actualmente cargados."""
        return list(self._models.keys())
    
    def _cleanup_memory(self):
        """Limpia memoria CUDA antes de operaciones pesadas."""
        if torch.cuda.is_available():
            logger.info("Limpiando memoria CUDA...")
            
            # Liberar todos los modelos
            if self._models:
                self._models.clear()
            
            # Limpiar caché y forzar sincronización
            import gc
            gc.collect()
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            
            # Pequeña pausa para asegurar liberación
            import time
            time.sleep(0.3)
            
            logger.info(f"Memoria CUDA limpia: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
    
    def _immediate_cleanup(self):
        """Limpieza inmediata después de generación para liberar memoria rápido."""
        if torch.cuda.is_available():
            logger.info("Limpieza inmediata post-generación...")
            
            # Liberar modelos inmediatamente
            if self._models:
                self._models.clear()
            
            # Forzar garbage collection
            import gc
            gc.collect()
            
            # Vaciar caché CUDA múltiples veces para asegurar liberación
            for _ in range(3):
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                import time
                time.sleep(0.2)
            
            logger.info(f"Memoria post-limpieza: {torch.cuda.memory_allocated() / 1e9:.2f} GB libre")
    
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
        model_size: Optional[str] = None,
        generation_params: Optional[Dict] = None
    ) -> AudioResult:
        """
        Genera voz usando un personaje preestablecido.
        
        Args:
            text: Texto a convertir
            speaker: Nombre del speaker (Vivian, Ryan, etc.)
            language: Idioma del texto
            instruction: Instrucción opcional para modificar estilo/emoción
            model_size: Tamaño del modelo a usar
            generation_params: Parámetros de generación (temperature, top_p, etc.)
        
        Returns:
            AudioResult con el audio generado
        """
        # Forzar liberación de memoria antes de generar
        self._cleanup_memory()
        
        model = self._get_model("custom_voice", model_size)
        
        logger.info(f"Generando Custom Voice - Speaker: {speaker}, Lang: {language}")
        start_time = time.time()
        
        # Preparar kwargs con parámetros de generación
        kwargs = {}
        if generation_params:
            kwargs.update(generation_params)
            logger.info(f"Usando parámetros de generación: {generation_params}")
        
        try:
            # Usar no_grad para reducir uso de memoria
            with torch.no_grad():
                wavs, sr = model.generate_custom_voice(
                    text=text,
                    language=language,
                    speaker=speaker,
                    instruct=instruction,
                    **kwargs
                )
            
            audio_data = wavs[0]
            duration = len(audio_data) / sr
            processing_time = time.time() - start_time
            
            logger.info(f"Audio generado: {duration:.2f}s en {processing_time:.2f}s")
            
            result = AudioResult(
                audio_data=audio_data,
                sample_rate=sr,
                duration_seconds=duration,
                model_used=f"{model_size or self.default_model_size}_custom_voice"
            )
            
            # LIMPIAR MEMORIA INMEDIATAMENTE DESPUÉS de generar
            self._immediate_cleanup()
            
            return result
            
        except Exception as e:
            logger.error(f"Error en generate_custom_voice: {e}")
            # También limpiar en caso de error
            self._immediate_cleanup()
            raise
    
    # ============================================================
    # VOICE DESIGN
    # ============================================================
    
    def generate_voice_design(
        self,
        text: str,
        voice_description: str,
        language: str = "Spanish",
        model_size: Optional[str] = None,
        generation_params: Optional[Dict] = None
    ) -> AudioResult:
        """
        Genera voz mediante descripción de texto.
        
        Args:
            text: Texto a convertir
            voice_description: Descripción detallada de la voz deseada
            language: Idioma del texto
            model_size: Tamaño del modelo a usar
            generation_params: Parámetros de generación (temperature, top_p, etc.)
        
        Returns:
            AudioResult con el audio generado
        """
        # Forzar liberación de memoria antes de generar
        self._cleanup_memory()
        
        model = self._get_model("voice_design", model_size)
        
        logger.info(f"Generando Voice Design - Lang: {language}")
        logger.debug(f"Voice description: {voice_description[:100]}...")
        start_time = time.time()
        
        # Preparar kwargs con parámetros de generación
        kwargs = {}
        if generation_params:
            kwargs.update(generation_params)
            logger.info(f"Usando parámetros de generación: {generation_params}")
        
        try:
            with torch.no_grad():
                wavs, sr = model.generate_voice_design(
                    text=text,
                    language=language,
                    instruct=voice_description,
                    **kwargs
                )
            
            audio_data = wavs[0]
            duration = len(audio_data) / sr
            processing_time = time.time() - start_time
            
            logger.info(f"Audio generado: {duration:.2f}s en {processing_time:.2f}s")
            
            result = AudioResult(
                audio_data=audio_data,
                sample_rate=sr,
                duration_seconds=duration,
                model_used=f"{model_size or self.default_model_size}_voice_design"
            )
            
            # LIMPIAR MEMORIA INMEDIATAMENTE DESPUÉS de generar
            self._immediate_cleanup()
            
            return result
            
        except Exception as e:
            logger.error(f"Error en generate_voice_design: {e}")
            # También limpiar en caso de error
            self._immediate_cleanup()
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
        # LIMPIEZA AGRESIVA antes de crear prompt
        logger.info("Limpieza previa para create_voice_clone_prompt...")
        self._immediate_cleanup()
        
        # Usar force_reload=True para liberar memoria antes de cargar modelo de clone
        model = self._get_model("voice_clone", model_size, force_reload=True)
        
        prompt_id = f"{hash(ref_audio_path)}_{hash(ref_text)}"
        
        if prompt_id not in self._voice_clone_prompts:
            logger.info(f"Creando voice clone prompt: {prompt_id}")
            
            try:
                # Descargar si es URL
                if ref_audio_path.startswith("http"):
                    audio_path = self._download_audio(ref_audio_path)
                else:
                    audio_path = ref_audio_path
                
                with torch.no_grad():
                    prompt = model.create_voice_clone_prompt(
                        ref_audio=audio_path,
                        ref_text=ref_text
                    )
                
                self._voice_clone_prompts[prompt_id] = prompt
                logger.info(f"Voice clone prompt creado: {prompt_id}")
                
                # LIMPIAR MEMORIA INMEDIATAMENTE DESPUÉS de crear el prompt
                self._immediate_cleanup()
                
            except Exception as e:
                logger.error(f"Error creando voice clone prompt: {e}")
                # También limpiar en caso de error
                self._immediate_cleanup()
                raise
        
        return prompt_id
    
    def generate_voice_clone(
        self,
        text: str,
        voice_clone_prompt_id: str,
        language: str = "Spanish",
        model_size: Optional[str] = None,
        generation_params: Optional[Dict] = None
    ) -> AudioResult:
        """
        Genera voz clonada usando un prompt previamente creado.
        
        Args:
            text: Texto a convertir
            voice_clone_prompt_id: ID del prompt de clonación
            language: Idioma del texto
            model_size: Tamaño del modelo a usar
            generation_params: Parámetros de generación (temperature, top_p, etc.)
        
        Returns:
            AudioResult con el audio generado
        """
        size = model_size or self.default_model_size
        
        # Usar force_reload=True para liberar memoria si es necesario
        model = self._get_model("voice_clone", size, force_reload=True)
        
        if voice_clone_prompt_id not in self._voice_clone_prompts:
            raise ValueError(f"Voice clone prompt no encontrado: {voice_clone_prompt_id}. "
                           f"Debes crear el prompt primero usando create_voice_clone_prompt.")
        
        prompt = self._voice_clone_prompts[voice_clone_prompt_id]
        
        # Validar compatibilidad del prompt con el modelo
        # Los prompts creados con 1.7B no funcionan con 0.6B y viceversa
        prompt_cache_key = f"{voice_clone_prompt_id}_{size}"
        if hasattr(prompt, 'shape') or hasattr(prompt, '__len__'):
            # Intentar detectar incompatibilidad por dimensiones
            try:
                if torch.is_tensor(prompt):
                    # Si es un tensor, verificar dimensiones típicas
                    if prompt.dim() >= 2:
                        last_dim = prompt.shape[-1]
                        if size == "0.6B" and last_dim == 2048:
                            raise ValueError(
                                f"El prompt fue creado con el modelo 1.7B (dimensión {last_dim}) "
                                f"pero estás usando el modelo 0.6B. "
                                f"Debes recrear el prompt con el modelo 0.6B usando create_voice_clone_prompt."
                            )
                        elif size == "1.7B" and last_dim == 1024:
                            raise ValueError(
                                f"El prompt fue creado con el modelo 0.6B (dimensión {last_dim}) "
                                f"pero estás usando el modelo 1.7B. "
                                f"Debes recrear el prompt con el modelo 1.7B usando create_voice_clone_prompt."
                            )
            except Exception as e:
                if "Debes recrear el prompt" in str(e):
                    raise
                # Si hay otro error, continuar y dejar que falle más adelante si es necesario
                pass
        
        logger.info(f"Generando Voice Clone - Lang: {language}")
        start_time = time.time()
        
        # Preparar kwargs con parámetros de generación
        kwargs = {}
        if generation_params:
            kwargs.update(generation_params)
            logger.info(f"Usando parámetros de generación: {generation_params}")
        
        try:
            with torch.no_grad():
                wavs, sr = model.generate_voice_clone(
                    text=text,
                    language=language,
                    voice_clone_prompt=prompt,
                    **kwargs
                )
            
            audio_data = wavs[0]
            duration = len(audio_data) / sr
            processing_time = time.time() - start_time
            
            logger.info(f"Audio generado: {duration:.2f}s en {processing_time:.2f}s")
            
            result = AudioResult(
                audio_data=audio_data,
                sample_rate=sr,
                duration_seconds=duration,
                model_used=f"{model_size or self.default_model_size}_voice_clone"
            )
            
            # LIMPIAR MEMORIA INMEDIATAMENTE DESPUÉS de generar
            self._immediate_cleanup()
            
            return result
            
        except Exception as e:
            logger.error(f"Error en generate_voice_clone: {e}")
            # También limpiar en caso de error
            self._immediate_cleanup()
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
        Soporta formatos: WAV, MP3, OGG, OPUS.
        
        Args:
            text: Texto a convertir
            ref_audio_file: Contenido del archivo de audio (bytes)
            ref_text: Texto correspondiente al audio
            language: Idioma del texto
            model_size: Tamaño del modelo a usar (0.6B recomendado para RTX 3060)
        
        Returns:
            AudioResult con el audio generado
        """
        import subprocess
        
        # Para voice clone, usar 0.6B por defecto si no se especifica (menos uso de memoria)
        size = model_size or "0.6B"
        
        # Limpieza agresiva de memoria antes de voice clone
        logger.info("Limpieza agresiva de memoria antes de voice clone...")
        self._cleanup_memory()
        
        # Doble limpieza para voice clone (operación más pesada)
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            import time
            time.sleep(1.0)  # Esperar 1 segundo completo
        
        logger.info(f"Memoria antes de voice clone: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
        
        # Guardar archivo temporal con extensión genérica
        with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as tmp_input:
            tmp_input.write(ref_audio_file)
            input_path = tmp_input.name
        
        # Crear archivo de salida WAV
        wav_path = input_path + ".wav"
        
        try:
            # Convertir a WAV usando ffmpeg (soporta cualquier formato de entrada)
            logger.info(f"Convirtiendo archivo de audio a WAV...")
            cmd = [
                "ffmpeg", "-y",
                "-i", input_path,  # Input (cualquier formato)
                "-ar", "24000",    # Sample rate 24kHz
                "-ac", "1",        # Mono
                "-c:a", "pcm_s16le",  # PCM 16-bit little endian
                wav_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"ffmpeg conversion error: {result.stderr}")
                raise RuntimeError(f"No se pudo convertir el audio a WAV: {result.stderr[:200]}")
            
            logger.info(f"Audio convertido exitosamente a WAV: {wav_path}")
            
            # Crear prompt y generar usando el WAV convertido
            prompt_id = self.create_voice_clone_prompt(wav_path, ref_text, size)
            
            # LIMPIEZA EXTRA entre crear prompt y generar
            logger.info("Limpieza entre prompt y generación...")
            self._immediate_cleanup()
            
            result = self.generate_voice_clone(text, prompt_id, language, size)
            
            # LIMPIEZA FINAL después de todo el proceso de voice clone
            logger.info("Limpieza final post-voice-clone...")
            self._immediate_cleanup()
            
            return result
            
        except Exception as e:
            # Asegurar limpieza en caso de error
            logger.error(f"Error en voice clone from file: {e}")
            self._immediate_cleanup()
            raise
        finally:
            # Limpiar archivos temporales
            for path in [input_path, wav_path]:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        pass
    
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