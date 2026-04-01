# Playbook de Cambios (AI-first)

Guía práctica: “si me piden X, toco Y”.

## 1. Me piden cambiar defaults (market, pasajeros, tiempos)

- Editar `config/vuelo.py`, `config/rutas.py`, `config/pago.py`, `config/pasajero.py`.
- Si impacta textos de UI o presets iniciales, actualizar `gui.py`.
- Actualizar `README.md`.
- Si afecta housekeeping de evidencias, también revisar `test_sky.py` y `screenshots_pruebas/`.

## 2. Me piden un nuevo flag CLI

1. Agregar flag en `parse_args()` de `cli.py`.
2. Mapearlo a `cfg` en `aplicar_args()`.
3. Consumirlo en `test_sky.py`.
4. Si aplica, exponerlo en `gui.py`.
5. Documentarlo en `README.md`.

## 3. Me piden cambios de interfaz visual

- Todo en `gui.py`:
  - layout/secciones/colapsables/tooltips,
  - presets,
  - texto visible y traducciones de labels.
- No mover lógica de automatización web a GUI.
- Si el control modifica comportamiento real de ejecución, exponer el flag equivalente en `cli.py`.

## 4. Me piden arreglar navegación del flujo web

- Tocar `test_sky.py`:
  - helpers de selector (`_buscar_selector_visible`, `_click_selector_visible`, etc.),
  - pasos del flujo (`_seleccionar_ciudad`, `_seleccionar_fechas`, `_seleccionar_vuelo_y_tarifa`).
- Priorizar selectores semánticos sobre clicks por coordenadas.

## 5. Me piden soporte Chrome abierto / CDP

- `gui.py`: UX CDP (checkbox, botón preparar chrome, url CDP).
- `cli.py`: flags `--usar-chrome-existente`, `--cdp-url`.
- `test_sky.py`: sesión CDP (`connect_over_cdp`, contexto y pestaña).

## 6. Me piden nuevos casos de uso reutilizables

- `gui.py`:
  - `DEFAULT_PRESETS` para casos base,
  - guardar/renombrar/eliminar presets,
  - persistencia en `.sky_gui_settings.json`.

## 7. Me piden “modo más limpio” de logs

- `gui.py`: filtrar líneas en el stream y toggle de “log limpio”.
- Evitar silenciar errores críticos en `test_sky.py`.

## 8. Me piden cambiar reglas antifraude (`--dias`)

- Regla y mensaje en `cli.py` (`aplicar_args()`).
- Constante de referencia en `config/vuelo.py` (`MIN_DIAS_A_FUTURO`).
- Documentación en `README.md` y `CASOS_DE_PRUEBA.md`.

## 9. Me piden agregar o modificar un ambiente (QA/TSTS/Stage/otro)

1. `config/pago.py`: agregar entrada en `AMBIENTES_DISPONIBLES` con el subdominio exacto.
2. `gui.py`: agregar label en `AMBIENTE_LABEL_TO_CODE` (constante al inicio del archivo).
3. No tocar `URLS_POR_MARKET` directamente — se genera desde `get_urls_por_market()`.
4. `AGENTS.md` + este playbook: actualizar si el ambiente tiene comportamiento especial.

> **No tocar** `test_sky.py` — el ambiente solo afecta la URL base, la navegación es igual.

## 10. Me piden agregar un nuevo market (país)

1. `config/pago.py`: `_URLS_BASE`, `MEDIO_PAGO_POR_MARKET`, `TARJETA_POR_MARKET`.
2. `cli.py`: `MARKETS_VALIDOS`.
3. `gui.py`: `MARKET_LABEL_TO_CODE`.
4. `test_sky.py`: flujo de pago específico del market (estructura de formulario varía por gateway).
5. `README.md` y `CASOS_DE_PRUEBA.md`.

## 11. Verificación rápida recomendada

```bash
make check
make smoke-busqueda
make smoke-checkout
```
