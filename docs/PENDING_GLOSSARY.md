# Pending + Glossary

Backlog de limpieza técnica y glosario corto para reducir ambigüedad entre agentes.

## 1) Pending (priorizado)

## P0 (alta prioridad — mayor impacto en eficiencia de agentes IA)

- **Dividir `test_sky.py` (~1900 líneas) en módulos**:
  - `core/search_flow.py` — búsqueda, tipo viaje, fechas, pasajeros
  - `core/passenger_flow.py` — datos de pasajero, avance a checkout
  - `core/payment_flows.py` — `_pagar_*` + `PAYMENT_DISPATCH`
  - `core/selectors.py` — constantes de selectores CSS/texto
  - `core/browser_session.py` — CDP, sesión, contexto Playwright
  - **Por qué es P0**: un agente hoy lee ~1900 líneas por tarea. Con módulos lee ~200. Mayor ROI de tokens del proyecto.
  - Riesgo: refactor grande — validar todos los smokes post-split.

- **Centralizar selectores CSS/texto en `core/selectors.py`**:
  - Hoy están inline dispersos. Cuando cambia el frontend de SKY, un agente hace grep de todo el archivo.
  - Con archivo central: el cambio es una línea.

## P1 (media prioridad)

- Unificar logs de `test_sky.py` en eventos estables.
  - Impacto: menor ruido y menos tokens en debugging.
- Añadir tests unitarios de `cli.py` (parsing y precedence de flags).
  - `make check` ya valida contrato básico; ampliar con edge cases (market inválido, ambiente default, etc.).

## P2 (baja prioridad)

- Migrar persistencia GUI a schema versionado (versión en `.sky_gui_settings.json`).
  - Impacto: upgrades seguros sin romper ajustes guardados.
- Crear comando `make doctor` para validar entorno (tkinter, playwright, python, CDP).
  - Impacto: onboarding más rápido.

## ✅ Completado (referencia)

- `PAYMENT_DISPATCH` dict en `test_sky.py` — reemplaza if/elif. Para agregar market: 1 línea en el dict.
- `validate-ambientes`, `smoke-tsts`, `smoke-stage` en `Makefile`.
- Schema de `CFG` documentado en docstring de `cli.py::aplicar_args()`.
- `make check` valida contrato CLI además de compilación.

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
