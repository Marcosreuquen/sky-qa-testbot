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

## 🔧 Requisitos Previos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

## 📦 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/ErickRRB/sky-qa-testbot.git
cd sky-qa-testbot
```

### 2. Crear entorno virtual

```bash
# En macOS/Linux:
python3 -m venv venv
source venv/bin/activate

# En Windows:
python -m venv venv
venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install playwright
playwright install chromium
```

## ⚙️ Configuración

Antes de ejecutar el bot, puedes personalizar los parámetros en el archivo `test_sky_peru.py`:

### Configuración del vuelo:
```python
VUELO_ORIGEN = "Santiago"
VUELO_DESTINO = "La Serena"
DIAS_A_FUTURO = 16  # Día a seleccionar en el calendario
```

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
```

### 🛑 Checkpoints (Pausas dinámicas):
Puedes detener el bot en puntos específicos del flujo para probar algo manualmente:

```python
CHECKPOINT = None  # Sin pausas intermedias (ejecuta todo el flujo)
```

**Opciones disponibles:**
- `"BUSQUEDA"` - Pausa después de buscar el vuelo
- `"SELECCION_TARIFA"` - Pausa después de seleccionar vuelo y tarifa
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

### Ejecutar el bot:

```bash
python test_sky_peru.py
```

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
