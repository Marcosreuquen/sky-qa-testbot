# Pending + Glossary

Backlog de limpieza técnica y glosario corto para reducir ambigüedad entre agentes.

## 1) Pending (priorizado)

> Formato: **Descripción** · Prioridad · Dificultad · Impacto

---

## P0 — Alta prioridad

- **Formalizar validadores semánticos de “estado aplicado” por campo** · P0 · Dificultad: Media · Impacto: Alto
  - En Stage apareció un falso positivo donde la fecha parecía aplicada por texto visible del calendario, pero el input seguía vacío.
  - El mismo patrón puede repetirse en origen, destino, pasajeros y ancillaries.
  - Solución: helpers explícitos por campo (`origen_aplicado`, `destino_aplicado`, `fecha_aplicada`, `pasajeros_aplicados`) que validen contra el valor real del control y no contra DOM incidental.

- **Agregar smoke automatizado fijo para `CL stage` (`origen -> destino -> fecha -> búsqueda`)** · P0 · Dificultad: Baja · Impacto: Alto
  - El flujo de Stage hoy es suficientemente distinto como para merecer una regresión dedicada.
  - Sin este smoke, cambios en home/datepicker pueden volver a romper búsqueda sin detectarse temprano.
  - Solución: script/comando estable en `scripts/` o `Makefile` y referencia en `docs/REGRESSION_MATRIX.md`.

- **Centralizar selectores CSS/texto en `core/selectors.py`** · P0 · Dificultad: Media · Impacto: Alto
  - Selectores dispersos en `search_flow.py`, `passenger_flow.py`, `payment_flows.py`. Cuando cambia el frontend de SKY un agente debe grep todo el código.
  - Con archivo central: el cambio es 1 línea. Los módulos importan desde allí.

- **Reemplazar polling manual de iframes con `frame_locator` de Playwright** · P0 · Dificultad: Media · Impacto: Alto
  - `_buscar_iframe_mp` (`payment_flows.py:28`): 15 × 1s = 15s máximo por iframe; llamada 3 veces en MercadoPago → hasta 45s de espera.
  - `_buscar_campo_tarjeta` (`payment_flows.py:47`): 20 × 2s = 40s máximo.
  - Reemplazar con `page.frame_locator('iframe[name="..."]').locator('input').wait_for(state="visible", timeout=...)` — Playwright espera en el event loop del navegador en lugar de polling Python.
  - Riesgo bajo: la API `frame_locator` existe en Playwright sync; cambio aislado en `payment_flows.py`.

---

## P1 — Media prioridad

- **Separar módulo de home/date-picker de `core/search_flow.py`** · P1 · Dificultad: Media · Impacto: Alto
  - `search_flow.py` absorbió mucha lógica de hidratación, ciudades, calendario y transición a resultados.
  - Hoy arreglar una regresión de búsqueda obliga a tocar un archivo demasiado grande y con demasiadas responsabilidades.
  - Solución: extraer `home_search.py` / `date_picker.py` o equivalente, manteniendo `search_flow.py` como orquestador.

- **Distinguir claramente pruebas aisladas vs sesiones CDP compartidas** · P1 · Dificultad: Baja · Impacto: Medio
  - Varias iteraciones recientes mezclaron diagnóstico automático con Chrome compartido y generaron ruido de pestañas/sesiones.
  - Solución: documentar y automatizar dos modos estables:
    `smoke aislado` para regresión y `CDP/manual` para edición y debugging visual.

- **Instrumentar tiempos de hidratación por etapa crítica** · P1 · Dificultad: Media · Impacto: Medio-Alto
  - Home, selección de vuelo, ancillaries y checkout mostraron comportamientos intermitentes por carga tardía.
  - Hoy se corrige con waits/reintentos, pero sin visibilidad de cuánto tarda realmente cada etapa.
  - Solución: logs o evidencia liviana por etapa (`home_ready_ms`, `search_results_ms`, `payment_visible_ms`) para detectar regresiones de frontend.

- **Unificar `_snapshot_settings` y `_estado_actual_para_preset` en `gui.py`** · P1 · Dificultad: Media · Impacto: Medio
  - `_estado_actual_para_preset` (`gui.py:237`) y `_snapshot_settings` (`gui.py:979`) serializan los mismos ~20 campos. La diferencia es que `_snapshot_settings` añade `preset` y `presets_guardados`.
  - Cada vez que se añade un campo al formulario hay que actualizarlo en los dos lugares.
  - Solución: `_snapshot_settings` llama a `_estado_actual_para_preset` y agrega los campos extra.

- **Reemplazar `count() + nth()` por `locator.all()` en `_listar_valores_visibles`** · P1 · Dificultad: Baja · Impacto: Bajo-Medio
  - `core/helpers.py:_listar_valores_visibles`: ejecuta `count()` + N llamadas `nth(i)` = N+1 queries al DOM.
  - `locator.all()` resuelve el selector una vez y devuelve lista de handles — 1 sola query.
  - Solo afecta modo exploración (`_capturar_estado_ui`), no el flujo de compra.
  - Riesgo: `locator.all()` puede fallar si el locator es dinámico; safe en contexto de exploración.

- **`CHECKPOINTS_VALIDOS` en `cli.py` y `CHECKPOINT_LABEL_TO_CODE` en `gui.py` no están sincronizados desde una fuente común** · P1 · Dificultad: Baja · Impacto: Bajo
  - Hoy son dos listas independientes. Añadir un checkpoint requiere tocar ambos archivos.
  - Solución: definir `CHECKPOINTS_VALIDOS` en `config/checkpoint.py` (donde ya vive el default) e importar desde `cli.py`.

- **Añadir tests unitarios de `cli.py`** · P1 · Dificultad: Baja · Impacto: Medio
  - `make check` valida el contrato básico; ampliar con edge cases: market inválido, ambiente default, round-trip sin días de retorno, etc.

---

## P2 — Baja prioridad

- **`gui.py._construir_ui()` es un god-method de 233 líneas** · P2 · Dificultad: Alta · Impacto: Bajo
  - Crea todos los frames, widgets, tooltips y secciones en un único método. Difícil de mantener o modificar una sección sin riesgo de romper el layout.
  - Solución: extraer `_construir_seccion_presets()`, `_construir_seccion_vuelo()`, etc.
  - Riesgo: refactor visual — requiere smoke manual de la GUI completa.

- **Migrar persistencia GUI a schema versionado** · P2 · Dificultad: Media · Impacto: Bajo
  - Añadir `"version": 1` en `.sky_gui_settings.json` para migrar campos viejos de forma segura.

- **Crear comando `make doctor`** · P2 · Dificultad: Baja · Impacto: Medio
  - Validar entorno: tkinter, playwright, python ≥ 3.10, CDP disponible.
  - Impacto: onboarding más rápido para nuevos devs y agentes.

- **Unificar logs con niveles estables** · P2 · Dificultad: Media · Impacto: Bajo
  - Los prints en `core/` mezclan prefijos emoji, `---`, `⚠️`, `❌`. Estandarizar a `[INFO]`, `[WARN]`, `[ERROR]` o similar facilitaría parsear logs desde CI.

## ✅ Completado (referencia)

- **Split de `test_sky.py`** — módulos `core/` creados:
  - `core/state.py`, `core/helpers.py`, `core/browser_session.py`
  - `core/search_flow.py`, `core/passenger_flow.py`, `core/payment_flows.py`
  - `test_sky.py` reducido a ~170 líneas (orquestador puro).
- `PAYMENT_DISPATCH` dict en `core/payment_flows.py` — reemplaza if/elif. Para agregar market: 1 línea en el dict.
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
