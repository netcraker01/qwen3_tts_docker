#!/usr/bin/env python3
"""
Script de descarga de modelos para Docker build.
Descarga TODOS los modelos necesarios durante el build del contenedor.
"""
import os
import sys
import shutil
from pathlib import Path
from huggingface_hub import snapshot_download, hf_hub_download

# Directorio de caché - debe coincidir con HF_HOME en el contenedor
CACHE_DIR = Path("/app/models")

# Modelos a descargar (1.7B por defecto, se pueden cambiar via env var)
MODELS_1_7B = [
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice", 
    "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
]

MODELS_0_6B = [
    "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
    "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
    "Qwen/Qwen3-TTS-12Hz-0.6B-VoiceDesign",
]

REQUIRED_TOKENIZER_FILES = [
    "preprocessor_config.json",
    "configuration.json", 
    "model.safetensors"
]


def find_model_snapshot(model_name: str) -> Path:
    """Encuentra el directorio snapshot de un modelo descargado."""
    model_dirs = list(CACHE_DIR.glob(f"models--Qwen--{model_name}/snapshots/*"))
    return model_dirs[0] if model_dirs else None


def download_model(repo_id: str) -> bool:
    """Descarga un modelo completo de HuggingFace."""
    model_name = repo_id.split("/")[-1]
    print(f"\n{'='*70}")
    print(f"Descargando: {model_name}")
    print(f"{'='*70}")
    
    try:
        # Descargar modelo completo
        local_path = snapshot_download(
            repo_id=repo_id,
            cache_dir=CACHE_DIR,
            local_dir_use_symlinks=False,
            resume_download=True,
        )
        print(f"  ✓ Modelo descargado en: {local_path}")
        return True
    except Exception as e:
        print(f"  ✗ Error descargando {model_name}: {e}")
        return False


def fix_speech_tokenizer(repo_id: str) -> bool:
    """
    Asegura que los archivos del speech_tokenizer estén correctamente ubicados.
    A veces los archivos se descargan pero no están en el lugar correcto.
    """
    model_name = repo_id.split("/")[-1]
    snapshot_dir = find_model_snapshot(model_name)
    
    if not snapshot_dir:
        print(f"  ⚠ Modelo {model_name} no encontrado en caché")
        return False
    
    tokenizer_dir = snapshot_dir / "speech_tokenizer"
    tokenizer_dir.mkdir(parents=True, exist_ok=True)
    
    # Verificar archivos faltantes
    missing_files = []
    for filename in REQUIRED_TOKENIZER_FILES:
        filepath = tokenizer_dir / filename
        if not filepath.exists():
            missing_files.append(filename)
    
    if not missing_files:
        print(f"  ✓ speech_tokenizer completo")
        return True
    
    print(f"  → Descargando archivos faltantes: {missing_files}")
    
    all_ok = True
    for filename in missing_files:
        try:
            downloaded = hf_hub_download(
                repo_id=repo_id,
                filename=f"speech_tokenizer/{filename}",
                cache_dir=CACHE_DIR,
                local_dir_use_symlinks=False,
                force_download=True
            )
            dest = tokenizer_dir / filename
            if Path(downloaded).resolve() != dest.resolve():
                shutil.copy2(downloaded, dest)
            print(f"    ✓ {filename}")
        except Exception as e:
            print(f"    ✗ Error en {filename}: {e}")
            all_ok = False
    
    return all_ok


