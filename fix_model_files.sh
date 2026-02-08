#!/bin/bash
# Script para corregir archivos faltantes en modelos Qwen3-TTS
# Este script copia los archivos necesarios desde models/ a hub/

echo "Corrigiendo archivos de modelos..."

# Función para copiar archivos de un modelo
copy_model_files() {
    local model_name=$1
    local snapshot_id=$2
    
    local SRC="/app/models/models--Qwen--${model_name}/snapshots/${snapshot_id}/speech_tokenizer"
    local DST="/app/models/hub/models--Qwen--${model_name}/snapshots/${snapshot_id}/speech_tokenizer"
    
    if [ -d "$SRC" ]; then
        echo "Procesando $model_name..."
        mkdir -p "$DST"
        
        # Copiar archivos si existen
        if [ -f "$SRC/preprocessor_config.json" ]; then
            cp "$SRC/preprocessor_config.json" "$DST/"
            echo "  ✓ preprocessor_config.json copiado"
        fi
        
        if [ -f "$SRC/configuration.json" ]; then
            cp "$SRC/configuration.json" "$DST/"
            echo "  ✓ configuration.json copiado"
        fi
        
        if [ -f "$SRC/model.safetensors" ]; then
            cp -L "$SRC/model.safetensors" "$DST/"
            echo "  ✓ model.safetensors copiado"
        fi
        
        echo "  $model_name corregido"
    else
        echo "  $model_name no encontrado en cache"
    fi
}

# Corregir CustomVoice model
copy_model_files "Qwen3-TTS-12Hz-1.7B-CustomVoice" "0c0e3051f131929182e2c023b9537f8b1c68adfe"

# Corregir VoiceDesign model  
copy_model_files "Qwen3-TTS-12Hz-1.7B-VoiceDesign" "5ecdb67327fd37bb2e042aab12ff7391903235d3"

# Buscar y corregir Base model si existe
BASE_DIR="/app/models/models--Qwen--Qwen3-TTS-12Hz-1.7B-Base/snapshots"
if [ -d "$BASE_DIR" ]; then
    BASE_SNAPSHOT=$(ls "$BASE_DIR" | head -1)
    if [ -n "$BASE_SNAPSHOT" ]; then
        copy_model_files "Qwen3-TTS-12Hz-1.7B-Base" "$BASE_SNAPSHOT"
    fi
fi

echo ""
echo "Corrección completada. Los modelos deberían funcionar correctamente ahora."
