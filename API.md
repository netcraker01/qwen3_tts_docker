# API Documentation - Qwen3-TTS Service

Documentación detallada de la API REST para el servicio de Texto a Voz Qwen3-TTS.

## Base URL

```
http://localhost:8080/api/v1
```

## Autenticación

Actualmente la API no requiere autenticación. Para producción, se recomienda implementar:
- API Keys
- JWT Tokens
- OAuth 2.0

---

## Endpoints

### Health Check

#### GET `/health`
Verifica el estado del servicio.

**Respuesta:**
```json
{
  "status": "healthy",
  "cuda_available": true,
  "models_loaded": [],
  "default_model_size": "1.7B",
  "gpu_name": "NVIDIA GeForce RTX 3060"
}
```

---

### Información

#### GET `/models`
Obtiene información sobre los modelos disponibles.

**Respuesta:**
```json
{
  "available_models": {
    "1.7B": {
      "custom_voice": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
      "voice_design": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
      "voice_clone": "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
    }
  },
  "available_speakers": ["Vivian", "Serena", "Ryan", ...],
  "supported_languages": ["Spanish", "English", "Chinese", ...],
  "loaded_models": [],
  "cuda_available": true,
  "gpu_info": {
    "name": "NVIDIA GeForce RTX 3060",
    "total_memory_gb": 12.0,
    "allocated_memory_gb": 0.5,
    "reserved_memory_gb": 0.8
  }
}
```

#### GET `/speakers`
Lista los speakers disponibles para Custom Voice.

**Respuesta:**
```json
{
  "speakers": ["Vivian", "Serena", "Ryan", "Dylan", "Eric", ...],
  "details": {
    "Ryan": {
      "gender": "Male",
      "language": "English",
      "style": "Conversational"
    }
  }
}
```

#### GET `/languages`
Lista los idiomas soportados.

**Respuesta:**
```json
{
  "languages": ["Auto", "Spanish", "English", "Chinese", ...],
  "notes": "Use 'Auto' para detección automática del idioma"
}
```

---

### Text-to-Speech

#### POST `/tts/custom`
Genera voz usando un personaje preestablecido.

**Request Body:**
```json
{
  "text": "Hello world, this is a test.",
  "speaker": "Ryan",
  "language": "English",
  "instruction": "Clear and professional",
  "output_format": "ogg",
  "temperature": 0.9,
  "top_p": 0.0,
  "top_k": 50,
  "repetition_penalty": 1.05,
  "max_new_tokens": 4096
}
```

**Parámetros:**
| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| text | string | ✅ | Texto a convertir |
| speaker | string | ✅ | Nombre del speaker |
| language | string | ❌ | Idioma (default: "Auto") |
| instruction | string | ❌ | Instrucción para estilo/emoción |
| output_format | string | ❌ | Formato: wav, mp3, ogg, opus |
| temperature | float | ❌ | Creatividad (0.0-1.0) |
| top_p | float | ❌ | Nucleus sampling |
| top_k | int | ❌ | Top-k sampling |
| repetition_penalty | float | ❌ | Penalización repetición |
| max_new_tokens | int | ❌ | Máximo de tokens |

**Respuesta:**
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

---

#### POST `/tts/design`
Genera voz mediante descripción de texto.

**Request Body:**
```json
{
  "text": "Bienvenidos a la presentación de hoy.",
  "voice_description": "gender: Female, pitch: Medium, speed: Moderate, emotion: Professional",
  "language": "Spanish",
  "output_format": "wav",
  "temperature": 0.9,
  "top_p": 0.0
}
```

**Parámetros:**
| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| text | string | ✅ | Texto a convertir |
| voice_description | string | ✅ | Descripción de la voz deseada |
| language | string | ❌ | Idioma (default: "Spanish") |
| output_format | string | ❌ | Formato de salida |
| *generation_params | varies | ❌ | Parámetros de generación |

---

### Voice Cloning

#### POST `/tts/clone/url`
Clona voz desde una URL de audio.

**Request Body:**
```json
{
  "text": "Esta es mi voz clonada hablando.",
  "ref_audio_url": "https://ejemplo.com/mi-voz.wav",
  "ref_text": "Hola, esta es mi voz de referencia.",
  "language": "Spanish",
  "output_format": "ogg",
  "model_size": "1.7B"
}
```