def copy_to_hub_cache(repo_id: str) -> bool:
    """
    Copia los modelos descargados a la ruta hub/ donde HuggingFace los busca en runtime.
    Esto evita problemas de ruta cuando el contenedor se ejecuta.
    """
    model_name = repo_id.split("/")[-1]
    
    # Ruta origen (donde se descargó durante build)
    src_pattern = CACHE_DIR / f"models--Qwen--{model_name}"
    src_dirs = list(src_pattern.glob("snapshots/*"))
    if not src_dirs:
        print(f"  ⚠ No se encontró modelo {model_name} para copiar a hub/")
        return False
    
    src_snapshot = src_dirs[0]
    snapshot_id = src_snapshot.name
    
    # Ruta destino (donde HuggingFace busca en runtime)
    hub_dir = CACHE_DIR / "hub" / f"models--Qwen--{model_name}" / "snapshots" / snapshot_id
    hub_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"  Copiando a hub/ para runtime...")
    
    try:
        # Copiar archivos principales
        main_files = [
            "config.json", "generation_config.json", "model.safetensors", 
            "model.safetensors.index.json", "preprocessor_config.json",
            "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json"
        ]
        for file in main_files:
            src_file = src_snapshot / file
            if src_file.exists() and not (hub_dir / file).exists():
                shutil.copy2(src_file, hub_dir / file)
        
        # Crear y copiar directorio speech_tokenizer
        src_tokenizer = src_snapshot / "speech_tokenizer"
        dst_tokenizer = hub_dir / "speech_tokenizer"
        dst_tokenizer.mkdir(parents=True, exist_ok=True)
        
        for file in REQUIRED_TOKENIZER_FILES:
            src_file = src_tokenizer / file
            if src_file.exists() and not (dst_tokenizer / file).exists():
                shutil.copy2(src_file, dst_tokenizer / file)
        
        print(f"    ✓ Modelo copiado a hub/{model_name}")
        return True
    except Exception as e:
        print(f"    ✗ Error copiando a hub/: {e}")
        return False


def verify_model(repo_id: str) -> bool:
    """Verifica que un modelo esté completamente instalado."""
    model_name = repo_id.split("/")[-1]
    snapshot_dir = find_model_snapshot(model_name)
    
    if not snapshot_dir:
        return False
    
    # Verificar archivos principales
    main_files = ["config.json", "model.safetensors"]
    has_main = any((snapshot_dir / f).exists() for f in main_files)
    
    # Verificar speech_tokenizer
    tokenizer_dir = snapshot_dir / "speech_tokenizer"
    has_tokenizer = all((tokenizer_dir / f).exists() for f in REQUIRED_TOKENIZER_FILES)
    
    return has_main and has_tokenizer


def main():
    print("="*70)
    print("Descarga de modelos Qwen3-TTS para Docker")
    print(f"Cache: {CACHE_DIR}")
    print("="*70)
    
    # Crear directorio de caché
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Determinar qué modelos descargar
    model_size = os.getenv("DOWNLOAD_MODEL_SIZE", "1.7B")
    models = MODELS_1_7B if model_size == "1.7B" else MODELS_0_6B
    
    print(f"\nDescargando modelos {model_size}...")
    print(f"Total: {len(models)} modelos")
    
    # Descargar todos los modelos
    success_count = 0
    for repo_id in models:
        if download_model(repo_id):
            success_count += 1
    
    # Corregir speech_tokenizer para todos
    print(f"\n{'='*70}")
    print("Verificando speech_tokenizer...")
    print(f"{'='*70}")
    
    for repo_id in models:
        fix_speech_tokenizer(repo_id)
    
    # Copiar modelos a hub/ para runtime
    print(f"\n{'='*70}")
    print("Copiando modelos a hub/ para runtime...")
    print(f"{'='*70}")
    
    for repo_id in models:
        copy_to_hub_cache(repo_id)
    
    # Verificación final
    print(f"\n{'='*70}")
    print("Verificación final")
    print(f"{'='*70}")
    
    all_ok = True
    for repo_id in models:
        model_name = repo_id.split("/")[-1]
        if verify_model(repo_id):
            print(f"  ✓ {model_name}: OK")
        else:
            print(f"  ✗ {model_name}: INCOMPLETO")
            all_ok = False
    
    print(f"\n{'='*70}")
    if all_ok and success_count == len(models):
        print(f"✅ Todos los modelos ({success_count}/{len(models)}) descargados correctamente")
        return 0
    else:
        print(f"⚠️  Solo {success_count}/{len(models)} modelos completos")
        return 1


if __name__ == "__main__":
    sys.exit(main())
