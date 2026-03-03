# START HERE (Agent Bootstrap)

Punto de entrada oficial para cualquier agente.

## Orden obligatorio de contexto (low-token)

1. `docs/AI_CONTEXT_PACK.md`
2. `CHANGELOG.md` (sección `Unreleased`)
3. `docs/PENDING_GLOSSARY.md`
4. `docs/REGRESSION_MATRIX.md`

Luego, según tarea:
- Si cambia arquitectura: `docs/ARCHITECTURE.md`
- Si cambia ubicación de responsabilidades: `docs/CHANGE_PLAYBOOK.md`
- Si se va a commitear: `docs/COMMIT_PROTOCOL.md`

## Comando único de arranque

```bash
make ai-bootstrap
```

Esto imprime:
- rama actual,
- cambios locales,
- commits recientes,
- checklist de lectura,
- comandos de validación.

## Regla de oro

Si un agente no siguió este orden, puede trabajar sobre contexto incompleto y provocar regresiones.
