# Qwen3-TTS Service API

[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> Servicio Docker de Texto a Voz (TTS) basado en **Qwen3-TTS** de Alibaba Cloud con API REST y cola FIFO para procesamiento asíncrono.

Servicio Docker de Texto a Voz (TTS) basado en **Qwen3-TTS** con soporte para:
- 🎭 **Custom Voice**: Voces preestablecidas (Vivian, Ryan, Sohee, etc.)
- 🎨 **Voice Design**: Crear voces por descripción de texto
- 🎤 **Voice Clone**: Clonación Zero-Shot desde audio de referencia
- 📋 **Jobs Asíncronos con Cola FIFO**: Procesamiento ordenado sin timeouts

## 🚀 Características

- **Modelo 1.7B**: Alta calidad de síntesis de voz
- **API REST**: FastAPI con documentación OpenAPI/Swagger automática
- **Soporte GPU**: Optimizado para CUDA
- **Multi-idioma**: Español, Inglés, Chino, Japonés, Coreano, Alemán, Francés, Ruso, Portugués, Italiano
- **Self-contained**: Modelos pre-descargados en la imagen Docker

## 📋 Requisitos

- Docker y Docker Compose
- NVIDIA Docker Runtime (para soporte GPU)
- GPU con al menos 8GB VRAM (recomendado 12GB)
- ~15GB espacio en disco para la imagen Docker (incluye modelos)

## 🛠️ Instalación y Uso

### Prerrequisitos

Antes de comenzar, asegúrate de tener instalado:

1. **Docker Desktop** (Windows/Mac) o **Docker Engine** (Linux)
   - [Descargar Docker Desktop](https://www.docker.com/products/docker-desktop)

2. **NVIDIA Docker Runtime** (solo para GPU)
   ```bash
   # Linux - Ubuntu/Debian
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
   curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
   sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
   sudo systemctl restart docker
   
   # Verificar instalación
   docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
   ```

---

### Paso 1: Clonar y Construir

```bash
# Clonar el repositorio
git clone https://github.com/netcraker01/qwen3_tts_docker.git
cd qwen3_tts_docker

# Construir la imagen (descarga modelos durante el build)
# ⚠️ Esto puede tardar 10-20 minutos la primera vez
docker-compose build

# O si prefieres usar modelos 0.6B (más ligeros, 3GB menos):
# Edita docker-compose.yml y cambia DOWNLOAD_MODEL_SIZE a 0.6B
```

> **Nota importante**: Los modelos se descargan **durante el build** de Docker, no en runtime. Esto hace que el contenedor sea completamente autónomo.

---

### Paso 2: Iniciar el Servicio

```bash
# Iniciar en modo detached (background)
docker-compose up -d

# Verificar que está corriendo
docker-compose ps

# Ver logs en tiempo real
docker-compose logs -f qwen3-tts
```

---

### Paso 3: Verificar la Instalación

```bash
# Test de health check
curl http://localhost:8080/api/v1/health

# Ver información de modelos
curl http://localhost:8080/api/v1/models

# Listar speakers disponibles
curl http://localhost:8080/api/v1/speakers
```

**Respuesta esperada del health check:**
```json
{
  "status": "healthy",
  "models_loaded": [],
  "cuda_available": true,
  "default_model_size": "1.7B",
  "gpu_name": "NVIDIA GeForce RTX 3060"
}
```

---

### Paso 4: Acceder a la Documentación

- **API Docs (Swagger UI)**: http://localhost:8080/docs
- **API Docs (ReDoc)**: http://localhost:8080/redoc
- **Health Check**: http://localhost:8080/api/v1/health
- **Web UI**: http://localhost:8081 (si habilitaste tts-webui)

---

## 📡 Endpoints API

### Health & Info

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/health` | GET | Estado del servicio |
| `/api/v1/models` | GET | Información de modelos |
| `/api/v1/speakers` | GET | Listar speakers disponibles |
| `/api/v1/languages` | GET | Listar idiomas soportados |

### Text-to-Speech

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/tts/custom` | POST | Voz con personaje preestablecido |
| `/api/v1/tts/design` | POST | Voz por descripción de texto |
| `/api/v1/tts/clone/url` | POST | Clonar desde URL de audio |
| `/api/v1/tts/clone/upload` | POST | Clonar subiendo archivo |
| `/api/v1/tts/custom/file` | POST | Generar y descargar archivo |

### Jobs Asíncronos (Cola FIFO) ⭐ NUEVO

Para operaciones largas que pueden causar timeout, usa los endpoints de jobs asíncronos:

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/jobs` | POST | Crear job de generación de audio |
| `/api/v1/jobs/queue/status` | GET | Estado de la cola de procesamiento |
| `/api/v1/jobs/{id}/stream` | GET | SSE - Progreso en tiempo real |
| `/api/v1/jobs/{id}/status` | GET | Consultar estado del job |
| `/api/v1/jobs/{id}/result` | GET | Obtener resultado |
| `/api/v1/jobs/{id}/cancel` | POST | Cancelar job |

**Características:**
- ✅ **Cola FIFO**: Jobs procesados en orden de llegada
- ✅ **Sin timeouts**: Respuesta inmediata con job_id
- ✅ **Múltiples peticionarios**: Varios clientes pueden enviar jobs simultáneamente
- ✅ **Progreso en tiempo real**: Streaming SSE con actualizaciones de progreso
- ✅ **Monitoreo**: Endpoint para ver estado de la cola

**Tipos de job soportados:**
- `custom_voice` - Voz preestablecida
- `voice_design` - Diseño de voz por descripción
- `voice_clone_url` - Clonación desde URL
- `voice_clone_file` - Clonación desde archivo base64
- `cloned_voice_generate` - Generar usando voz clonada guardada

**Ejemplo de uso con jobs:**
```bash
# 1. Crear job
curl -X POST "http://localhost:8080/api/v1/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "job_type": "custom_voice",
    "request_data": {
      "text": "Texto largo a convertir...",
      "speaker": "Sohee",
      "output_format": "wav"
    }
  }'
# Respuesta: {"job_id": "xxx", "stream_url": "/api/v1/jobs/xxx/stream", ...}

# 2. Monitorear progreso (en navegador o con sseclient)
# GET /api/v1/jobs/{job_id}/stream

# 3. Obtener resultado
curl "http://localhost:8080/api/v1/jobs/{job_id}/result"
```

**Ver estado de la cola:**
```bash
curl "http://localhost:8080/api/v1/jobs/queue/status"
```
Respuesta:
```json
{
  "queue": {
    "pending": 3,
    "processing": 1,
    "max_concurrent": 1
  },
  "jobs": {
    "total": 15,
    "completed": 12,
    "failed": 0
  },
  "system_status": "busy"
}
```

Más detalles en [API.md](API.md#jobs-asíncronos-con-cola-fifo).

## 💡 Ejemplos de Uso


### Custom Voice

```bash
curl -X POST "http://localhost:8080/api/v1/tts/custom" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello world, this is a test of the Qwen3 TTS service.",
    "speaker": "Ryan",
    "language": "English",
    "instruction": "Clear and professional",
    "output_format": "ogg"
  }'
