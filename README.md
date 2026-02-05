# Qwen3-TTS Service API

[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> Servicio Docker de Texto a Voz (TTS) basado en **Qwen3-TTS** de Alibaba Cloud con API REST.

**Repositorio**: https://github.com/netcraker01/qwen3_tts_docker

Servicio Docker de Texto a Voz (TTS) basado en **Qwen3-TTS** con soporte para:
- 🎭 **Custom Voice**: Voces preestablecidas (Vivian, Ryan, Sohee, etc.)
- 🎨 **Voice Design**: Crear voces por descripción de texto
- 🎤 **Voice Clone**: Clonación Zero-Shot desde audio de referencia

## 🚀 Características

- **Modelo 1.7B**: Alta calidad de síntesis de voz
- **API REST**: FastAPI con documentación OpenAPI/Swagger automática
- **Soporte GPU**: Optimizado para CUDA con Flash Attention
- **Multi-idioma**: Español, Inglés, Chino, Japonés, Coreano, Alemán, Francés, Ruso, Portugués, Italiano
- **Lazy Loading**: Carga modelos bajo demanda para optimizar memoria

## 📋 Requisitos

- Docker y Docker Compose
- NVIDIA Docker Runtime (para soporte GPU)
- GPU con al menos 8GB VRAM (recomendado 12GB)
- ~10GB espacio en disco para modelos

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

3. **Git**
   - [Descargar Git](https://git-scm.com/downloads)

---

### Paso 1: Clonar el Repositorio

```bash
# Clonar desde GitHub
git clone https://github.com/netcraker01/qwen3_tts_docker.git

# Entrar al directorio
cd qwen3_tts_docker

# Verificar archivos
ls -la
```

---

### Paso 2: Preparar el Entorno

```bash
# Crear directorios necesarios (si no existen)
mkdir -p models output

# Verificar estructura
tree -L 2
# o
ls -R
```

**Estructura esperada:**
```
qwen3_tts_docker/
├── app/              # Código fuente
├── models/           # Cache de modelos (se creará automáticamente)
├── output/           # Archivos generados (se creará automáticamente)
├── docker-compose.yml
├── Dockerfile
└── README.md
```

---

### Paso 3: Configurar Variables de Entorno (Opcional)

Crea un archivo `.env` para personalizar la configuración:

```bash
# Crear archivo .env
cat > .env << EOF
# GPU Configuration
CUDA_VISIBLE_DEVICES=0

# Model Configuration
DEFAULT_MODEL_SIZE=1.7B
USE_FLASH_ATTENTION=true
MODEL_CACHE_DIR=/app/models

# Service Configuration
LOG_LEVEL=info
EOF
```

**Variables disponibles:**

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `CUDA_VISIBLE_DEVICES` | ID de la GPU a usar | `0` |
| `DEFAULT_MODEL_SIZE` | Tamaño del modelo (`1.7B` o `0.6B`) | `1.7B` |
| `USE_FLASH_ATTENTION` | Activar Flash Attention (más rápido) | `true` |
| `LOG_LEVEL` | Nivel de logs (`debug`, `info`, `warning`, `error`) | `info` |

---

### Paso 4: Construir la Imagen Docker

```bash
# Construir la imagen (primera vez ~5-10 minutos)
docker-compose build

# O construir sin caché (si hay problemas)
docker-compose build --no-cache
```

**Nota:** La construcción descarga:
- Imagen base CUDA 12.1 (~2GB)
- Dependencias Python
- Flash Attention (compilación desde código fuente)

---

### Paso 5: Iniciar el Servicio

```bash
# Iniciar en modo detached (background)
docker-compose up -d

# Verificar que está corriendo
docker-compose ps

# Ver logs en tiempo real
docker-compose logs -f qwen3-tts

# Ver logs recientes (últimas 100 líneas)
docker-compose logs --tail=100 qwen3-tts
```

**Primera ejecución:** Se descargarán automáticamente los modelos de HuggingFace (~4-6GB). Esto puede tardar 10-30 minutos dependiendo de tu conexión.

---

### Paso 6: Verificar la Instalación

```bash
# Test de health check
curl http://localhost:8000/api/v1/health

# Ver información de modelos
curl http://localhost:8000/api/v1/models

# Listar speakers disponibles
curl http://localhost:8000/api/v1/speakers
```

**Respuesta esperada del health check:**
```json
{
  "status": "healthy",
  "models_loaded": [],
  "cuda_available": true,
  "gpu_count": 1,
  "gpu_name": "NVIDIA GeForce RTX 3060"
}
```

---

### Paso 7: Acceder a la Documentación

- **API Docs (Swagger UI)**: http://localhost:8000/docs
- **API Docs (ReDoc)**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/v1/health

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

## 💡 Ejemplos de Uso

### Custom Voice

```bash
curl -X POST "http://localhost:8000/api/v1/tts/custom" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "¡Hola! Esta es una prueba de síntesis de voz.",
    "speaker": "Sohee",
    "language": "Spanish",
    "instruction": "Feliz y enérgica",
    "output_format": "wav"
  }'
```

### Voice Design

```bash
curl -X POST "http://localhost:8000/api/v1/tts/design" \
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
curl -X POST "http://localhost:8000/api/v1/tts/clone/url" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Esta es mi voz clonada hablando.",
    "ref_audio_url": "https://ejemplo.com/mi-voz.wav",
    "ref_text": "Hola, esta es mi voz de referencia.",
    "language": "Spanish"
  }'
```

### Voice Clone (Upload)

```bash
curl -X POST "http://localhost:8000/api/v1/tts/clone/upload" \
  -F "text=Esta es mi voz clonada" \
  -F "ref_text=Hola, esta es mi voz" \
  -F "language=Spanish" \
  -F "ref_audio=@/ruta/a/mi-voz.wav"
```

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

## 🌍 Idiomas Soportados

- Auto (detección automática)
- Spanish
- English
- Chinese
- Japanese
- Korean
- German
- French
- Russian
- Portuguese
- Italian

## ⚙️ Configuración

Variables de entorno en `docker-compose.yml`:

| Variable | Descripción | Default |
|----------|-------------|---------|
| `CUDA_VISIBLE_DEVICES` | GPU a usar | 0 |
| `MODEL_CACHE_DIR` | Directorio caché de modelos | /app/models |
| `DEFAULT_MODEL_SIZE` | Tamaño modelo (1.7B o 0.6B) | 1.7B |
| `USE_FLASH_ATTENTION` | Usar Flash Attention | true |
| `LOG_LEVEL` | Nivel de logs | info |

## 📁 Estructura del Proyecto

```
qwen3-tts-service/
├── app/
│   ├── api/
│   │   └── routes.py          # Endpoints REST
│   ├── schemas/
│   │   └── requests.py        # Modelos Pydantic
│   ├── services/
│   │   └── tts_service.py     # Lógica TTS
│   ├── __init__.py
│   └── main.py                # Entry point FastAPI
├── models/                    # Caché de modelos (volumen)
├── output/                    # Archivos generados (volumen)
├── Dockerfile                 # Imagen Docker
├── docker-compose.yml         # Orquestación
├── requirements.txt           # Dependencias
└── README.md                  # Este archivo
```

## 🔧 Desarrollo

### Sin Docker (desarrollo local)

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
python -m uvicorn app.main:app --reload --port 8000
```

### Testing

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Listar speakers
curl http://localhost:8000/api/v1/speakers
```

## 🛑 Detener y Actualizar el Servicio

### Detener el servicio
```bash
# Detener contenedores (conserva datos)
docker-compose down

# Detener y eliminar volúmenes (⚠️ borra modelos descargados)
docker-compose down -v

# Detener y eliminar imágenes también
docker-compose down --rmi all
```

### Actualizar el servicio
```bash
# Obtener últimos cambios del repositorio
git pull origin main

# Reconstruir imagen con cambios
docker-compose up -d --build

# O forzar reconstrucción completa
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Verificar estado
```bash
# Ver contenedores corriendo
docker ps

# Ver uso de recursos
docker stats qwen3-tts

# Ver logs con filtro
docker-compose logs -f qwen3-tts | grep ERROR
```

---

## 🐛 Solución de Problemas

### Error: `docker: Error response from daemon: could not select device driver`
**Solución:** NVIDIA Docker Runtime no está instalado.
```bash
# Linux: Instalar nvidia-container-toolkit
sudo apt-get install nvidia-container-toolkit
sudo systemctl restart docker
```

### Error: `RuntimeError: CUDA out of memory`
**Solución:** La GPU no tiene suficiente VRAM.
```bash
# Opción 1: Usar modelo más pequeño
echo "DEFAULT_MODEL_SIZE=0.6B" >> .env
docker-compose restart

# Opción 2: Limitar longitud de audio
# Editar docker-compose.yml y añadir:
# environment:
#   - MAX_AUDIO_LENGTH_SECONDS=30
```

### Error: `Connection refused` al llamar a la API
**Solución:** El servicio aún está iniciando o hay un error.
```bash
# Verificar estado
docker-compose ps

# Ver logs
docker-compose logs qwen3-tts

# Esperar a que descargue modelos (primera vez)
docker-compose logs -f qwen3-tts | grep "Application startup complete"
```

### Error: `ModuleNotFoundError: No module named 'qwen_tts'`
**Solución:** Reconstruir la imagen.
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Modelos descargan muy lento
**Solución:** Configurar mirror de HuggingFace (China).
```bash
# Crear .env con mirror
cat >> .env << EOF
HF_ENDPOINT=https://hf-mirror.com
EOF
docker-compose restart
```

---

## 📊 Comandos Útiles

```bash
# Ver espacio usado por Docker
docker system df

# Limpiar caché de Docker
docker system prune -a

# Ejecutar comando dentro del contenedor
docker-compose exec qwen3-tts bash

# Ver archivos generados
ls -lah output/

# Copiar archivo desde contenedor
docker cp qwen3-tts:/app/output/audio.wav ./audio.wav

# Escuchar audio generado (Linux con paplay)
paplay output/audio.wav
```

---

## 🔒 Seguridad

- El servicio expone el puerto 8000 solo en localhost por defecto
- Para acceso remoto, usar reverse proxy (nginx) con HTTPS
- No expongas el puerto 8000 directamente a internet sin autenticación
- Los archivos de audio en `output/` son accesibles por cualquiera con acceso al contenedor

---

## 📄 Licencia

Este proyecto utiliza Qwen3-TTS de Alibaba Cloud. Ver licencias originales:
- [Qwen3-TTS](https://huggingface.co/Qwen)

## 🤝 Contribuciones

Issues y PRs son bienvenidos!

---

**Nota**: La primera ejecución descargará los modelos (~4-6GB), lo cual puede tardar varios minutos dependiendo de la conexión.