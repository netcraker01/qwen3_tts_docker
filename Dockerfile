# Multi-stage build for Qwen3-TTS Service
FROM nvidia/cuda:12.1.1-devel-ubuntu22.04 AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    python3.10-dev \
    build-essential \
    libsndfile1 \
    libsndfile1-dev \
    ffmpeg \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python3.10 -m pip install --upgrade pip setuptools wheel

# Production stage
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODEL_CACHE_DIR=/app/models \
    CUDA_VISIBLE_DEVICES=0

# Install runtime dependencies (incluyendo sox binario)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    libsndfile1 \
    libsndfile1-dev \
    ffmpeg \
    sox \
    libsox-fmt-all \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install numpy and typing_extensions first (required by sox)
RUN python3.10 -m pip install --no-cache-dir numpy==1.26.4 typing_extensions

# Install Python dependencies (except flash-attn)
RUN python3.10 -m pip install --no-cache-dir \
    fastapi==0.115.0 \
    uvicorn[standard]==0.32.0 \
    pydantic==2.9.0 \
    python-multipart==0.0.17 \
    qwen-tts==0.1.0 \
    torch==2.5.1 \
    torchaudio==2.5.1 \
    soundfile==0.12.1 \
    accelerate==1.12.0 \
    aiofiles==24.1.0 \
    httpx==0.27.2 \
    pydub==0.25.1

# Install flash-attn with proper build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3.10-dev \
    git \
    && pip install --no-cache-dir flash-attn==2.7.4.post1 \
    && apt-get remove -y build-essential python3.10-dev git \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY app/ ./app/

# Create models directory
RUN mkdir -p /app/models

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD python3.10 -c "import requests; requests.get('http://localhost:8000/api/v1/health')" || exit 1

# Run the application
CMD ["python3.10", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]