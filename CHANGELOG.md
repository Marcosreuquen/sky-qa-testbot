# Changelog

Todos los cambios relevantes del proyecto se documentan aquí para facilitar debugging y análisis de regresiones por agentes.

Formato recomendado por entrada:
- `Qué cambió`
- `Por qué`
- `Riesgo de regresión`
- `Cómo validar`
- `Archivos clave`

## [Unreleased]

### Added
- Documentación AI-first:
  - `AGENTS.md`
  - `docs/START_HERE.md`
  - `docs/ARCHITECTURE.md`
  - `docs/CHANGE_PLAYBOOK.md`
  - `docs/AI_CONTEXT_PACK.md`
  - `docs/REGRESSION_MATRIX.md`
  - `docs/COMMIT_PROTOCOL.md`
  - `docs/PENDING_GLOSSARY.md`
  - `docs/README.md`
- Nuevos comandos de mantenimiento:
  - `make ai-bootstrap`
  - `make context-digest`
  - `make check`
  - `make smoke-busqueda`
  - `make smoke-checkout`
  - `scripts/agent_bootstrap.sh`
  - `scripts/context_digest.sh`
  - `scripts/validate_local.sh`
  - `scripts/smoke_pe_checkout.sh`
- Plantilla de PR para cambios consistentes: `.github/pull_request_template.md`.
- Estandarización de formato con `.editorconfig`.

### Changed
- README actualizado con sección AI-first y comandos de validación.
- `CASOS_DE_PRUEBA.md` corregido para reflejar reglas actuales (`--dias < 16` solo advierte, no fuerza ajuste).
- Comentario de `config/vuelo.py` actualizado para evitar confusión sobre antifraude.
- Smokes de `Makefile` y script `smoke_pe_checkout.sh` en modo no interactivo (`--headless --slow-mo 0`) para ejecución automática.

## [2026-03-03]

### Fixed
- Regresión en navegación que afectaba transición de búsqueda/selección:
  - se removieron reintentos agresivos de `Buscar vuelo` que podían cortar el flujo por falso negativo,
  - se conservó cierre defensivo del panel de login sin clicks por coordenadas.

Archivos: `test_sky.py`.

### Changed
- Evolución grande de GUI (presets editables, tooltips, layout colapsable, modo log limpio, defaults y persistencia), además de mejoras de CDP y tiempos de espera finales.

Referencia: commit `1963d18`.

## [Histórico resumido]

- `f7a3909`: soporte `ROUND_TRIP`, múltiples pasajeros e infantes.
- `8b217de`: manejo robusto de errores en checkout/pago.
- `fb16ff9`: checkpoints dinámicos.
- `bdd3e4f`: `argparse` + CLI + home market.
- `24729d4`: base inicial del bot.