**Parámetros:**
| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| text | string | ✅ | Texto a sintetizar |
| ref_audio_url | string | ✅ | URL del audio de referencia |
| ref_text | string | ✅ | Transcripción del audio |
| language | string | ❌ | Idioma |
| output_format | string | ❌ | Formato de salida |
| model_size | string | ❌ | "0.6B" o "1.7B" |

---

#### POST `/tts/clone/upload`
Clona voz subiendo un archivo de audio.

**Content-Type:** `multipart/form-data`

**Parámetros:**
| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| text | string | ✅ | Texto a sintetizar |
| ref_text | string | ✅ | Transcripción del audio |
| language | string | ❌ | Idioma (default: "Spanish") |
| output_format | string | ❌ | Formato de salida |
| model_size | string | ❌ | "0.6B" o "1.7B" |
| ref_audio | file | ✅ | Archivo de audio (WAV, MP3, OGG) |

**Ejemplo cURL:**
```bash
curl -X POST "http://localhost:8080/api/v1/tts/clone/upload" \
  -F "text=Esta es mi voz clonada" \
  -F "ref_text=Hola, esta es mi voz de referencia" \
  -F "language=Spanish" \
  -F "ref_audio=@/ruta/a/mi-voz.wav"
```

---

### Gestión de Voces Clonadas

#### POST `/cloned-voices`
Crea una voz clonada persistente.

**Request Body:**
```json
{
  "name": "Mi Voz Personal",
  "description": "Voz clonada de mi audio",
  "ref_audio_url": "https://ejemplo.com/mi-voz.wav",
  "ref_text": "Hola, esta es mi voz",
  "language": "Spanish",
  "temperature": 0.9,
  "top_p": 0.0
}
```

**Respuesta:**
```json
{
  "success": true,
  "voice": {
    "id": "mi_voz_personal_1704567890",
    "name": "Mi Voz Personal",
    "description": "Voz clonada de mi audio",
    "ref_text": "Hola, esta es mi voz",
    "language": "Spanish",
    "created_at": "2024-01-06 15:30:45",
    "last_used": "2024-01-06 15:30:45",
    "use_count": 0
  },
  "message": "Voz 'Mi Voz Personal' creada exitosamente. Use el ID 'mi_voz_personal_1704567890' para generar audio."
}
```

---

#### GET `/cloned-voices`
Lista todas las voces clonadas.

**Respuesta:**
```json
{
  "voices": [
    {
      "id": "mi_voz_personal_1704567890",
      "name": "Mi Voz Personal",
      "description": "Voz clonada",
      "language": "Spanish",
      "created_at": "2024-01-06 15:30:45",
      "last_used": "2024-01-06 15:30:45",
      "use_count": 5
    }
  ],
  "total": 1
}
```

---

#### GET `/cloned-voices/{voice_id}`
Obtiene información de una voz específica.

**Respuesta:**
```json
{
  "voice": {
    "id": "mi_voz_personal_1704567890",
    "name": "Mi Voz Personal",
    "description": "Voz clonada",
    "language": "Spanish",
    "created_at": "2024-01-06 15:30:45",
    "last_used": "2024-01-06 15:30:45",
    "use_count": 5
  }
}
```

---

#### PUT `/cloned-voices/{voice_id}`
Actualiza una voz clonada.

**Request Body:**
```json
{
  "name": "Nuevo Nombre",
  "description": "Nueva descripción",
  "generation_params": {
    "temperature": 0.8
  }
}
```

---

#### DELETE `/cloned-voices/{voice_id}`
Elimina una voz clonada.

**Respuesta:**
```json
{
  "success": true,
  "message": "Voz 'mi_voz_personal_1704567890' eliminada exitosamente"
}
```

---

#### POST `/tts/cloned-voice/generate`
Genera audio usando una voz clonada guardada.

**Request Body:**
```json
{
  "text": "Mensaje usando mi voz clonada",
  "voice_id": "mi_voz_personal_1704567890",
  "language": "Spanish",
  "output_format": "ogg",
  "use_voice_defaults": true,
  "model_size": "1.7B"
}
```

