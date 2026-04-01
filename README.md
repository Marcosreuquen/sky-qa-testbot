# 🤖 Sky QA Test Bot

Bot automatizado de pruebas para el flujo de compra de vuelos en Sky Airline, desarrollado con Playwright y Python.

## 📋 Descripción

Este bot automatiza el proceso completo de compra de un vuelo en el sitio de Sky Airline, incluyendo:
- Búsqueda de vuelos (origen, destino, fecha)
- Selección de tarifa
- Ingreso de datos del pasajero
- Proceso de checkout
- Pago con tarjeta de prueba mediante Niubiz

📖 **Ver casos de prueba documentados:** [`CASOS_DE_PRUEBA.md`](CASOS_DE_PRUEBA.md)

## 🤖 AI-First Development

Si vas a trabajar este repo con agentes (AI o humanos), empieza por:
- [`AGENTS.md`](AGENTS.md) (guía operativa principal)
- [`docs/START_HERE.md`](docs/START_HERE.md) (bootstrap obligatorio)
- [`CHANGELOG.md`](CHANGELOG.md) (historial para ubicar regresiones)
- [`docs/README.md`](docs/README.md) (índice de documentación técnica)
- [`docs/agent/README.md`](docs/agent/README.md) (lectura orientada a agentes)
- [`docs/human/README.md`](docs/human/README.md) (lectura orientada a personas, UX y proceso)
- [`docs/AI_CONTEXT_PACK.md`](docs/AI_CONTEXT_PACK.md) (contexto corto para ahorrar tokens)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) (arquitectura y contratos)
- [`docs/CHANGE_PLAYBOOK.md`](docs/CHANGE_PLAYBOOK.md) (dónde tocar según pedido)
- [`docs/REGRESSION_MATRIX.md`](docs/REGRESSION_MATRIX.md) (checklist anti-roturas)
- [`docs/COMMIT_PROTOCOL.md`](docs/COMMIT_PROTOCOL.md) (estándar de commits)

### Mapa rápido del repositorio

- `test_sky.py`: flujo de automatización end-to-end (Playwright)
- `cli.py`: flags y construcción de `CFG`
- `gui.py`: interfaz visual, presets, persistencia y ejecución
- `config/`: defaults por dominio (rutas, vuelo, pasajero, pago, checkpoint)
- `run.sh`: arranque 1 comando en macOS

### Comandos de validación para contributors/agentes

```bash
make ai-bootstrap
make check
make smoke-busqueda
make smoke-checkout
./scripts/validate_local.sh
```

## 🔧 Requisitos Previos

- macOS (prioridad del proyecto) con shell `bash`/`zsh`
- Python 3.10 o superior con soporte `tkinter`
- `pip` (gestor de paquetes de Python)
- `git`
- Conexión a internet (para Playwright + sitio objetivo)
- Opcional: Google Chrome instalado (si usarás modo **Chrome abierto/CDP**)

## 📦 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/ErickRRB/sky-qa-testbot.git
cd sky-qa-testbot
```

### 2. Arranque rápido (recomendado)

```bash
chmod +x run.sh
./run.sh
```

Alternativa equivalente:
```bash
make run
```

Este comando:
- crea `venv` si no existe
- detecta/usa un Python con soporte `tkinter` (requerido para la UI)
- instala dependencias
- instala Chromium de Playwright
- abre la interfaz visual (`gui.py`)

### 3. Instalación manual (opcional)

```bash
# En macOS/Linux:
python3 -m venv venv
source venv/bin/activate

