# Commit Protocol (AI + Human Friendly)

Objetivo: que cada commit deje contexto suficiente para auditar regresiones sin abrir todo el diff.

## 1. Mensaje de commit sugerido

Formato:
`<tipo>(<scope>): <resumen>`

Tipos:
- `feat`
- `fix`
- `refactor`
- `docs`
- `chore`
- `test`

Ejemplo:
- `fix(flow): restore stable flight selection after GUI refactor`

## 2. Contenido mínimo por commit

Antes de commitear, registrar en `CHANGELOG.md` (sección `Unreleased`):
- qué cambió,
- por qué,
- riesgo,
- validación ejecutada,
- archivos clave.

## 3. Plantilla corta de descripción (PR o nota de commit)

```md
## Why
<problema que resuelve>

## What
<cambios principales>

## Risk
<dónde podría romper>

## Validation
- [ ] make check
- [ ] make smoke-busqueda
- [ ] make smoke-checkout

## Files
<lista corta>
```

## 4. Reglas para evitar deuda de contexto

- Si cambias flags: actualizar `cli.py`, `gui.py` (si aplica) y `README.md`.
- Si cambias flujo: actualizar `docs/REGRESSION_MATRIX.md` si cambia el smoke.
- Si cambias arquitectura: actualizar `docs/ARCHITECTURE.md`.
- Si cambias “dónde tocar”: actualizar `docs/CHANGE_PLAYBOOK.md`.
