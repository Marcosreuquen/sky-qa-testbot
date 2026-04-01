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

## 3b) Multi-ambiente

El bot soporta 3 ambientes vía `--ambiente`:

| Código | Subdominio           | GUI label |
|--------|----------------------|-----------|
| `qa`   | `initial-sale-qa`    | QA        |
| `tsts` | `initial-sale-tsts`  | TSTS      |
| `stage`| `initial-sale-stage` | Stage     |

- Fuente de verdad: `config/pago.py` → `AMBIENTES_DISPONIBLES`, `get_urls_por_market()`
- **No usar `URLS_POR_MARKET` directamente** — es un snapshot de QA. Usar `get_urls_por_market(ambiente)`.
- Combo en GUI: sección "Flujo", entre País y Tipo de viaje.

## 4) Flujo funcional

Home -> búsqueda -> selección vuelo/tarifa -> extras -> pasajeros -> checkout -> pago -> cierre.

Checkpoints:
- `BUSQUEDA`
- `SELECCION_TARIFA`
- `ANCILLARIES`
- `LLEGADA_DATOS_PASAJERO`
- `DATOS_PASAJERO`
- `CHECKOUT`
- `PAGO`

## 5) Riesgos típicos

- Cambio en selectores de UI de SKY.
- Diferencias de comportamiento entre CDP y navegador lanzado por Playwright.
- Popups/modales (login, cookies, overlays) tapando botones.
- Frontend parcialmente hidratado en home (ciudades/fecha visibles pero no realmente aplicadas).
- Flujos de pago por market con estructuras distintas.

## 6) Validación mínima

```bash
make check
make smoke-busqueda
make smoke-checkout
```

## 7) Estado persistente local

- `.sky_gui_settings.json`: preferencias de GUI y presets custom.
- `screenshots_pruebas/`: evidencia runtime; puede autolimpiarse por semanas al arrancar.

## 8) Docs ampliadas

- `AGENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/CHANGE_PLAYBOOK.md`
- `docs/REGRESSION_MATRIX.md`
- `CHANGELOG.md`
