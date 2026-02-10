#!/bin/bash
# Entrypoint script - Inicia el servicio Qwen3-TTS

set -e

echo "=========================================="
echo "Qwen3-TTS Service"
echo "=========================================="

# Configurar directorio de caché (debe coincidir con HF_HOME en Dockerfile)
export HF_HOME="${HF_HOME:-/app/models}"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"

# Crear directorios necesarios
mkdir -p "$HF_HOME"
mkdir -p /app/data
mkdir -p /app/output

echo "📁 Cache directory: $HF_HOME"
echo "🎮 CUDA Device: $CUDA_VISIBLE_DEVICES"

# Verificar CUDA
echo ""
echo "Verificando CUDA..."
python3 -c "import torch; print(f'  CUDA disponible: {torch.cuda.is_available()}'); print(f'  Dispositivos: {torch.cuda.device_count()}')" 2>/dev/null || echo "  ⚠️ No se pudo verificar CUDA"

# Verificar modelos (corrección automática si es necesario)
echo ""
echo "=========================================="
echo "Verificando modelos..."
echo "=========================================="
python3 /app/fix_models_on_startup.py || echo "⚠️  Advertencia: Verificación de modelos tuvo problemas, continuando..."

echo ""
echo "=========================================="
echo "Iniciando servicio..."
echo "=========================================="
echo ""
echo "✅ Los modelos están pre-instalados en la imagen"
echo "✅ No se requiere descarga en tiempo de ejecución"
echo ""

# Iniciar el servidor
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
