# AI Context Pack (Low-Token)

Resumen mínimo para que un agente entienda el repo rápido sin cargar todo el código.

## 1) Entrypoints

- `./run.sh`: bootstrap macOS-first + abre GUI.
- `gui.py`: UI que arma comando CLI y ejecuta `test_sky.py`.
- `test_sky.py`: automatización Playwright end-to-end.
- `cli.py`: parsea flags y genera `CFG`.

## 2) Config precedence

1. `config/*.py` (defaults)
2. flags CLI (`cli.py`)
3. GUI persiste preferencias y vuelve a inyectar por flags

## 3) Dónde tocar

- UX/UI/presets/tooltips/log visual: `gui.py`
- Flags/argumentos: `cli.py`
- Navegación/selectores/payments: `test_sky.py`
- Defaults de negocio: `config/*.py`
- One-command startup: `run.sh`

## 4) Flujo funcional

Home -> búsqueda -> selección vuelo/tarifa -> extras -> pasajeros -> checkout -> pago -> cierre.

Checkpoints:
- `BUSQUEDA`
- `SELECCION_TARIFA`
- `DATOS_PASAJERO`
- `CHECKOUT`
- `PAGO`

## 5) Riesgos típicos

- Cambio en selectores de UI de SKY.
- Diferencias de comportamiento entre CDP y navegador lanzado por Playwright.
- Popups/modales (login, cookies, overlays) tapando botones.
- Flujos de pago por market con estructuras distintas.

## 6) Validación mínima

```bash
make check
make smoke-busqueda
make smoke-checkout
```

## 7) Estado persistente local

- `.sky_gui_settings.json`: preferencias de GUI y presets custom.

## 8) Docs ampliadas

- `AGENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/CHANGE_PLAYBOOK.md`
- `docs/REGRESSION_MATRIX.md`
- `CHANGELOG.md`
