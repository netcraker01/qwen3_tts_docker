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
- **Soporte GPU**: Optimizado para CUDA
- **Multi-idioma**: Español, Inglés, Chino, Japonés, Coreano, Alemán, Francés, Ruso, Portugués, Italiano
- **Lazy Loading**: Carga modelos bajo demanda para optimizar memoria

## 📋 Requisitos

- Docker y Docker Compose
- NVIDIA Docker Runtime (para soporte GPU)
- GPU con al menos 8GB VRAM (recomendado 12GB)
- ~15GB espacio en disco para modelos y contenedor

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
mkdir -p models output data

# Verificar estructura
tree -L 2
# o
ls -R
```

**Estructura esperada:**
```
qwen3_tts_docker/
├── app/              # Código fuente
├── models/           # Cache de modelos (volumen)
├── output/           # Archivos generados (volumen)
├── data/             # Voces clonadas persistentes (volumen)
├── docker-compose.yml
├── Dockerfile
└── README.md
```

---

### Paso 3: Iniciar el Servicio

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

**Primera ejecución:** El servicio intentará descargar los modelos automáticamente. Esto puede tardar varios minutos dependiendo de tu conexión.

---

### Paso 4: Verificar la Instalación

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

### Paso 5: Acceder a la Documentación

- **API Docs (Swagger UI)**: http://localhost:8080/docs
- **API Docs (ReDoc)**: http://localhost:8080/redoc
- **Health Check**: http://localhost:8080/api/v1/health

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
- ✅ Calidad óptima para voz a 24kHz mono

**Formatos soportados:** `wav`, `mp3`, `ogg`, `opus`

**Respuesta exitosa:**
```json
{
  "success": true,
  "audio_base64": "UklGRiT+AQBXQVZFZm10IBAAAAABAAEAwF0AAIC7AAACABAAZGF0YQD+AQAAAAEAAAAAAAAAAAABAAAAAAAAAAAAAAAAAAAA/////wAA/////wAAAAD/////AQABAP///v/+/wAAAQABAAEAAAAAAAAA///+////AAAAAP////8AAAEAA...",
  "sample_rate": 24000,
  "duration_seconds": 2.72,
  "model_used": "1.7B_custom_voice",
  "processing_time_seconds": 17.69,
  "error": null
}
```

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

### Voice Clone (Upload)

```bash
curl -X POST "http://localhost:8080/api/v1/tts/clone/upload" \
  -F "text=Esta es mi voz clonada" \
  -F "ref_text=Hola, esta es mi voz" \
  -F "language=Spanish" \
  -F "ref_audio=@/ruta/a/mi-voz.wav"
```

## 🎵 Formatos de Audio

La API soporta múltiples formatos de salida configurables mediante el parámetro `output_format`.

### Formatos Disponibles

| Formato | Extensión | Tamaño | Uso Recomendado |
|---------|-----------|--------|-----------------|
| **OGG** | `.ogg` | ~20-30KB | **WhatsApp** - Formato nativo (Opus) |
| **OPUS** | `.opus` | ~20-30KB | **WhatsApp** - Codec Opus explícito |
| **MP3** | `.mp3` | ~40-60KB | Compatibilidad universal |
| **WAV** | `.wav` | ~200-400KB | Máxima calidad, sin compresión |

### 📱 Guía para WhatsApp

Para enviar mensajes de voz por WhatsApp, se recomienda usar **OGG** o **OPUS**:

**Características:**
- ✅ Formato nativo de WhatsApp (contenedor OGG con codec Opus)
- ✅ Archivos pequeños (~20-30KB para mensajes de 2-3 segundos)
- ✅ Máxima compatibilidad con todos los clientes de WhatsApp
- ✅ Calidad óptima para voz a 24kHz mono

**Ejemplo para WhatsApp:**
```bash
curl -X POST "http://localhost:8080/api/v1/tts/custom" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hola, este es un mensaje de WhatsApp",
    "speaker": "Ryan",
    "language": "Spanish",
    "output_format": "ogg"
  }'
```

**Decodificar Base64 a archivo:**
```bash
# Linux/Mac
curl -X POST "http://localhost:8080/api/v1/tts/custom" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hola WhatsApp","speaker":"Ryan","language":"Spanish","output_format":"ogg"}' | \
  jq -r '.audio_base64' | base64 -d > mensaje.ogg

# Windows (PowerShell)
$response = Invoke-RestMethod -Uri "http://localhost:8080/api/v1/tts/custom" -Method Post -ContentType "application/json" -Body '{"text":"Hola WhatsApp","speaker":"Ryan","language":"Spanish","output_format":"ogg"}'
[System.Convert]::FromBase64String($response.audio_base64) | Set-Content -Path "mensaje.ogg" -Encoding Byte
```

## 🗣️ Gestión de Voces Clonadas Persistentes

El sistema permite crear, almacenar y reusar voces clonadas para generación rápida de audio.

### Endpoints de Gestión

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/cloned-voices` | POST | Crear nueva voz clonada persistente |
| `/api/v1/cloned-voices` | GET | Listar todas las voces clonadas |
| `/api/v1/cloned-voices/{id}` | GET | Obtener información de una voz |
| `/api/v1/cloned-voices/{id}` | PUT | Actualizar nombre/descripción |
| `/api/v1/cloned-voices/{id}` | DELETE | Eliminar voz clonada |
| `/api/v1/cloned-voices/stats` | GET | Estadísticas de uso |
| `/api/v1/tts/cloned-voice/generate` | POST | Generar audio usando voz guardada |

