# Oportunidades Mejora UX Sky

Documento de oportunidades UX para la experiencia web de SKY.

Este material no describe mejoras del bot. El foco esta puesto en la experiencia
de una persona que busca, configura y compra un vuelo en la pagina.

## Resumen Ejecutivo

La mayor oportunidad de mejora no parece estar en agregar mas funcionalidad,
sino en volver mas confiable y legible el tramo mas sensible del funnel:

`home de busqueda -> seleccion de fecha -> resultados -> extras -> checkout`

Hoy la experiencia parece sufrir en tres dimensiones:

- **claridad de estado**: la interfaz no siempre comunica si un dato ya quedo aplicado,
  si aun esta cargando o si realmente ocurrio un error;
- **consistencia de comportamiento**: algunos componentes parecen “estar” pero no necesariamente
  estan listos para usarse, lo que genera dudas y acciones repetidas;
- **continuidad del flujo**: hay transiciones que se sienten fragiles, con mensajes residuales,
  drawers que se re-renderizan o pasos importantes ocultos.

En términos de UX, esto erosiona confianza. La persona usuaria puede completar el flujo,
pero siente que la pagina no responde de forma predecible.

Tambien se observa una diferencia importante entre desktop y mobile:

- **mobile** presenta una home mas enfocada y lineal;
- **desktop** expone mas estados residuales, mas ruido visual y una convivencia menos clara
  entre formulario y mensajes de resultado/error.

## Principios de Diseño Recomendados

Antes de entrar en mejoras puntuales, conviene alinear algunos principios:

1. **Un estado visible debe significar algo real**
   Un campo no deberia parecer listo si todavia no esta realmente aplicado.

2. **Cada transicion debe tener una semantica clara**
   `cargando`, `faltan datos`, `sin resultados` y `error tecnico` no deberian compartir
   el mismo lenguaje visual.

3. **El usuario no deberia tener que adivinar si la accion funciono**
   Seleccionar una ciudad o una fecha debe producir una confirmacion inmediata y comprensible.

4. **El flujo deberia proteger de errores evitables**
   Si un dato critico no esta completo, la interfaz deberia prevenir el avance en lugar de permitir
   estados ambiguos.

5. **La validacion debe ayudar, no castigar**
   Deshabilitar un CTA sin explicacion suele ser tan confuso como permitir avanzar sin guia.
   La mejor practica, en general, es combinar prevencion suave + feedback explicito al intento.

## Prioridad P0

### 1. Rediseñar el estado de la home de busqueda

**Problema**

La home parece cargar parcialmente: muestra campos, labels y hasta mensajes de error/respuesta
antes de transmitir con claridad si el formulario esta realmente listo.

**Impacto UX**

- baja la confianza desde el primer paso,
- lleva a intentos prematuros de interacción,
- hace que el error “se sienta del usuario” cuando en realidad el sistema aun no consolidó estado.

**Recomendaciones**

- No mostrar errores de disponibilidad en la home antes de una búsqueda real.
- No pintar el formulario como inválido mientras todavía hay datos resolviéndose.
- Separar visualmente estos estados:
  - formulario listo,
  - formulario incompleto,
  - búsqueda en progreso,
  - sin resultados,
  - error técnico.
- Definir si la home debe ser un “formulario limpio” o una “pantalla con memoria de una búsqueda anterior”.
  Hoy parece quedar en un punto medio confuso.

**Quick wins**

- limpiar mensajes residuales al volver a home,
- no mostrar validaciones en rojo hasta que haya interacción o submit,
- si el CTA esta deshabilitado, explicar exactamente por que,
- si el CTA permite click, marcar con claridad el primer faltante al intentar avanzar.

### 2. Hacer inequívoca la confirmación de fecha

**Problema**

El datepicker de dos meses no siempre deja claro cuándo la fecha quedó realmente aplicada
al campo. El sistema puede dar sensación de selección visual sin una confirmación fuerte.

**Impacto UX**

- se puede interpretar que ya se eligió la fecha cuando el formulario todavía no la consolidó,
- aumenta la ansiedad de “¿quedó o no quedó?”,
- genera retrabajo, clicks repetidos y búsquedas fallidas.

**Recomendaciones**

- Actualizar el valor del input inmediatamente luego de seleccionar un día.
- Cerrar el calendario o mostrar una señal inequívoca de confirmación.
- Diferenciar visualmente:
  - día seleccionado,
  - día actual,
  - días no disponibles,
  - días de otro mes.
