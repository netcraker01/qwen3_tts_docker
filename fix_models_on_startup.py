#!/usr/bin/env python3
"""
Script de corrección automática de modelos Qwen3-TTS al iniciar el contenedor.
Este script verifica que todos los archivos necesarios del speech_tokenizer estén presentes
y los descarga si faltan.
"""
import os
import sys
import shutil
import json
from pathlib import Path
from huggingface_hub import hf_hub_download, list_repo_files

# Directorio de caché de HuggingFace - debe coincidir con HF_HOME en Dockerfile
CACHE_DIR = os.getenv("HF_HOME", "/app/models")

# Modelos soportados con sus repositorios
MODELS = {
    "1.7B": {
        "voice_clone": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        "custom_voice": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        "voice_design": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
    },
    "0.6B": {
        "voice_clone": "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
        "custom_voice": "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
        "voice_design": "Qwen/Qwen3-TTS-12Hz-0.6B-VoiceDesign",
    }
}

# Archivos necesarios para el speech_tokenizer
REQUIRED_TOKENIZER_FILES = [
    "preprocessor_config.json",
    "configuration.json",
    "model.safetensors"
]


def find_model_snapshots(model_name):
    """
    Encuentra todos los snapshots disponibles para un modelo en el caché.
    """
    cache_path = Path(CACHE_DIR)
    model_pattern = f"models--Qwen--{model_name}"
    
    model_dirs = list(cache_path.glob(f"{model_pattern}/snapshots/*"))
    return model_dirs


def check_speech_tokenizer(snapshot_dir):
    """
    Verifica si el speech_tokenizer tiene todos los archivos necesarios.
    Retorna lista de archivos faltantes.
    """
    tokenizer_dir = Path(snapshot_dir) / "speech_tokenizer"
    missing = []
    
    for filename in REQUIRED_TOKENIZER_FILES:
        filepath = tokenizer_dir / filename
        if not filepath.exists():
            missing.append(filename)
    
    return missing


def download_tokenizer_file(repo_id, filename, snapshot_dir):
    """
    Descarga un archivo del speech_tokenizer desde HuggingFace.
    """
    try:
        print(f"    → Descargando {filename}...")
        
        # Descargar usando huggingface_hub
        downloaded_path = hf_hub_download(
            repo_id=repo_id,
            filename=f"speech_tokenizer/{filename}",
            cache_dir=CACHE_DIR,
            local_dir_use_symlinks=False,
            force_download=True
        )
        
        # El archivo se descarga al caché, necesitamos copiarlo al snapshot
        tokenizer_dir = Path(snapshot_dir) / "speech_tokenizer"
        tokenizer_dir.mkdir(parents=True, exist_ok=True)
        
        dest_path = tokenizer_dir / filename
        
        # Si el archivo descargado es un symlink, resolverlo
        downloaded_path = Path(downloaded_path).resolve()
        
        if downloaded_path.exists():
            shutil.copy2(str(downloaded_path), str(dest_path))
            print(f"      ✓ {filename} descargado y copiado")
            return True
        else:
            print(f"      ✗ Archivo descargado no encontrado: {downloaded_path}")
            return False
            
    except Exception as e:
        print(f"      ✗ Error descargando {filename}: {e}")
        return False


def fix_model(repo_id, snapshot_dirs):
    """
    Corrige los archivos faltantes del speech_tokenizer para un modelo.
    """
    model_name = repo_id.split("/")[-1]
    print(f"\n  Procesando: {model_name}")
    
    if not snapshot_dirs:
        print(f"    ⚠ Modelo no descargado aún (se descargará bajo demanda)")
        return True
    
    all_fixed = True
    
    for snapshot_dir in snapshot_dirs:
        print(f"    Snapshot: {snapshot_dir.name}")
        
        missing = check_speech_tokenizer(snapshot_dir)
        
        if not missing:
            print(f"    ✓ Todos los archivos del speech_tokenizer están presentes")
            continue
        
        print(f"    → Faltan archivos: {missing}")
        
        # Descargar archivos faltantes
        for filename in missing:
            if not download_tokenizer_file(repo_id, filename, snapshot_dir):
                all_fixed = False
    
    return all_fixed


def verify_all_models():
    """
    Verifica el estado de todos los modelos y retorna reporte.
    """
    print("\n" + "="*70)
    print("Verificación de modelos")
    print("="*70)
    
    all_ok = True
    
    for size, models in MODELS.items():
        print(f"\n  Modelos {size}:")
        for model_type, repo_id in models.items():
            model_name = repo_id.split("/")[-1]
            snapshot_dirs = find_model_snapshots(model_name)
            
            if not snapshot_dirs:
                print(f"    • {model_type}: No descargado (se descargará bajo demanda)")
                continue
            
            # Verificar speech_tokenizer en el primer snapshot
            missing = check_speech_tokenizer(snapshot_dirs[0])
            
            if missing:
                print(f"    ✗ {model_type}: Faltan archivos en speech_tokenizer")
                all_ok = False
            else:
                print(f"    ✓ {model_type}: OK")
    
    return all_ok


def main():
    print("="*70)
    print("Corrección automática de modelos Qwen3-TTS")
    print(f"Cache dir: {CACHE_DIR}")
    print("="*70)
    
    # Crear directorio de caché si no existe
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    # Procesar cada modelo
    all_success = True
    
    for size, models in MODELS.items():
        print(f"\n{'='*70}")
        print(f"Modelos {size}")
        print(f"{'='*70}")
        
        for model_type, repo_id in models.items():
            model_name = repo_id.split("/")[-1]
            snapshot_dirs = find_model_snapshots(model_name)
            
            if not fix_model(repo_id, snapshot_dirs):
                all_success = False
    
    # Verificación final
    print("\n" + "="*70)
    print("Resumen")
    print("="*70)
    
    if verify_all_models():
        print("\n✅ Todos los modelos están correctamente configurados")
        return 0
    else:
        print("\n⚠️  Algunos modelos tienen problemas pero se descargarán bajo demanda")
        return 0  # No fallar el inicio del contenedor


if __name__ == "__main__":
    sys.exit(main())
