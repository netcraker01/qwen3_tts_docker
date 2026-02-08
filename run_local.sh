#!/bin/bash
# Script para ejecutar el servicio Qwen3-TTS localmente (sin Docker)

set -e

echo "=========================================="
echo "Qwen3-TTS Service - Ejecución Local"
echo "=========================================="

# Cargar variables de entorno desde .env
if [ -f .env ]; then
    echo "Cargando configuración desde .env..."
    export $(grep -v '^#' .env | xargs)
fi

# Verificar que HF_HOME esté configurado
if [ -z "$HF_HOME" ]; then
    echo "⚠️  ADVERTENCIA: HF_HOME no está configurado"
    echo "   Configurando HF_HOME=/root/qwen3_tts_docker/models/hub"
    export HF_HOME=/root/qwen3_tts_docker/models/hub
fi

echo ""
echo "Configuración:"
echo "  HF_HOME: $HF_HOME"
echo "  CUDA_VISIBLE_DEVICES: $CUDA_VISIBLE_DEVICES"
echo "  DEFAULT_MODEL_SIZE: $DEFAULT_MODEL_SIZE"
echo ""

# Verificar que los modelos existen
echo "Verificando modelos..."
if [ ! -d "$HF_HOME/models--Qwen--Qwen3-TTS-12Hz-1.7B-Base" ]; then
    echo "❌ Error: No se encontraron los modelos en $HF_HOME"
    echo "   Por favor, ejecuta primero: python3 download_models.py"
    exit 1
fi

echo "✅ Modelos encontrados"
echo ""

# Iniciar el servidor
echo "=========================================="
echo "Iniciando Qwen3-TTS Service..."
echo "=========================================="
echo ""
echo "API disponible en: http://localhost:8000"
echo "Documentación: http://localhost:8000/docs"
echo ""

# Ejecutar con python3
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
