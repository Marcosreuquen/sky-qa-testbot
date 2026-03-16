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
- `docs/BOT_FRICTIONS.md`: registro separado de parches, inconsistencias y mejoras sugeridas de causa raíz detectadas en ejecuciones reales del bot.

### Changed
- Soporte inicial de parámetros para extras:
  - `--seleccion-asiento SKIP|AUTO`
  - `--maletas-cabina`
  - `--maletas-bodega`
- GUI y presets actualizados para persistir estrategia de asiento y maletas.
- Navegación post-tarifa endurecida para variantes visuales nuevas en `seats` y `additional-services` de QA/Stage.
- Checkpoints en modo visual ahora reanudan la ejecución detectando la etapa actual en lugar de cortar siempre el flujo.
- Checkout de pago endurecido para variantes donde las pasarelas quedan detrás del acordeón `Más medios de pago`.
- GUI con pausa cooperativa (`Pausar para edición` / `Continuar`) y recuperación de errores en runtime.
- Nuevos checkpoints: `ANCILLARIES` y `LLEGADA_DATOS_PASAJERO`.
- Búsqueda endurecida para no avanzar a extras mientras la etapa siga en `BUSQUEDA`.
- Selección de fechas en Stage endurecida para el datepicker de dos meses y validación real contra el valor del input.

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

### Added (2026-03-05)
- **Selección de ambiente multi-entorno** (`--ambiente qa|tsts|stage`):
  - `config/pago.py`: refactorizado con `AMBIENTES_DISPONIBLES`, `_URLS_BASE` y `get_urls_por_market(ambiente)`.
  - `cli.py`: nuevo flag `--ambiente`.
  - `gui.py`: combo "Ambiente" en sección Flujo; guardado en settings y presets.
  - Riesgo: bajo — la URL se resuelve solo en runtime, sin cambios en navegación.
  - Validar: `python3 -m py_compile cli.py gui.py` + smoke con `--ambiente tsts`.

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
