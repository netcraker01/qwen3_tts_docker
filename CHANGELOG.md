# Changelog

Todos los cambios notables de este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Sistema de Jobs Asíncronos con Cola FIFO** - Nueva API para procesamiento de audio sin bloqueo
  - Cola FIFO (First In, First Out) para procesamiento ordenado de jobs
  - Múltiples peticionarios pueden enviar jobs simultáneamente
  - Procesamiento secuencial por defecto (1 job a la vez), configurable
  - Workers asíncronos que procesan jobs de la cola en orden
  - Endpoint `/jobs/queue/status` para monitorear estado de la cola
  - Streaming de progreso en tiempo real vía Server-Sent Events (SSE)
  - Soporte para custom_voice, voice_design, voice_clone_url, voice_clone_file, cloned_voice_generate
  - Heartbeats automáticos para mantener conexiones vivas durante procesos largos
  - Posibilidad de cancelar jobs en proceso
  - Limpieza automática de jobs antiguos
- Script `test_async_jobs.py` con ejemplos de uso de la API asíncrona
- Soporte para modelos 0.6B (menor uso de memoria)
- Nuevo endpoint `/tts/clone/upload` para subir archivos directamente
- Sistema de voces clonadas persistentes
- Soporte para data URLs base64 en cloned voices
- Script `run_local.sh` para ejecución sin Docker
- Archivo `.env` para configuración local

### New Endpoints
- `POST /api/v1/jobs` - Crear job de generación de audio asíncrono
- `GET /api/v1/jobs/{job_id}/stream` - Stream SSE de progreso en tiempo real
- `GET /api/v1/jobs/{job_id}/status` - Consultar estado del job
- `GET /api/v1/jobs/{job_id}/result` - Obtener resultado del job
- `GET /api/v1/jobs` - Listar todos los jobs
- `POST /api/v1/jobs/{job_id}/cancel` - Cancelar un job
- `DELETE /api/v1/jobs/{job_id}` - Eliminar un job

### Fixed
- Corregido error de carga de modelos `speech_tokenizer`
- Corregido mapeo de volúmenes en docker-compose.yml
- Actualizado entrypoint.sh para rutas correctas

### Changed
- Mejorado manejo de memoria CUDA
- Actualizada documentación API.md

## [1.0.0] - 2024-02-08

### Added
- Implementación inicial del servicio Qwen3-TTS
- API REST con FastAPI
- Soporte para Custom Voice (9 speakers)
- Soporte para Voice Design
- Soporte para Voice Clone (Zero-Shot)
- Documentación Swagger/OpenAPI automática
- Interfaz web básica
- Soporte Docker y Docker Compose
- Soporte GPU CUDA
- Múltiples formatos de salida (WAV, MP3, OGG, OPUS)
- Optimizaciones de memoria (lazy loading)
- Manejo de errores global
- Health check endpoint
- Logs detallados

### Endpoints
- `GET /api/v1/health` - Health check
- `GET /api/v1/models` - Información de modelos
- `GET /api/v1/speakers` - Listar speakers
- `GET /api/v1/languages` - Listar idiomas
- `POST /api/v1/tts/custom` - Custom Voice
- `POST /api/v1/tts/design` - Voice Design
- `POST /api/v1/tts/clone/url` - Voice Clone desde URL
- `POST /api/v1/tts/clone/upload` - Voice Clone desde archivo

### Tecnologías
- FastAPI 0.115.0
- Qwen-TTS 0.1.0
- PyTorch 2.5.1
- CUDA 12.1
- Python 3.10

---

## Notas de Versión

### v1.0.0
Primera versión estable del servicio Qwen3-TTS Docker. Incluye todas las funcionalidades básicas para síntesis de voz con los modelos 1.7B de Qwen3-TTS.

### Roadmap

#### Próximas versiones
- [ ] Tests automatizados
- [ ] Autenticación API (JWT/API Keys)
- [ ] Rate limiting
- [ ] Caché de audio generado
- [ ] Webhook callbacks
- [ ] Métricas y monitoring (Prometheus)
- [ ] Soporte batch (múltiple texto)
- [ ] Streaming de audio
- [ ] Más speakers
- [ ] Modelos multilingües mejorados

#### Consideraciones Futuras
- [ ] Soporte para AMD ROCm
- [ ] CPU-only mode optimizado
- [ ] Quantización INT8/INT4
- [ ] ONNX export
- [ ] TensorRT optimización