- Deshabilitar `Buscar vuelo` hasta que la fecha esté aplicada de verdad.

**Quick wins**

- reforzar estilo del día seleccionado,
- reflejar el valor elegido en el campo antes de cualquier otra transición,
- evitar que el calendario quede abierto en un estado ambiguo.

### 3. Diseñar una estrategia de validacion mas comprensible

**Problema**

En formularios cortos como la home de busqueda, un CTA completamente bloqueado puede ser opaco
si no comunica que falta. Pero un CTA siempre habilitado tambien puede generar frustracion
si devuelve errores tardios y dispersos.

**Impacto UX**

- si el CTA no responde, parece roto;
- si responde tarde y mal, parece arbitrario;
- en ambos casos se rompe la sensacion de progreso.

**Recomendacion**

Adoptar un patron mixto:

- prevencion en dependencias estructurales,
- validacion visible al intento de submit,
- feedback localizado en el primer campo que requiere accion.

Aplicado a este flujo:

- fecha no deberia estar realmente activa sin origen y destino confirmados,
- `Buscar vuelo` no deberia quedar en estado ambiguo,
- al click, si falta algo, el sistema deberia:
  - enfocar el primer campo incompleto,
  - marcarlo visualmente,
  - explicar con microcopy breve que se necesita.

**Mejor practica**

No pensar el problema como `habilitar vs deshabilitar`, sino como:
`como entiende la persona que falta y como lo resuelve rapido`.

### 4. Fortalecer la selección de origen y destino

**Problema**

El autocomplete no siempre deja una confirmación visual suficientemente robusta.
Puede sentirse como un estado intermedio más que como una selección cerrada.

**Impacto UX**

- obliga a releer el campo para validar que quedó tomado,
- aumenta clicks redundantes,
- genera dudas antes de pasar al siguiente paso.

**Recomendaciones**

- Mostrar loading explícito mientras resuelve el autocomplete.
- Confirmar la selección con una representación estable tipo `Ciudad (IATA)`.
- Limpiar error del campo apenas la selección queda aplicada.
- Evitar estados visuales donde el label “parece vacío” aunque internamente ya haya valor.

**Quick wins**

- usar una confirmación tipo chip/valor estable,
- mejorar contraste y persistencia del valor aplicado,
- no reutilizar el placeholder como si fuera estado actual.

## Prioridad P1

### 5. Mejorar la transición de búsqueda a resultados

**Problema**

La transición entre home y resultados no siempre comunica si la plataforma está buscando,
si no encontró disponibilidad o si ocurrió un error del sistema.

**Impacto UX**

- la persona queda sin modelo mental claro,
- se confunde “no hay vuelos” con “todavía está cargando”,
- disminuye la sensación de control del proceso.

**Recomendaciones**

- Mostrar un estado intermedio real de `Buscando vuelos...`.
- Evitar reutilizar el mismo layout para “sin disponibilidad” y “error técnico”.
- Explicar, cuando sea posible, si el problema es:
  - disponibilidad,
  - validación del formulario,
  - error temporal del servicio.

### 6. Mejorar la escaneabilidad de resultados

**Problema**

La grilla/lista de resultados permite avanzar, pero la lectura comparativa no parece tan eficiente
como podria ser. Hay bastante densidad de informacion y poca jerarquia entre lo decisivo y lo accesorio.

**Impacto UX**

- cuesta comparar rapidamente precio, horario, aeropuerto y trade-offs,
- el usuario debe dedicar mas esfuerzo cognitivo a cada tarjeta,
- la toma de decision se vuelve menos fluida.

**Recomendaciones**

- Reforzar jerarquia entre:
  - horario,
  - aeropuerto,
  - duracion,
  - precio final,
  - condiciones relevantes.
- Dar mas contexto al orden `Recomendado`: recomendado segun que criterio.
- Hacer mas visible el cambio de fecha en el carrusel superior y su efecto en el precio.
- Revisar si el resumen lateral realmente ayuda a decidir o compite visualmente con la lista principal.

### 7. Hacer más estable la experiencia de ancillaries y asientos

**Problema**

La experiencia de seats/ancillaries parece sensible a variaciones de layout, re-render
y cambios en CTAs.

**Impacto UX**

- percepción de lentitud o fragilidad,
- decisiones menos confiables en un paso con impacto económico,
- menor claridad sobre qué quedó seleccionado.

**Recomendaciones**

- Unificar los CTAs principales y su jerarquía visual.
- Reducir cambios de layout una vez que la persona ya está dentro del paso.
- Mantener visible un resumen estable de lo seleccionado antes de continuar.
- Evitar drawers o paneles que cambian demasiado la posición de controles clave.

