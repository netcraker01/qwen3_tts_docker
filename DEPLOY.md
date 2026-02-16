# Guía de Despliegue - Jobs Asíncronos

## Deploy en Servidor

### Opción 1: Deploy Automático (si tienes acceso)

Si me das acceso SSH al servidor, puedo hacer el deploy automáticamente.

### Opción 2: Deploy Manual (comandos para ejecutar)

Conéctate a tu servidor vía SSH y ejecuta:

```bash
# 1. Ir al directorio del proyecto (o clonar si no existe)
cd /ruta/a/qwen3_tts_docker
# o
git clone https://github.com/netcraker01/qwen3_tts_docker.git
cd qwen3_tts_docker

# 2. Actualizar código con los últimos cambios
git pull origin main

# 3. Verificar que tenemos los archivos nuevos
ls -la app/services/job_manager.py
ls -la app/api/jobs_routes.py

# 4. Detener contenedor actual
docker-compose down

# 5. Reconstruir imagen (IMPORTANTE - incluye nuevos archivos)
docker-compose build --no-cache

# 6. Iniciar servicio
docker-compose up -d

# 7. Verificar que está corriendo
docker-compose ps
docker-compose logs -f qwen3-tts

# 8. Probar endpoints
curl http://localhost:8080/api/v1/health
curl http://localhost:8080/api/v1/jobs/queue/status
```

### Verificación del Deploy

```bash
# Ver logs del servicio
docker-compose logs -f qwen3-tts

# Probar creación de job
curl -X POST "http://localhost:8080/api/v1/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "job_type": "custom_voice",
    "request_data": {
      "text": "Hola, esto es una prueba",
      "speaker": "Sohee",
      "output_format": "wav"
    }
  }'

# Ver documentación Swagger
# Abrir en navegador: http://TU_SERVIDOR:8080/docs
```

### Troubleshooting

Si el build falla:
```bash
# Limpiar todo y reconstruir
docker-compose down -v
docker system prune -a  # CUIDADO: Elimina todas las imágenes
docker-compose build --no-cache
docker-compose up -d
```

Si el puerto 8080 está ocupado:
```bash
# Editar docker-compose.yml y cambiar el puerto
# ports:
#   - "8081:8000"  # Usar 8081 en lugar de 8080
```

## Endpoints Disponibles

Después del deploy, estos endpoints estarán activos:

```
POST   /api/v1/jobs                 → Crear job
GET    /api/v1/jobs/queue/status    → Estado de la cola
GET    /api/v1/jobs/{id}/stream     → SSE progreso en tiempo real
GET    /api/v1/jobs/{id}/status     → Consultar estado del job
GET    /api/v1/jobs/{id}/result     → Obtener resultado
POST   /api/v1/jobs/{id}/cancel     → Cancelar job
DELETE /api/v1/jobs/{id}            → Eliminar job
GET    /api/v1/jobs                 → Listar todos los jobs
```

## Características del Sistema

- ✅ Cola FIFO (First In, First Out)
- ✅ Procesamiento secuencial por defecto (1 job a la vez)
- ✅ Múltiples peticionarios pueden enviar jobs simultáneamente
- ✅ Streaming SSE para progreso en tiempo real
- ✅ Sin timeouts - respuesta inmediata con job_id
