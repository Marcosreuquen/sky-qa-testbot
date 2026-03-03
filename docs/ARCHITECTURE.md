# Arquitectura del Bot Sky QA

Este documento resume la arquitectura actual para cambios rápidos y seguros.

## 1. Componentes

- `config/`: defaults de negocio y entorno.
- `cli.py`: parsea flags y construye `CFG` final.
- `test_sky.py`: ejecuta el flujo end-to-end con Playwright.
- `gui.py`: UI de ejecución (presets, estado persistente, logs, CDP).
- `run.sh`: bootstrap y ejecución en macOS (prioritario).

## 2. Flujo de ejecución

1. Usuario ejecuta `./run.sh` o `python test_sky.py ...`.
2. `cli.py` resuelve `CFG` (defaults + overrides).
3. `test_sky.py` abre sesión de navegador:
   - local Playwright, o
   - CDP (`--usar-chrome-existente`).
4. Flujo principal:
   - home listo,
   - tipo de viaje/origen/destino/fecha/pasajeros,
   - buscar vuelo,
   - elegir vuelo/tarifa,
   - extras,
   - datos de pasajero,
   - checkout/pago,
   - espera final y evidencia.

## 3. Contratos internos importantes

- `CFG` es el contrato principal entre `cli.py` y `test_sky.py`.
- `CHECKPOINT` soportado: `BUSQUEDA`, `SELECCION_TARIFA`, `DATOS_PASAJERO`, `CHECKOUT`, `PAGO`, o `None`.
- GUI no ejecuta lógica de negocio web; solo arma flags y lanza proceso.

## 4. Persistencia local

- `.sky_gui_settings.json`:
  - última configuración de UI,
  - presets personalizados,
  - estado visual (secciones expand/collapse, preferencias).

No usar este archivo como fuente de verdad de negocio; solo UX local.

## 5. Zonas sensibles (alto riesgo de regresión)

- Selectores de búsqueda/ciudad/fecha/pasajeros en `test_sky.py`.
- Lógica de `Elegir vuelo` y transición a pasajeros/checkout.
- Integraciones de pago por market (`_pagar_niubiz`, `_pagar_webpay`, `_pagar_mercadopago`, `_pagar_cielo`).
- Manejo CDP (reuso de pestañas/contextos).

## 6. Estrategia de cambios recomendada

1. Cambiar una capa por vez (`config`/`cli`/`gui`/`test_sky`).
2. Mantener la API de flags estable.
3. Validar en `CHECKPOINT BUSQUEDA` y `CHECKPOINT CHECKOUT`.
4. Solo después ajustar UX y documentación.
