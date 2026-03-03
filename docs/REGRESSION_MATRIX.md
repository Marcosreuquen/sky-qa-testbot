# Matriz de Regresión

Checklist operativo para detectar rupturas rápido en cambios incrementales.

## 1. Salud estática

```bash
make check
```

Esperado:
- compila `test_sky.py`, `cli.py`, `gui.py` sin errores.

## 2. Flujo PE hasta búsqueda

```bash
make smoke-busqueda
```

Esperado:
- llega a checkpoint `BUSQUEDA`,
- no revienta en selección de origen/destino/fecha/pasajeros.

## 3. Flujo PE hasta checkout

```bash
make smoke-checkout
```

Esperado:
- pasa selección de vuelo/tarifa,
- completa datos de pasajero,
- llega a checkpoint `CHECKOUT`.

## 4. GUI base

Comando:
```bash
./run.sh
```

Esperado:
- abre ventana GUI,
- carga preset inicial,
- botones `Ejecutar/Detener/Limpiar log` responden,
- persisten ajustes al reabrir.

## 5. CDP (opcional pero recomendado)

1) Inicia Chrome con remote debugging.
2) Ejecuta con `--usar-chrome-existente`.

Esperado:
- conecta por CDP,
- ejecuta flujo sin abrir paneles bloqueantes por error,
- no cierra Chrome al finalizar en modo CDP.

## 6. Smoke extendido por tipo de viaje

```bash
venv/bin/python -u test_sky.py --market PE --tipo-viaje ROUND_TRIP --checkpoint CHECKOUT
```

Esperado:
- selecciona ida y vuelta correctamente.

## 7. Criterio de salida

Un cambio se considera estable si:
- pasa `make check`,
- pasa smoke de búsqueda y checkout,
- no introduce cambios inesperados en flags/documentación.
