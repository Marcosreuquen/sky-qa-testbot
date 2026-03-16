# Casos de Prueba - Bot Sky Airline

Comandos listos para copiar y pegar.

## Arranque más simple (1 comando)
```bash
./run.sh
```

## Preparación
```bash
cd bot-skyairline
source venv/bin/activate
```

## Interfaz visual (sin CLI)
```bash
venv/bin/python gui.py
```

En la UI, si marcas **Usar Chrome abierto** intentará iniciarlo automáticamente si no está activo.
La UI recuerda tus últimos ajustes (market, pasajeros, checkpoint, etc.) para la siguiente ejecución.
Los campos de pasajero/tarjeta vienen precargados y siempre se aplican (puedes editarlos antes de ejecutar).

## Usar Chrome abierto (CDP)
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-cdp-sky
venv/bin/python -u test_sky.py --usar-chrome-existente --cdp-url http://127.0.0.1:9222
```

## Flujos principales (visibles)

### 1) Solo ida, Perú, 1 adulto
```bash
venv/bin/python -u test_sky.py --market PE --tipo-viaje ONE_WAY --adultos 1 --ninos 0 --infantes 0 --checkpoint CHECKOUT
```

### 2) Ida y vuelta, Perú, 1 adulto
```bash
venv/bin/python -u test_sky.py --market PE --tipo-viaje ROUND_TRIP --adultos 1 --ninos 0 --infantes 0 --checkpoint CHECKOUT
```

### 3) Solo ida, Perú, 2 adultos y 1 niño
```bash
venv/bin/python -u test_sky.py --market PE --tipo-viaje ONE_WAY --adultos 2 --ninos 1 --infantes 0 --checkpoint CHECKOUT
```

### 4) Ida y vuelta, Perú, 2 adultos y 1 infante
```bash
venv/bin/python -u test_sky.py --market PE --tipo-viaje ROUND_TRIP --adultos 2 --ninos 0 --infantes 1 --checkpoint CHECKOUT
```

## Variante con exploración de frontend

### Guarda screenshots/reportes por etapa para revisar diferencias de UI
```bash
venv/bin/python -u test_sky.py --market PE --tipo-viaje ROUND_TRIP --adultos 1 --ninos 0 --infantes 0 --modo-exploracion --checkpoint CHECKOUT
```

## Smoke útil para Stage (fecha+búsqueda)

### Valida que origen/destino/fecha avancen correctamente antes de tarifa
```bash
venv/bin/python -u test_sky.py --market CL --ambiente stage --tipo-viaje ONE_WAY --origen Santiago --destino "Buenos Aires" --dias 16 --adultos 1 --ninos 0 --infantes 0 --checkpoint BUSQUEDA
```

## Flags que más se tocan
- `--market PE|CL|AR|BR`
- `--ambiente qa|tsts|stage`
- `--tipo-viaje ONE_WAY|ROUND_TRIP`
- `--adultos N`
- `--ninos N`
- `--infantes N`
- `--checkpoint BUSQUEDA|SELECCION_TARIFA|ANCILLARIES|LLEGADA_DATOS_PASAJERO|DATOS_PASAJERO|CHECKOUT|PAGO`
- `--seleccion-asiento SKIP|AUTO`
- `--maletas-cabina N`
- `--maletas-bodega N`
- `--modo-exploracion`

Nota: `--dias` menor a 16 muestra advertencia antifraude, pero respeta el valor indicado.