```

**📱 Para WhatsApp, usar formato `ogg` o `opus`:**
- ✅ Formato nativo de WhatsApp (Opus en contenedor OGG)
- ✅ Archivos pequeños (~20-30KB para mensajes de 2-3 segundos)
- ✅ Máxima compatibilidad con todos los clientes de WhatsApp

**Formatos soportados:** `wav`, `mp3`, `ogg`, `opus`

### Voice Design

```bash
curl -X POST "http://localhost:8080/api/v1/tts/design" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Bienvenidos a la presentación de hoy.",
    "voice_description": "gender: Female, pitch: Medium, speed: Moderate, emotion: Professional",
    "language": "Spanish",
    "output_format": "wav"
  }'
```

### Voice Clone (URL)

```bash
curl -X POST "http://localhost:8080/api/v1/tts/clone/url" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Esta es mi voz clonada hablando.",
    "ref_audio_url": "https://ejemplo.com/mi-voz.wav",
    "ref_text": "Hola, esta es mi voz de referencia.",
    "language": "Spanish"
  }'
```

---

## 🎭 Speakers Disponibles

| Speaker | Género | Idioma | Estilo |
|---------|--------|--------|--------|
| Vivian | Female | Chinese | Natural |
| Serena | Female | English | Professional |
| Uncle_Fu | Male | Chinese | Mature |
| Dylan | Male | English | Young |
| Eric | Male | English | Professional |
| Ryan | Male | English | Conversational |
| Aiden | Male | English | Versatile |
| Ono_Anna | Female | Japanese | Anime |
| Sohee | Female | Korean | Natural |

---

## ⚙️ Configuración

### Variables de Entorno

Edita `docker-compose.yml` para personalizar:

| Variable | Descripción | Default |
|----------|-------------|---------|
| `CUDA_VISIBLE_DEVICES` | GPU a usar | 0 |
| `DEFAULT_MODEL_SIZE` | Tamaño modelo (1.7B o 0.6B) | 1.7B |
| `USE_FLASH_ATTENTION` | Usar Flash Attention | false |
| `LOG_LEVEL` | Nivel de logs | info |

### Cambiar tamaño de modelo (1.7B vs 0.6B)

Para usar modelos más ligeros (0.6B):

```yaml
# En docker-compose.yml
services:
  qwen3-tts:
    build:
      args:
        - DOWNLOAD_MODEL_SIZE=0.6B  # Cambiar aquí
    environment:
      - DEFAULT_MODEL_SIZE=0.6B    # Y aquí
