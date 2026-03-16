# Bot Frictions

Registro de parches, inconsistencias y comportamientos frágiles detectados durante ejecuciones reales del bot.

Objetivo:
- dejar trazabilidad separada de los fixes tácticos,
- facilitar revisiones de causa raíz,
- priorizar mejoras que impactan fuerte la experiencia de uso.

## 2026-03-16

### P0 · Home de Stage puede quedar parcialmente hidratada en búsqueda

- En `CL stage` se observó que origen/destino/fecha podían existir en DOM pero no estar realmente aplicados al buscador todavía.
- El datepicker de dos meses permitía clickear el día correcto, pero el bot podía confundir texto visible del calendario con valor ya aplicado en el input.
- Impacto:
  - la búsqueda seguía en `BUSQUEDA`,
  - el usuario veía el campo de fecha vacío,
  - el flujo parecía continuar “sin elegir nada” y podía derivar en loops posteriores.
- Fix táctico aplicado:
  - validación de fecha endurecida contra el valor real del input,
  - selección del día anclada al `vc-pane`/`vc-title` correcto del calendario,
  - corte explícito para no avanzar a extras si la etapa sigue en `BUSQUEDA`.
- Causa raíz sugerida:
  - esperar señales semánticas de home hidratada por campo, no sólo por presencia de wrappers,
- separar en código “calendario abierto” de “fecha aplicada”,
- agregar smoke fijo de Stage para `origen -> destino -> fecha -> búsqueda`.

## 2026-03-13

### P0 · Pantalla `seats` cambia entre QA y Stage

- QA mostró CTA `Continuar al siguiente vuelo`.
- Stage mostró CTA `Quiero un asiento aleatorio`.
- En ambos ambientes apareció además un modal posterior para continuar sin elegir asiento.
- Impacto:
  - el bot quedaba frenado hasta timeout,
  - la experiencia parecía “colgada” aunque la página sí había cargado.
- Fix táctico aplicado:
  - reintentos en `core/search_flow.py`,
  - soporte para ambas variantes de CTA,
  - manejo del modal `Continuar sin elegir` / `Seguir sin elegir`.
- Causa raíz sugerida:
  - centralizar selectores/versiones de UI por etapa,
  - medir con evidencia si la variante depende de ambiente, market o feature flag.

### P0 · Hidratación lenta/inconsistente en `seats` y `additional-services`

- Se observaron etapas donde la URL ya había cambiado, pero los botones todavía no existían o no estaban listos para click.
- Impacto:
  - sensación de lag,
  - reintentos visibles en logs,
  - riesgo de falsos negativos si los timeouts son cortos.
- Fix táctico aplicado:
  - reintentos tolerantes antes de abortar,
  - waits más largos en transición de vuelo a tarifa.
- Causa raíz sugerida:
  - esperar por señales de UI semánticas de cada pantalla,
  - registrar tiempo de hidratación por ambiente para detectar regresiones.

### P1 · Carga de tarifas después de elegir vuelo puede tardar más de 5s

- Al seleccionar vuelo, la grilla de tarifas no siempre aparecía dentro del timeout corto original.
- Impacto:
  - fallas intermitentes en selección de vuelo,
  - percepción de fragilidad del flujo.
- Fix táctico aplicado:
  - aumento de espera para la grilla de tarifas.
- Causa raíz sugerida:
  - instrumentar tiempos por market/ambiente,
  - validar si hay skeleton o evento más estable que el selector actual.

### P1 · Equipaje/ancillaries todavía con variabilidad alta

- Se agregó soporte de parámetros para `--maletas-cabina` y `--maletas-bodega`.
- El flujo ya navega correctamente por `additional-services`, pero la suma efectiva de maletas sigue siendo best-effort y mostró inconsistencias en QA.
- Impacto:
  - el bot puede llegar a checkout sin haber confirmado la maleta solicitada,
  - el usuario no siempre distingue entre “navegó bien” y “ancillary aplicado”.
- Estado actual:
  - CLI/GUI/presets ya aceptan parámetros,
  - navegación a checkout validada,
  - aplicación real de equipaje todavía requiere endurecimiento adicional.
- Causa raíz sugerida:
  - mapear selectores estables del drawer/panel lateral de equipaje,
  - validar visualmente subtotal o cantidad final antes de continuar,
  - separar “intento de agregar” de “confirmación efectiva”.

### P2 · Selectores de UI todavía dispersos

- La sesión confirmó otra vez que un cambio visual obliga a tocar varias heurísticas dentro de `core/search_flow.py`.
- Impacto:
  - mantenimiento más lento,
  - mayor riesgo de regresiones por ambiente.
- Causa raíz sugerida:
  - mover selectores/versiones a un módulo dedicado por pantalla.

### P1 · Checkout puede ocultar pasarelas detrás de `Más medios de pago`

- En checkout PE se detectó que la lista de pasarelas puede venir colapsada detrás del botón `Más medios de pago`.
- Impacto:
  - el bot no encontraba Niubiz/Webpay/Cielo aunque el contenido sí estuviera presente en DOM,
  - la carga de tarjeta fallaba por no abrir ese paso intermedio.
- Fix táctico aplicado:
  - expansión automática del bloque de medios de pago antes de seleccionar la pasarela,
  - espera tolerante para layouts donde la pasarela tarda en quedar visible.
- Causa raíz sugerida:
  - centralizar selectores del checkout,
  - validar explícitamente estado expandido/colapsado de la sección en vez de depender de texto visible.