**Parámetros:**
| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| text | string | ✅ | Texto a sintetizar |
| voice_id | string | ✅ | ID de la voz clonada |
| language | string | ❌ | Idioma |
| output_format | string | ❌ | Formato de salida |
| use_voice_defaults | boolean | ❌ | Usar params guardados |
| model_size | string | ❌ | "0.6B" o "1.7B" |

---

#### GET `/cloned-voices/stats`
Obtiene estadísticas de uso.

**Respuesta:**
```json
{
  "total_voices": 5,
  "total_generations": 150,
  "most_used": {
    "voice_id": "mi_voz_personal_1704567890",
    "name": "Mi Voz Personal",
    "use_count": 75
  },
  "voices_by_language": {
    "Spanish": 3,
    "English": 2
  }
}
```

---

## Códigos de Error

| Código | Descripción |
|--------|-------------|
| 200 | Éxito |
| 400 | Bad Request - Parámetros inválidos |
| 404 | Not Found - Recurso no encontrado |
| 422 | Validation Error - Error de validación |
| 500 | Internal Server Error - Error del servidor |

---

## Formatos de Audio

| Formato | Extensión | Tamaño típico | Uso recomendado |
|---------|-----------|---------------|-----------------|
| OGG | .ogg | ~20-30KB | **WhatsApp** - Formato nativo |
| OPUS | .opus | ~20-30KB | **WhatsApp** - Codec Opus |
| MP3 | .mp3 | ~40-60KB | Compatibilidad universal |
| WAV | .wav | ~200-400KB | Máxima calidad |

---

## Jobs Asíncronos con Cola FIFO

Para operaciones largas que pueden causar timeout (textos largos, voice clone con archivos grandes), la API proporciona endpoints de jobs asíncronos con **cola FIFO** (First In, First Out).

### Características:
- **Cola FIFO**: Los jobs se procesan en orden de llegada
- **Múltiples peticionarios**: Varios clientes pueden enviar jobs simultáneamente
- **Procesamiento controlado**: Por defecto 1 job a la vez (configurable)
- **No hay timeouts**: El cliente recibe inmediatamente un job_id y puede monitorear el progreso
- **Streaming en tiempo real**: Progreso vía Server-Sent Events (SSE)

### Flujo de trabajo:
1. Cliente crea un job → Recibe job_id inmediatamente
2. Job se encola en la cola FIFO
3. Worker procesa jobs uno a uno (o según configuración de concurrencia)
4. Cliente monitorea progreso vía SSE
5. Cliente obtiene resultado cuando el job termina

### Crear un Job

#### POST `/jobs`
Crea un nuevo job de generación de audio asíncrono.

**Request Body:**
```json
{
  "job_type": "custom_voice",
  "request_data": {
    "text": "Texto largo a convertir...",
    "speaker": "Sohee",
    "language": "Spanish",
    "output_format": "wav"
  }
}
```

**Tipos de job soportados:**
| Tipo | Descripción |
|------|-------------|
| `custom_voice` | Voz preestablecida |
| `voice_design` | Diseño de voz por descripción |
| `voice_clone_url` | Clonación desde URL |
| `voice_clone_file` | Clonación desde archivo base64 |
| `cloned_voice_generate` | Generar usando voz clonada guardada |

**Respuesta:**
```json
{
  "success": true,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "job": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "custom_voice",
    "status": "pending",
    "created_at": 1704567890.123,
    "updated_at": 1704567890.123,
    "progress": {
      "stage": "created",
      "percent": 0,
      "message": "Job creado",
      "timestamp": 1704567890.123
    },
    "elapsed_seconds": 0.0
  },
  "stream_url": "/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000/stream",
  "status_url": "/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000/status"
}
```

---

### Stream de Progreso (SSE)

#### GET `/jobs/{job_id}/stream`
Conecta a un stream Server-Sent Events para recibir actualizaciones de progreso en tiempo real.

**Content-Type:** `text/event-stream`

**Eventos:**
| Evento | Descripción |
|--------|-------------|
| `progress` | Actualización de progreso (stage, percent, message) |
| `heartbeat` | Ping cada segundo para mantener conexión |
| `completed` | Job completado exitosamente |
| `error` | Error durante el procesamiento |
| `cancelled` | Job cancelado |

