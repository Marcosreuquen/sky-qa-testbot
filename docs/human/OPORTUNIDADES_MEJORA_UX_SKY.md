# Oportunidades Mejora UX Sky

Hallazgos sobre la pagina de SKY observados durante pruebas reales.

Este documento no apunta a corregir el bot, sino a identificar mejoras de producto/frontend
que tendrian impacto directo en la experiencia de una persona usuaria.

## P0 · Alta prioridad

### 1. Home de busqueda mas confiable

Hoy la pagina a veces muestra `Desde`, `Hacia`, fecha y hasta mensajes de error antes de estar realmente lista.
Eso se siente como una UI viva pero rara.

Mejoras:
- no habilitar fecha hasta que origen y destino esten confirmados de verdad,
- no mostrar estados de error en rojo mientras el campo todavia se esta resolviendo,
- separar visualmente `cargando`, `faltan datos` y `no hay vuelos`,
- evitar que la home muestre un `No encontramos vuelos...` residual antes de una busqueda real.

### 2. Datepicker mucho mas claro

El calendario de dos meses hoy puede quedar visualmente abierto pero sin dejar claro cuando la fecha quedo aplicada al input.

Mejoras:
- al elegir un dia, actualizar el campo inmediatamente y de forma inequivoca,
- que el estado seleccionado del calendario y el valor del input nunca se desincronicen,
- deshabilitar `Buscar vuelo` hasta que la fecha este realmente aplicada,
- mejorar la jerarquia visual del dia seleccionado vs dia `hoy` vs dias no disponibles.

### 3. Autocomplete de ciudades mas robusto

En varias pruebas, origen/destino parecian cargados pero visualmente todavia no era obvio o no estaba firme.

Mejoras:
- mostrar loading explicito en autocomplete,
- confirmar seleccion con chip/label estable tipo `Santiago (SCL)` apenas queda elegida,
- no dejar el campo en un estado intermedio ambiguo,
- limpiar errores apenas la ciudad queda aplicada.

## P1 · Media prioridad

### 4. Resultados de busqueda mas legibles

Mejoras:
- mostrar un estado de `buscando vuelos...` real antes del resultado,
- no reciclar el mensaje de `no encontramos vuelos` como estado por defecto de la home,
- si la busqueda falla, explicar si fue disponibilidad, validacion o error tecnico.

### 5. Asientos y ancillaries mas estables

Mejoras:
- unificar CTAs entre ambientes/versiones,
- evitar drawers laterales que se re-renderizan y mueven controles,
- mantener un resumen estable de lo elegido antes de continuar.

### 6. Checkout y pagos con menos friccion

Mejoras:
- no esconder medios relevantes detras de `Otros medios de pago` salvo que sea realmente necesario,
- recordar el ultimo metodo usado o destacar el principal,
- mantener expandido el bloque de pago una vez que la persona entra ahi.

## P2 · Baja prioridad

### 7. Performance percibida

Mejoras:
- reducir re-render/remount de componentes,
- preservar inputs y foco,
- usar skeletons o disabled states semanticos en vez de dejar controles interactuables a medias.

### 8. Accesibilidad y claridad

Mejoras:
- mejores mensajes inline,
- foco consistente al abrir modales/calendario,
- estados `disabled` / `loading` / `error` mas distinguibles.

## Priorizacion sugerida

Si hubiera que priorizar esto como Staff Engineer con foco producto web:

1. home de busqueda e hidratacion,
2. datepicker y validacion de fecha,
3. autocomplete de ciudades,
4. transicion busqueda -> resultados,
5. ancillaries y checkout.

La mayor mejora de experiencia no parece estar en sumar mas features,
sino en hacer mas confiable el tramo `home -> busqueda -> resultados`.