### Ejemplo: Crear y Usar Voz Clonada

**1. Crear voz clonada:**
```bash
curl -X POST "http://localhost:8080/api/v1/cloned-voices" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mi Voz Personal",
    "description": "Voz clonada de mi audio de referencia",
    "ref_audio_url": "https://ejemplo.com/mi-voz.wav",
    "ref_text": "Hola, esta es mi voz de referencia para clonación",
    "language": "Spanish"
  }'
```

**Respuesta:**
```json
{
  "success": true,
  "voice": {
    "id": "mi_voz_personal_1704567890",
    "name": "Mi Voz Personal",
    "description": "Voz clonada de mi audio de referencia",
    "ref_text": "Hola, esta es mi voz de referencia...",
    "language": "Spanish",
    "created_at": "2024-01-06 15:30:45",
    "last_used": "2024-01-06 15:30:45",
    "use_count": 0
  },
  "message": "Voz 'Mi Voz Personal' creada exitosamente. Use el ID 'mi_voz_personal_1704567890' para generar audio."
}
```

**2. Generar audio usando la voz guardada:**
```bash
curl -X POST "http://localhost:8080/api/v1/tts/cloned-voice/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Este es un mensaje usando mi voz clonada guardada",
    "voice_id": "mi_voz_personal_1704567890",
    "output_format": "ogg"
  }'
```

**Ventajas de usar voces persistentes:**
- ⚡ **Mucho más rápido**: No requiere reprocesar el audio de referencia
- 💾 **Persistente**: Las voces sobreviven reinicios del servidor
- 📊 **Estadísticas**: Seguimiento de uso de cada voz
- 🔧 **Editable**: Puedes renombrar y modificar descripciones

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
| `HF_HOME` | Directorio caché de modelos HuggingFace | /app/models |
| `DEFAULT_MODEL_SIZE` | Tamaño modelo (1.7B o 0.6B) | 1.7B |
| `USE_FLASH_ATTENTION` | Usar Flash Attention | true |
| `LOG_LEVEL` | Nivel de logs | info |

## 📁 Estructura del Proyecto

```
qwen3-tts-service/
├── app/
│   ├── api/
│   │   ├── routes.py          # Endpoints REST
│   │   └── __init__.py
│   ├── schemas/
│   │   ├── requests.py        # Modelos Pydantic
│   │   └── __init__.py
│   ├── services/
│   │   ├── tts_service.py     # Lógica TTS
│   │   └── __init__.py
│   ├── dependencies.py        # Inyección de dependencias
│   └── main.py                # Entry point FastAPI
├── models/                    # Caché de modelos (volumen)
├── output/                    # Archivos generados (volumen)
├── data/                      # Voces clonadas persistentes (volumen)
├── Dockerfile                 # Imagen Docker
├── docker-compose.yml         # Orquestación
├── download_models.py         # Script descarga manual
├── requirements.txt           # Dependencias
├── test_api.py                # Script de pruebas
├── .dockerignore
├── .gitignore
├── LICENSE
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
curl http://localhost:8080/api/v1/health

# Listar speakers
curl http://localhost:8080/api/v1/speakers

# Generar audio
curl -X POST "http://localhost:8080/api/v1/tts/custom" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello world","speaker":"Ryan","language":"English"}'
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
# Usar modelo más pequeño
echo "DEFAULT_MODEL_SIZE=0.6B" >> .env
docker-compose restart
```

### Error: `No se pudo cargar el modelo` o descarga atascada
**Solución:** Descargar modelos manualmente.
```bash
# Ejecutar script de descarga manual dentro del contenedor
docker-compose exec qwen3-tts python3.10 /app/download_models.py

# O copiar el script y ejecutar
docker cp download_models.py qwen3-tts:/tmp/
docker-compose exec qwen3-tts python3.10 /tmp/download_models.py
```

### Error: `Connection refused` al llamar a la API
**Solución:** El servicio aún está iniciando o hay un error.
```bash
# Verificar estado
docker-compose ps

# Ver logs
docker-compose logs qwen3-tts

# Esperar a que esté listo
docker-compose logs -f qwen3-tts | grep "Application startup complete"
```

### Error: `Disk quota exceeded` durante build
**Solución:** Limpiar espacio de Docker.
```bash
docker system prune -af
docker volume prune -f
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

## 🤝 Contribuciones

Issues y PRs son bienvenidos!

---

**Nota**: La primera ejecución descargará los modelos (~4-6GB), lo cual puede tardar varios minutos dependiendo de la conexión.