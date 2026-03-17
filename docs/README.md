# Documentación

Este directorio quedó separado por audiencia, pero mantiene algunos archivos canonicos en `docs/`
porque son usados por `AGENTS.md`, `make ai-bootstrap` y referencias internas del repo.

## Canónicos en `docs/` (se mantienen en raíz)

Estos archivos son parte del flujo base de agentes y no conviene moverlos sin actualizar bootstrap/scripts:

1. `START_HERE.md`
2. `AI_CONTEXT_PACK.md`
3. `PENDING_GLOSSARY.md`
4. `REGRESSION_MATRIX.md`
5. `ARCHITECTURE.md`
6. `CHANGE_PLAYBOOK.md`
7. `COMMIT_PROTOCOL.md`
8. `BOT_FRICTIONS.md`

## Lectura por audiencia

- `agent/README.md`
  - índice de lectura para agentes y automatizaciones.
- `human/README.md`
  - índice de lectura para decisiones humanas, UX, proceso y orquestación.

## Objetivo

- reducir tiempo de onboarding,
- separar claramente operación del bot vs lectura humana,
- minimizar ambigüedad sobre qué documentos son fuente de verdad,
- acelerar debugging de regresiones sin perder contexto de producto.