**Ejemplo de eventos:**
```
event: progress
data: {"stage": "loading_model", "percent": 15, "message": "Cargando modelo...", "timestamp": 1704567891.234}

event: progress
data: {"stage": "generating", "percent": 50, "message": "Generando audio...", "timestamp": 1704567895.678}

event: completed
data: {"status": "completed", "result": {"success": true, "audio_base64": "...", ...}}
```

**Ejemplo JavaScript:**
```javascript
const eventSource = new EventSource('/api/v1/jobs/{job_id}/stream');

eventSource.addEventListener('progress', (e) => {
  const data = JSON.parse(e.data);
  console.log(`${data.percent}% - ${data.message}`);
});

eventSource.addEventListener('completed', (e) => {
  const data = JSON.parse(e.data);
  console.log('Audio generado:', data.result);
  eventSource.close();
});

eventSource.addEventListener('error', (e) => {
  console.error('Error:', e.data);
  eventSource.close();
});
```

---

### Consultar Estado del Job

#### GET `/jobs/{job_id}/status`
Obtiene el estado actual de un job.

**Respuesta:**
```json
{
  "job": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "custom_voice",
    "status": "processing",
    "progress": {
      "stage": "generating",
      "percent": 65,
      "message": "Generando audio...",
      "timestamp": 1704567895.678
    },
    "elapsed_seconds": 15.5
  }
}
```

---

### Listar Jobs

#### GET `/jobs`
Lista todos los jobs, opcionalmente filtrados por estado.

**Query Parameters:**
| Parámetro | Descripción |
|-----------|-------------|
| `status` | Filtrar por: pending, processing, completed, failed, cancelled |

**Respuesta:**
```json
{
  "jobs": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "type": "custom_voice",
      "status": "completed",
      "elapsed_seconds": 25.3
    }
  ],
  "total": 1
}
```

---

### Obtener Resultado

#### GET `/jobs/{job_id}/result`
Obtiene el resultado de un job completado.

**Respuesta:**
```json
{
  "success": true,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "result": {
    "success": true,
    "audio_base64": "UklGRiT+AQBXQVZFZm10IBAAAAABAAEAwF0AAIC7AAACABAAZGF0YQD+AQAAAAEAAAAAAAAAAAABAAAAAAAAAAAAAAAAAAAA...",
    "sample_rate": 24000,
    "duration_seconds": 5.23,
    "model_used": "1.7B_custom_voice",
    "processing_time_seconds": 18.45
  }
}
```

---

### Cancelar Job

#### POST `/jobs/{job_id}/cancel`
Cancela un job que está pendiente o en proceso.

**Respuesta:**
```json
{
  "success": true,
  "message": "Job 550e8400-e29b-41d4-a716-446655440000 cancelado exitosamente"
}
```

---

### Eliminar Job

#### DELETE `/jobs/{job_id}`
Elimina permanentemente un job.

---

## Ejemplos de Uso

### Python
```python
import requests
import base64

# Custom Voice
response = requests.post(
    "http://localhost:8080/api/v1/tts/custom",
    json={
        "text": "Hello world",
        "speaker": "Ryan",
        "language": "English",
        "output_format": "ogg"
    }
)

data = response.json()
audio_bytes = base64.b64decode(data["audio_base64"])

with open("output.ogg", "wb") as f:
    f.write(audio_bytes)
```

### JavaScript
```javascript
const response = await fetch('http://localhost:8080/api/v1/tts/custom', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    text: 'Hello world',
    speaker: 'Ryan',
    language: 'English',
    output_format: 'ogg'
  })
});

const data = await response.json();
const audioBytes = Buffer.from(data.audio_base64, 'base64');
fs.writeFileSync('output.ogg', audioBytes);
```

### cURL
```bash
curl -X POST "http://localhost:8080/api/v1/tts/custom" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello world",
    "speaker": "Ryan",
    "language": "English",
    "output_format": "ogg"
  }'
```

---

## Limitaciones

- **Longitud máxima de texto**: ~4096 tokens
- **Tamaño máximo de archivo**: 10MB
- **Duración audio referencia**: 3-10 segundos recomendado
- **Memoria GPU requerida**: Mínimo 8GB (12GB recomendado)

---

## Changelog

Ver [CHANGELOG.md](CHANGELOG.md) para historial de cambios.