# En Windows:
python -m venv venv
venv\Scripts\activate
```

### 4. Instalar dependencias

```bash
pip install -r requirements.txt
playwright install chromium
```

## ⚙️ Configuración

Antes de ejecutar el bot, puedes personalizar los parámetros en la carpeta `config/` o pasarlos por CLI en `test_sky.py`:

### Configuración del vuelo:
```python
VUELO_ORIGEN = "Santiago"
VUELO_DESTINO = "La Serena"
DIAS_A_FUTURO = 16  # Día a seleccionar en el calendario
TIPO_VIAJE = "ONE_WAY"  # ONE_WAY o ROUND_TRIP
DIAS_RETORNO_DESDE_IDA = 4  # Solo para ROUND_TRIP
CANTIDAD_ADULTOS = 1
CANTIDAD_NINOS = 0
CANTIDAD_INFANTES = 0
```

> Si usas menos de 16 días, se muestra advertencia de posible riesgo antifraude, pero se respeta el valor indicado.

### Datos del pasajero:
```python
PASAJERO = {
    "nombre": "Erick",
    "apellido": "Test",
    "email": "erickr@email.co",
    "doc_tipo": "DNI",
    "doc_numero": "19999",
    "telefono": "11322323",
    "prefijo_pais": "51",
    "genero": "Masculino",
    "pais_emision": "Argentina",
    "fecha_nac": "21/04/1999"
}
```

### Datos de tarjeta de prueba:
```python
TARJETA = {
    "numero": "371204534881155",
    "fecha": "03/28",  # MM/YY
    "cvv": "111"
}
```

### Tiempos y velocidad:
```python
TIEMPO_PAUSA_SEGURIDAD = 1500  # Pausa antes de interactuar con campos (ms)
VELOCIDAD_VISUAL = 500          # Velocidad de animación del navegador (ms)
ESPERA_FINAL_SEGUNDOS = 600     # 10 minutos antes de screenshot final/cierre
LIMPIAR_EVIDENCIAS_ANTIGUAS = True
SEMANAS_RETENCION_EVIDENCIAS = 2
```

### 🛑 Checkpoints (Pausas dinámicas):
Puedes detener el bot en puntos específicos del flujo para probar algo manualmente:

```python
CHECKPOINT = None  # Sin pausas intermedias (ejecuta todo el flujo)
```

**Opciones disponibles:**
- `"BUSQUEDA"` - Pausa después de buscar el vuelo
- `"SELECCION_TARIFA"` - Pausa después de seleccionar vuelo y tarifa
- `"ANCILLARIES"` - Pausa al llegar a asientos/servicios adicionales
- `"LLEGADA_DATOS_PASAJERO"` - Pausa apenas entra a `passenger-detail`
- `"DATOS_PASAJERO"` - Pausa después de llenar datos del pasajero
- `"CHECKOUT"` - Pausa al llegar al checkout
- `"PAGO"` - Pausa después de llenar datos de pago (antes de clickear "Ir a pagar")
- `None` - Sin pausas (ejecuta el flujo completo)

**Ejemplo de uso:**
```python
CHECKPOINT = "CHECKOUT"  # El bot se detendrá al llegar al checkout
```

Cuando el bot alcance el checkpoint, verás el inspector de Playwright donde podrás:
- ✋ Interactuar manualmente con la página
- 🔍 Inspeccionar elementos
- ▶️ Presionar "Resume" para continuar o cerrar el navegador

## 🚀 Ejecución

### Opción más simple (1 comando)

```bash
./run.sh
```

### Ejecutar el bot:

```bash
python test_sky.py
```

### Ejecutar con interfaz visual (sin flags):

```bash
python gui.py
```

Desde la interfaz puedes:
- Elegir un caso desde el dropdown (se aplica automáticamente)
- Crear, renombrar y eliminar casos personalizados
- Ejecutar y detener el flujo con botones
- Pausar para edición manual y continuar sin reiniciar la ejecución
- Ver logs en tiempo real
- Ajustar la espera final (por defecto 600s = 10 minutos)
- Limpiar evidencias antiguas al iniciar y definir la retención en semanas
- Usar tu Chrome abierto por CDP (sin abrir una instancia nueva)
- Guardar automáticamente tus últimos ajustes para próximas ejecuciones
- Configurar overrides de pasajero/pagador y tarjeta desde la propia UI
- Corregir errores recuperables durante runtime y reanudar desde la etapa detectada
- Caso inicial inmutable: **Solo ida, PE, 1 adulto, flujo completo (sin checkpoint)**

### Usar Chrome ya abierto (CDP)

Desde `gui.py`, marca **Usar Chrome abierto**:
- si Chrome ya está listo para automatización, se conecta y ejecuta en la sesión CDP
- si no está listo, usa **Abrir/Preparar Chrome para automatización**
- `CDP URL` es la dirección técnica de conexión a Chrome (normalmente no necesitas cambiarla)

Si prefieres iniciar Chrome manualmente:
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-cdp-sky
python test_sky.py --usar-chrome-existente --cdp-url http://127.0.0.1:9222
```

### Ejemplos útiles:

```bash
# Ida y vuelta (si usas menos de 16 días, verás advertencia antifraude)
python test_sky.py --market PE --tipo-viaje ROUND_TRIP --dias 16 --dias-retorno 5

# 3 adultos + 1 niño
python test_sky.py --market PE --adultos 3 --ninos 1 --dias 16

# Modo exploración UI (captura screenshots + reporte de controles y se detiene tras búsqueda)
python test_sky.py --market PE --tipo-viaje ROUND_TRIP --adultos 2 --ninos 1 --modo-exploracion --solo-exploracion

# Conservar evidencias por 3 semanas
python test_sky.py --retencion-evidencias-semanas 3

# Desactivar la limpieza automática de evidencias
python test_sky.py --no-limpiar-evidencias-antiguas
```

En modo exploración, el bot guarda evidencia en:
- `screenshots_pruebas/exploracion_<timestamp>/*.png`
- `screenshots_pruebas/exploracion_<timestamp>/*.txt`

Si `LIMPIAR_EVIDENCIAS_ANTIGUAS = True`, al iniciar cada ejecución se eliminan entradas de `screenshots_pruebas/`
con antigüedad mayor a `SEMANAS_RETENCION_EVIDENCIAS`.

El bot se ejecutará con las siguientes características:
- **Navegador visible** (`headless=False`) para que puedas ver el proceso
- **Slow motion** configurado para visualización clara de cada paso
- **Capturas de pantalla** automáticas en caso de errores
- **Pausa final** al terminar para revisar el resultado

## 📸 Capturas de Error

Si el bot encuentra problemas, generará automáticamente screenshots con nombres como:
- `error_campo_tarjeta.png`
- `error_interaccion.png`

Estos archivos NO se subirán al repositorio (están en `.gitignore`).
Además, la limpieza automática puede borrar evidencia vieja para evitar crecimiento indefinido del directorio.

## 🔍 Características Técnicas

- ✅ Manejo robusto de elementos dinámicos
- ✅ Detección automática de iframes de Niubiz
- ✅ Navegación con tabs para campos de pago
- ✅ Validación de estados (visible, editable)
- ✅ Timeouts configurables
- ✅ Manejo de modales y popups

## 📝 Notas

- Este bot está diseñado para **entornos QA/Testing**
- Los datos de tarjeta son **valores de prueba**
- Se requiere conexión a internet estable
- El sitio objetivo es: `https://initial-sale-qa.skyairline.com/es/peru`

## 🐛 Troubleshooting

### Error: "playwright not found"
```bash
pip install playwright
playwright install chromium
```

### El bot va muy rápido
Aumenta el valor de `VELOCIDAD_VISUAL` en la configuración (línea 11).

### Fallan las interacciones con campos de pago
Aumenta el `TIEMPO_PAUSA_SEGURIDAD` (línea 10) para dar más tiempo a que los campos se habiliten.
