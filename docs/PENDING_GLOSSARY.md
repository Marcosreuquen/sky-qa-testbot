# Pending + Glossary

Backlog de limpieza técnica y glosario corto para reducir ambigüedad entre agentes.

## 1) Pending (priorizado)

## P0 (alta prioridad)

- Unificar logs de `test_sky.py` en eventos estables (evitar mensajes duplicados por etapa).
  - Impacto: menor ruido y menos tokens en debugging.
- Extraer helpers de CDP/session a módulo separado (`core/browser_session.py`).
  - Impacto: menor acoplamiento entre navegación y conexión.
- Cubrir regresiones críticas con smoke automatizable por script único.
  - Impacto: detectar quiebres de flujo antes de merge.

## P1 (media prioridad)

- Dividir `test_sky.py` por dominios:
  - `core/search_flow.py`
  - `core/passenger_flow.py`
  - `core/payment_flows.py`
  - `core/selectors.py`
  - Impacto: edición localizada, menos contexto en cada tarea.
- Centralizar selectores frecuentes en constantes versionadas.
  - Impacto: menor costo al adaptar cambios de frontend SKY.
- Añadir tests unitarios de `cli.py` (parsing y precedence).
  - Impacto: evitar regressions de flags sin ejecutar browser completo.

## P2 (baja prioridad)

- Migrar persistencia GUI a schema versionado.
  - Impacto: upgrades seguros de `.sky_gui_settings.json`.
- Crear comando `make doctor` para validar entorno (tkinter, playwright, python, CDP reachability).
  - Impacto: onboarding más rápido.

## 2) Redundancia detectada

- `AGENTS.md` y `docs/AI_CONTEXT_PACK.md` cubren ambos mapa de archivos.
  - Decisión: mantener ambos, pero usar `AI_CONTEXT_PACK` como entrada primaria.
- `README.md` y `docs/CHANGE_PLAYBOOK.md` ambos incluyen comandos de validación.
  - Decisión: mantener comandos solo mínimos en README; detalle operativo en `docs/`.

## 3) Glossary rápido

- `CFG`: configuración final resuelta por `cli.py` (defaults + overrides).
- `Checkpoint`: pausa intencional del flujo para inspección manual.
- `CDP`: Chrome DevTools Protocol para controlar Chrome ya abierto.
- `Smoke`: prueba rápida de salud de flujo (no validación exhaustiva).
- `Modo exploración`: ejecución que captura evidencia UI por etapa.
- `Modo log limpio`: filtro visual para mostrar solo eventos importantes.