```

Luego reconstruye:
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## 🛑 Comandos Útiles

```bash
# Ver logs
docker-compose logs -f qwen3-tts

# Reiniciar servicio
docker-compose restart qwen3-tts

# Detener servicio (conserva datos)
docker-compose down

# Detener y eliminar todo (⚠️ incluye voces clonadas)
docker-compose down -v

# Reconstruir imagen completa
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Ver uso de recursos
docker stats qwen3-tts
```

---

## 🐛 Solución de Problemas

### Error: `docker: Error response from daemon: could not select device driver`
**Solución:** NVIDIA Docker Runtime no está instalado.
```bash
sudo apt-get install nvidia-container-toolkit
sudo systemctl restart docker
```

### Error: `RuntimeError: CUDA out of memory`
**Solución:** Usar modelo más pequeño (0.6B) como se describe arriba.

### Error: `Can't load feature extractor for ... speech_tokenizer`
**Solución:** El script `fix_models_on_startup.py` se ejecuta automáticamente al iniciar el contenedor para corregir esto.

### El build falla al descargar modelos
**Solución:** Si el build falla por problemas de red, el contenedor intentará descargar los modelos en runtime. Sin embargo, esto hará que la primera ejecución sea más lenta.

---

## 📁 Estructura del Proyecto

```
qwen3_tts_docker/
├── app/                      # Código fuente de la API
│   ├── api/routes.py        # Endpoints REST
│   ├── services/            # Lógica de negocio
│   │   ├── tts_service.py   # Servicio TTS principal
│   │   ├── model_manager.py # Gestión de modelos
│   │   └── voice_manager.py # Gestión de voces clonadas
│   ├── schemas/requests.py  # Modelos Pydantic
│   └── main.py              # Entry point FastAPI
├── web/                      # Interfaz web (opcional)
├── Dockerfile               # Imagen Docker (modelos pre-descargados)
├── docker-compose.yml       # Orquestación
├── entrypoint.sh            # Script de inicio
├── fix_models_on_startup.py # Verificación de modelos
├── download_models_docker.py # Script de descarga para build
└── requirements.txt         # Dependencias Python
```

---

## 🔒 Seguridad

- El servicio expone el puerto 8080 en localhost por defecto
- Para acceso remoto, usar reverse proxy (nginx) con HTTPS
- No expongas el puerto 8080 directamente a internet sin autenticación

---

## 📄 Licencia

Este proyecto utiliza Qwen3-TTS de Alibaba Cloud. Ver licencias originales:
- [Qwen3-TTS](https://huggingface.co/Qwen)

---

**Nota**: La imagen Docker incluye los modelos pre-descargados (~4-6GB), lo que permite un despliegue inmediato sin esperas de descarga.
