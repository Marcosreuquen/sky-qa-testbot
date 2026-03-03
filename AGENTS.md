# AGENTS.md

Guía operativa para agentes (humanos o AI) que trabajan en este repositorio.

## 1. Objetivo del repositorio

Automatizar el flujo QA de compra en SKY (búsqueda, selección de tarifa, pasajeros, checkout y pago) para múltiples markets, con:
- ejecución por CLI (`test_sky.py`),
- ejecución visual (`gui.py`),
- soporte opcional de Chrome abierto por CDP.

## 0. Bootstrap obligatorio para agentes

Primero ejecutar:
```bash
make ai-bootstrap
```

Después leer en orden:
1. `docs/AI_CONTEXT_PACK.md`
2. `CHANGELOG.md` (Unreleased)
3. `docs/PENDING_GLOSSARY.md`
4. `docs/REGRESSION_MATRIX.md`

## 2. Mapa rápido del código

- `test_sky.py`: orquestador principal del flujo Playwright + helpers de interacción.
- `cli.py`: contrato de flags CLI y resolución de configuración final (`CFG`).
- `config/`: defaults de negocio (rutas, vuelo, pasajero, pagos, checkpoint).
- `gui.py`: interfaz visual, presets, persistencia local, armado de comando CLI.
- `run.sh`: bootstrap macOS-first (venv, dependencias, Playwright, UI).
- `README.md`: guía de uso para usuarios finales.
- `CASOS_DE_PRUEBA.md`: comandos de prueba frecuentes.
- `CHANGELOG.md`: historial orientado a debugging de regresiones.
- `docs/AI_CONTEXT_PACK.md`: resumen ultra corto para ahorrar tokens.
- `docs/REGRESSION_MATRIX.md`: batería mínima de regresión.
- `docs/COMMIT_PROTOCOL.md`: estándar de commits y trazabilidad.

## 3. Flujo de configuración (fuente de verdad)

Orden de precedencia:
1. Defaults en `config/`.
2. Overrides por CLI en `cli.py`.
3. Si se usa GUI, la GUI construye los flags CLI que pasan a `test_sky.py`.

Regla clave:
- `test_sky.py` no debería hardcodear defaults de negocio; consumir `CFG`.

## 4. Dónde tocar según el tipo de cambio

- Cambios de UX/UI visual (labels, secciones, tooltips, presets, look&feel): `gui.py`.
- Cambios de parámetros/flags (nuevas opciones): `cli.py` y luego `gui.py` (si aplica en UI).
- Cambios de defaults globales del bot: `config/*.py`.
- Cambios de navegación/selección de elementos web: `test_sky.py`.
- Cambios de arranque “1 comando”: `run.sh` y `README.md`.
- Cambios de documentación de operación: `README.md`, `CASOS_DE_PRUEBA.md`, `docs/*.md`.

## 5. Invariantes de estabilidad

- No romper compatibilidad de flags existentes sin actualizar GUI + README.
- No mover lógica de pago a `gui.py`; el flujo real vive en `test_sky.py`.
- Si se agrega un market, actualizar:
  - `config/pago.py` (`URLS_POR_MARKET`, `MEDIO_PAGO_POR_MARKET`, `TARJETA_POR_MARKET`)
  - flujos de pago en `test_sky.py`
  - opciones CLI y docs.
- Evitar clicks por coordenadas cuando exista selector estable.

## 6. Checklist mínimo antes de entregar cambios

1. Compilar Python:
```bash
python3 -m py_compile test_sky.py cli.py gui.py
```

2. Verificar arranque GUI:
```bash
./run.sh
```

3. Smoke de flujo por CLI (checkpoint para validar navegación):
```bash
venv/bin/python -u test_sky.py --market PE --tipo-viaje ONE_WAY --checkpoint BUSQUEDA
```

4. Si se tocó CDP:
- validar con `--usar-chrome-existente --cdp-url http://127.0.0.1:9222`.

Atajo:
```bash
./scripts/validate_local.sh
```

## 7. Convención para cambios grandes

Cuando un cambio afecte más de un módulo, actualizar además:
- `docs/ARCHITECTURE.md` (si cambia la arquitectura),
- `docs/CHANGE_PLAYBOOK.md` (si cambia dónde tocar para requests comunes),
- `README.md` (si cambia el comportamiento visible para usuario final),
- `CHANGELOG.md` (resumen de impacto y validación).
