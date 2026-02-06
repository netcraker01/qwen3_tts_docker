#!/usr/bin/env python3
"""
Script para descargar modelos Qwen3-TTS manualmente - Versión robusta
"""
import os
import sys
from huggingface_hub import snapshot_download, hf_hub_download
from huggingface_hub.utils import RepositoryNotFoundError

MODELS = [
    "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign", 
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
]

CACHE_DIR = "/app/models"

def download_model(model_id):
    print(f"\n{'='*70}")
    print(f"Descargando: {model_id}")
    print(f"{'='*70}")
    
    try:
        # Descargar a caché de HuggingFace (más confiable)
        local_path = snapshot_download(
            repo_id=model_id,
            cache_dir=CACHE_DIR,
            local_dir_use_symlinks=False,
            force_download=False,
            local_files_only=False,
        )
        print(f"✅ Descargado en: {local_path}")
        return True
    except RepositoryNotFoundError:
        print(f"❌ Error: Modelo no encontrado en HuggingFace")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def download_single_file(repo_id, filename):
    """Descargar un archivo específico (útil para verificar conectividad)"""
    try:
        path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            cache_dir=CACHE_DIR,
            local_dir_use_symlinks=False,
        )
        print(f"  ✓ {filename}")
        return path
    except Exception as e:
        print(f"  ✗ {filename}: {e}")
        return None

if __name__ == "__main__":
    print("="*70)
    print("Descargando modelos Qwen3-TTS")
    print(f"Destino: {CACHE_DIR}")
    print(f"HuggingFace Cache: {os.getenv('HF_HOME', 'default')}")
    print("="*70)
    
    # Crear directorio si no existe
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    # Verificar conectividad primero
    print("\nVerificando conectividad con HuggingFace...")
    test_file = download_single_file("Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice", "config.json")
    if test_file:
        print("✅ Conectividad OK")
    else:
        print("❌ No se pudo conectar a HuggingFace. Verifica tu conexión a internet.")
        sys.exit(1)
    
    success_count = 0
    for model in MODELS:
        if download_model(model):
            success_count += 1
        else:
            print(f"\n⚠️  Reintentando {model}...")
            if download_model(model):
                success_count += 1
    
    print(f"\n{'='*70}")
    print(f"Completado: {success_count}/{len(MODELS)} modelos descargados")
    print(f"{'='*70}")
    
    if success_count == len(MODELS):
        print("✅ Todos los modelos descargados correctamente")
        sys.exit(0)
    else:
        print("⚠️  Algunos modelos no se descargaron completamente")
        sys.exit(1)