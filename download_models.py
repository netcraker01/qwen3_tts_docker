#!/usr/bin/env python3
"""
Script para descargar modelos Qwen3-TTS manualmente
"""
import os
from huggingface_hub import snapshot_download

MODELS = [
    "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign", 
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
]

CACHE_DIR = "/app/models"

def download_model(model_id):
    print(f"\n{'='*60}")
    print(f"Descargando: {model_id}")
    print(f"{'='*60}")
    
    try:
        local_path = snapshot_download(
            repo_id=model_id,
            cache_dir=CACHE_DIR,
            local_dir_use_symlinks=False,
            resume_download=True
        )
        print(f"✅ Descargado en: {local_path}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("Descargando modelos Qwen3-TTS...")
    print(f"Destino: {CACHE_DIR}")
    
    # Crear directorio si no existe
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    success_count = 0
    for model in MODELS:
        if download_model(model):
            success_count += 1
    
    print(f"\n{'='*60}")
    print(f"Completado: {success_count}/{len(MODELS)} modelos descargados")
    print(f"{'='*60}")