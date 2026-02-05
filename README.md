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

### 1. Clonar y preparar

```bash
# Crear directorios necesarios
mkdir -p models output
```

### 2. Iniciar el servicio

```bash
# Con GPU (recomendado)
docker-compose up -d

# Ver logs
docker-compose logs -f qwen3-tts
```

### 3. Acceder a la API

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

## 🐛 Solución de Problemas

### Error de memoria GPU
- Verificar VRAM disponible: `nvidia-smi`
- Reducir `MAX_AUDIO_LENGTH_SECONDS` en docker-compose.yml
- Usar modelo 0.6B: `DEFAULT_MODEL_SIZE=0.6B`

### Modelos no descargan
- Verificar conexión a internet
- Verificar espacio en disco: `df -h`
- Limpiar caché: `docker-compose down -v`

### Error CUDA
- Verificar NVIDIA Docker Runtime instalado
- Verificar drivers NVIDIA: `nvidia-smi`

## 📄 Licencia

Este proyecto utiliza Qwen3-TTS de Alibaba Cloud. Ver licencias originales:
- [Qwen3-TTS](https://huggingface.co/Qwen)

## 🤝 Contribuciones

Issues y PRs son bienvenidos!

---

**Nota**: La primera ejecución descargará los modelos (~4-6GB), lo cual puede tardar varios minutos dependiendo de la conexión.