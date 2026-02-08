# Contributing to Qwen3-TTS Service

¡Gracias por tu interés en contribuir a Qwen3-TTS Service! Este documento proporciona guías para contribuir al proyecto.

## Cómo Contribuir

### Reportar Bugs

Si encuentras un bug, por favor crea un issue en GitHub con:
- Descripción clara del problema
- Pasos para reproducirlo
- Comportamiento esperado vs actual
- Logs de error (si aplica)
- Información del entorno (OS, GPU, versión de Docker)

### Sugerir Features

Para sugerir nuevas características:
- Explica el problema que resuelve
- Describe la solución propuesta
- Considera alternativas

### Pull Requests

1. **Fork** el repositorio
2. **Crea una rama** para tu feature (`git checkout -b feature/amazing-feature`)
3. **Commit** tus cambios (`git commit -m 'Add amazing feature'`)
4. **Push** a la rama (`git push origin feature/amazing-feature`)
5. **Abre un Pull Request**

## Estándares de Código

### Python
- Seguir PEP 8
- Usar type hints cuando sea posible
- Documentar funciones con docstrings
- Máximo 100 caracteres por línea

### Commits
- Usar mensajes descriptivos en español o inglés
- Formato: `tipo: descripción`
- Tipos: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Ejemplos:
```
feat: add voice clone persistence
fix: resolve CUDA memory leak
docs: update API documentation
```

## Estructura del Proyecto

```
qwen3_tts_docker/
├── app/
│   ├── api/           # Endpoints REST
│   ├── schemas/       # Modelos Pydantic
│   ├── services/      # Lógica de negocio
│   └── main.py        # Entry point
├── models/            # Cache de modelos
├── web/               # Interfaz web
├── tests/             # Tests (por implementar)
└── docs/              # Documentación adicional
```

## Testing

```bash
# Ejecutar tests
pytest

# Con coverage
pytest --cov=app
```

## Documentación

- Actualizar README.md si cambias la API
- Documentar nuevos endpoints en API.md
- Incluir ejemplos de uso

## Preguntas

Para preguntas generales, usar GitHub Discussions.

## Código de Conducta

- Sé respetuoso
- Acepta crítica constructiva
- Enfócate en lo mejor para la comunidad

## Licencia

Al contribuir, aceptas que tu código será licenciado bajo MIT License.