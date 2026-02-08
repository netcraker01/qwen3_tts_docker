#!/bin/bash
# Entrypoint script - Corrige archivos de modelos y luego inicia el servicio

echo "=========================================="
echo "Qwen3-TTS Service - Entrypoint"
echo "=========================================="

# Función para corregir archivos de un modelo
copy_model_files() {
    local model_name=$1
    local snapshot_id=$2
    
    local SRC="/app/models/models--Qwen--${model_name}/snapshots/${snapshot_id}/speech_tokenizer"
    local DST="/app/models/hub/models--Qwen--${model_name}/snapshots/${snapshot_id}/speech_tokenizer"
    
    if [ -d "$SRC" ] && [ ! -f "$DST/preprocessor_config.json" ]; then
        echo "  → Corrigiendo $model_name..."
        mkdir -p "$DST"
        cp "$SRC/preprocessor_config.json" "$DST/" 2>/dev/null
        cp "$SRC/configuration.json" "$DST/" 2>/dev/null
        cp -L "$SRC/model.safetensors" "$DST/" 2>/dev/null
        echo "  ✓ $model_name corregido"
    fi
}

# Verificar y corregir modelos si es necesario
echo "Verificando archivos de modelos..."

# Corregir CustomVoice model
copy_model_files "Qwen3-TTS-12Hz-1.7B-CustomVoice" "0c0e3051f131929182e2c023b9537f8b1c68adfe"

# Corregir VoiceDesign model  
copy_model_files "Qwen3-TTS-12Hz-1.7B-VoiceDesign" "5ecdb67327fd37bb2e042aab12ff7391903235d3"

# Corregir Base model
copy_model_files "Qwen3-TTS-12Hz-1.7B-Base" "fd4b254389122332181a7c3db7f27e918eec64e3"

echo "=========================================="
echo "Iniciando Qwen3-TTS Service..."
echo "=========================================="

# Iniciar el servidor
exec python3.10 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
