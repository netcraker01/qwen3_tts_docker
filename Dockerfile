# Qwen3-TTS Service - Optimized build with pre-downloaded models
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/app/models \
    CUDA_VISIBLE_DEVICES=0 \
    DOWNLOAD_MODEL_SIZE=1.7B

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    libsndfile1 \
    libsndfile1-dev \
    ffmpeg \
    sox \
    libsox-fmt-all \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && ln -sf /usr/bin/python3.10 /usr/bin/python3

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies in layers
RUN python3 -m pip install --no-cache-dir --upgrade pip

# Install PyTorch with CUDA support
RUN python3 -m pip install --no-cache-dir \
    torch==2.5.1 \
    torchaudio==2.5.1 \
    --index-url https://download.pytorch.org/whl/cu121

# Install remaining dependencies
RUN python3 -m pip install --no-cache-dir \
    numpy==1.26.4 \
    typing_extensions \
    requests \
    fastapi==0.115.0 \
    uvicorn==0.32.0 \
    pydantic==2.9.0 \
    python-multipart==0.0.17 \
    transformers \
    accelerate==1.12.0 \
    soundfile==0.12.1 \
    librosa \
    sox \
    aiofiles==24.1.0 \
    httpx==0.27.2 \
    pydub==0.25.1 \
    huggingface-hub \
    qwen-tts==0.1.0

# Pre-download models during build
# This makes the container self-contained
COPY download_models_docker.py .
RUN echo "==========================================" && \
    echo "Pre-downloading models during build..." && \
    echo "This may take 10-20 minutes depending on connection" && \
    echo "==========================================" && \
    python3 download_models_docker.py || echo "⚠️  Model download had issues, will retry on startup"

# Copy application code
COPY app/ ./app/

# Copy web interface
COPY web/ ./web/

# Copy entrypoint and fix scripts
COPY entrypoint.sh /app/entrypoint.sh
COPY fix_models_on_startup.py /app/fix_models_on_startup.py
RUN chmod +x /app/entrypoint.sh

# Create directories for data and output
RUN mkdir -p /app/data /app/output

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

# Run the application
ENTRYPOINT ["/app/entrypoint.sh"]