### 8. Reducir fricción cognitiva en checkout y pago

**Problema**

Algunos medios de pago quedan detrás de `Otros medios de pago`, lo que introduce
un paso extra de descubrimiento.

**Impacto UX**

- esfuerzo adicional en el tramo más sensible del funnel,
- menor percepción de transparencia sobre opciones disponibles,
- posible abandono si el método esperado “no aparece” a primera vista.

**Recomendaciones**

- Priorizar métodos principales a la vista.
- Mantener expandida la sección una vez abierta.
- Mejorar la relación visual entre método elegido y formulario que se despliega.
- Evaluar si el acordeón realmente simplifica o sólo esconde complejidad.

### 9. Mejorar la pantalla de procesamiento previa a checkout/pago

**Problema**

La pantalla de `Procesando los datos del viaje` comunica muy poco: indica que no se cierre la pantalla,
pero no da nocion de avance, tiempo estimado ni proximo paso.

**Impacto UX**

- transmite espera incierta,
- eleva ansiedad en un momento sensible del funnel,
- hace dificil distinguir entre procesamiento normal y posible cuelgue.

**Recomendaciones**

- Mostrar progreso real o al menos progreso por pasos.
- Indicar tiempo estimado o rango esperado.
- Explicar que ocurrira a continuacion.
- Evitar una pantalla tan vacia si la espera puede superar unos pocos segundos.

## Prioridad P2

### 10. Mejorar performance percibida

**Problema**

Parte de la fricción parece venir de re-render, remount y estados transitorios que hacen
que la interfaz se vea “viva” pero poco estable.

**Recomendaciones**

- Preservar foco e inputs cuando se actualiza la UI.
- Reducir remount innecesario de componentes críticos.
- Usar skeletons o disabled states semánticos en lugar de controles interactuables “a medias”.

### 11. Subir la barra de accesibilidad y claridad operativa

**Recomendaciones**

- Mejorar mensajes inline y microcopy de error.
- Asegurar foco consistente al abrir modales y calendario.
- Diferenciar de forma más clara `disabled`, `loading`, `error` y `success`.
- Revisar jerarquía visual de labels, placeholders y valores aplicados.

### 12. Asegurar paridad de experiencia entre desktop y mobile

**Observacion**

La version mobile de home se percibe mas limpia y enfocada que la desktop.
Eso sugiere una oportunidad: usar mobile como referencia para simplificar desktop,
no al reves.

**Recomendaciones**

- Revisar si desktop esta mostrando demasiado contexto simultaneo.
- Mantener consistencia semantica entre plataformas:
  - mismo significado de error,
  - mismo criterio de completitud,
  - misma confirmacion de valor aplicado.
- Auditar especialmente estados intermedios y mensajes residuales en desktop.

## Quick Wins vs Cambios Estructurales

### Quick wins

- limpiar mensajes residuales en home,
- no mostrar errores prematuros,
- usar validacion visible y guiada en vez de CTA ambiguo,
- reforzar confirmación visual de ciudad y fecha,
- mantener expandido el método de pago una vez elegido,
- dar contexto claro al estado de procesamiento antes de checkout.

### Cambios estructurales

- redefinir semántica de estados de home y resultados,
- rediseñar el datepicker como componente con contrato más claro,
- revisar la arquitectura visual y de interacción de ancillaries,
- replantear cómo se presentan y descubren medios de pago,
- simplificar la composición desktop tomando como base la linealidad de mobile.

## Cómo medir mejora real

Para validar si estas mejoras funcionan, conviene medir:

- tasa de reformulación de origen/destino,
- tasa de apertura repetida del calendario antes de buscar,
- clicks en `Buscar vuelo` con formulario incompleto,
- tiempo y abandono en la pantalla de procesamiento previa a checkout,
- tiempo desde carga de home hasta búsqueda exitosa,
- abandono entre resultados y checkout,
- errores de validación por paso,
- uso real de `Otros medios de pago`.

## Orden Recomendado de Trabajo

1. Home de búsqueda e hidratación real.
2. Estrategia de validación y confirmación de fecha.
3. Autocomplete de ciudades.
4. Transición búsqueda -> resultados y escaneabilidad.
5. Ancillaries, checkout y pantalla de procesamiento.

La oportunidad mayor está en aumentar **confianza, claridad y continuidad**.
La experiencia actual no parece necesitar primero más funcionalidad, sino menos ambigüedad.
