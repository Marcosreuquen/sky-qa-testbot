# 📋 Casos de Prueba - Sky Airline Bot

Este documento describe los diferentes casos de prueba que se pueden ejecutar con el bot.

---

## 🎯 Caso 1: Flujo Básico Solo Ida (Actual)

**Descripción:** Compra de vuelo solo ida con pasajero adulto y pago con tarjeta de prueba

### Paso a Paso:

#### 1️⃣ Búsqueda de Vuelo
- **Tipo de vuelo:** Solo ida
- **Origen:** Santiago (SCL)
- **Destino:** La Serena (LSC)
- **Fecha:** Día 16 disponible desde hoy (o último disponible si hay menos de 16)
- **Pasajeros:** 1 adulto

#### 2️⃣ Selección de Vuelo
- **Vuelo:** Primer vuelo disponible con botón "Elegir vuelo"
- **Tarifa:** Plus (segunda opción) o primera disponible
- **Extras:**
  - ❌ Upgrade de tarifa (rechazado)
  - ❌ Selección de asientos
  - ❌ Equipaje adicional
  - ❌ Seguros

#### 3️⃣ Datos del Pasajero
- **Nombre:** Erick
- **Apellido:** Test
- **Email:** erickr@email.co
- **Género:** Masculino
- **Fecha de nacimiento:** 21/04/1999 (25 años)
- **País de emisión:** Argentina
- **Tipo de documento:** DNI
- **Número de documento:** 19999
- **Teléfono:** +51 11322323

#### 4️⃣ Checkout
- **Método de pago:** Niubiz (tarjeta de crédito/débito)
- **Datos de contacto:** Mismo pasajero

#### 5️⃣ Pago
- **Tipo de tarjeta:** American Express (test)
- **Número:** 371204534881155
- **Fecha de expiración:** 03/28
- **CVV:** 111
- **Titular:** Erick Test (auto-completado)

#### 6️⃣ Confirmación
- ✅ Aceptación de términos y condiciones
- 🚀 Click en "Ir a pagar"

### Configuración en el código:
```python
URL_INICIAL = "https://initial-sale-qa.skyairline.com/es/peru"
VUELO_ORIGEN = "Santiago"
VUELO_DESTINO = "La Serena"
DIAS_A_FUTURO = 16
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
TARJETA = {
    "numero": "371204534881155",
    "fecha": "03/28",
    "cvv": "111"
}
CHECKPOINT = None
```

---

## 🎯 Caso 2: [Template - Completa según necesites]

**Descripción:** [Describe qué valida este caso]

### Paso a Paso:

#### 1️⃣ Búsqueda de Vuelo
- **Tipo de vuelo:** [Solo ida / Ida y vuelta]
- **Origen:** [Ciudad origen]
- **Destino:** [Ciudad destino]
- **Fecha:** [Configuración de fecha]
- **Pasajeros:** [Cantidad y tipo]

#### 2️⃣ Selección de Vuelo
- **Vuelo:** [Cuál vuelo seleccionar]
- **Tarifa:** [Light / Plus / Full / Top]
- **Extras:** [Qué extras seleccionar o rechazar]

#### 3️⃣ Datos del Pasajero
- **Nombre:** [Nombre]
- **Apellido:** [Apellido]
- **Email:** [Email]
- **Género:** [Masculino / Femenino]
- **Fecha de nacimiento:** [DD/MM/AAAA]
- **País de emisión:** [País]
- **Tipo de documento:** [Pasaporte / DNI / RUT / etc.]
- **Número de documento:** [Número]
- **Teléfono:** [Código país + número]

#### 4️⃣ Checkout
- **Método de pago:** [Niubiz / Otro]
- **Datos de contacto:** [Configuración]

#### 5️⃣ Pago
- **Tipo de tarjeta:** [Visa / Mastercard / Amex]
- **Número:** [Número de prueba]
- **Fecha de expiración:** [MM/YY]
- **CVV:** [CVV]

#### 6️⃣ Confirmación
- [Acciones finales]

### Configuración en el código:
```python
# Copia y modifica según el caso
```

---

## 📊 Casos de Prueba Sugeridos

### Variaciones de Vuelo:
- ✈️ **Caso 3:** Ida y vuelta (misma ruta)
- 🌎 **Caso 4:** Ruta internacional (Santiago - Buenos Aires)
- 📅 **Caso 5:** Vuelo para mañana (fecha cercana)
- 👨‍👩‍👧‍👦 **Caso 6:** Múltiples pasajeros (2 adultos, 1 niño)

### Variaciones de Pasajero:
- 🛂 **Caso 7:** Pasajero con Pasaporte (en lugar de DNI)
- 👶 **Caso 8:** Pasajero menor de edad
- 👴 **Caso 9:** Pasajero adulto mayor

### Variaciones de Tarifa:
- 💺 **Caso 10:** Tarifa Light (sin extras)
- 🎒 **Caso 11:** Tarifa Full (con equipaje)
- ⭐ **Caso 12:** Tarifa Top (todos los beneficios)

### Variaciones de Pago:
- 💳 **Caso 13:** Visa (en lugar de Amex)
- 💳 **Caso 14:** Mastercard
- ❌ **Caso 15:** Tarjeta inválida (validar error)

### Casos con Checkpoints:
- 🛑 **Caso 16:** Pausa en CHECKOUT (validar datos antes de pagar)
- 🛑 **Caso 17:** Pausa en DATOS_PASAJERO (llenar datos manualmente)
- 🛑 **Caso 18:** Pausa en PAGO (probar diferentes tarjetas)

---

## 🔧 Cómo Crear un Nuevo Caso de Prueba

### Opción 1: Modificar configuración directamente
1. Edita las variables en `test_sky_peru.py` (líneas 8-44)
2. Ejecuta el bot: `python test_sky_peru.py`

### Opción 2: Crear archivo de configuración por caso (Futuro)
```python
# casos/caso_01_solo_ida.json
{
  "vuelo": {
    "tipo": "solo_ida",
    "origen": "Santiago",
    "destino": "La Serena",
    "dias_futuro": 16
  },
  "pasajero": {...},
  "tarjeta": {...}
}
```

---

## 📝 Notas

- Los casos usan datos de **prueba** (tarjetas test, documentos ficticios)
- El entorno es **QA**: `https://initial-sale-qa.skyairline.com/es/peru`
- Para producción, se requieren datos reales y validación adicional

---

**Última actualización:** 2026-02-06
