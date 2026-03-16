# Orquestacion y Desarrollo

Notas pensadas para desarrollo, operacion humana del bot y orquestacion de IA.

No son tareas del bot en si, sino mejoras de forma de trabajo que pueden bajar friccion en futuras iteraciones.

## 1. Separar claramente modos de trabajo

Conviene tratar como modos distintos:

- `smoke aislado`: navegador levantado por Playwright para validar regresiones sin ruido externo,
- `CDP/manual`: Chrome compartido para editar, observar y corregir durante runtime.

Beneficio:
- menos sesiones contaminadas,
- menos diagnosticos falsos por usar el mismo browser mientras trabajas,
- mejor trazabilidad cuando algo falla.

## 2. Convertir hallazgos reales en checklist corto

Cada vez que aparezca una regresion real importante, conviene preguntarse:

- esto merece un smoke dedicado,
- esto merece una entrada en `BOT_FRICTIONS`,
- esto merece una tarea en `PENDING_GLOSSARY`,
- esto merece una nota para producto/UX.

Beneficio:
- la experiencia del repo se vuelve acumulativa,
- no dependes de memoria oral de lo que paso.

## 3. Cerrar cada iteracion en dos niveles

Buena practica que ya estas aplicando y vale reforzar:

- commit funcional,
- luego commit de docs/orden si hace falta.

Beneficio:
- historial mas legible,
- rollback mas facil,
- menor mezcla entre fix tecnico y narrativa.

## 4. Definir un contrato minimo por etapa

Para busqueda, pasajeros, ancillaries, checkout y pago conviene tener siempre claro:

- que significa `pantalla visible`,
- que significa `dato aplicado`,
- que significa `listo para continuar`.

Beneficio:
- menos heuristicas ambiguas,
- menos bugs por DOM visible que no implica estado real.

## 5. Reducir dependencia de diagnostico manual repetido

Cuando algo te haga perder tiempo mas de una vez, conviene formalizarlo:

- smoke nuevo,
- doc nueva,
- selector centralizado,
- helper semantico,
- o regla de proceso.

Beneficio:
- cada problema deja capacidad instalada en el repo.

## 6. Cuando usar IA y cuando cortar a decision humana

Conviene que la IA empuje implementacion, validacion y orden,
pero que las decisiones de producto/UX y priorizacion comercial queden en documentos de lectura humana.

Buena separacion:
- `docs/agent/`: operacion del bot, regresion, arquitectura,
- `docs/human/`: decisiones de producto, forma de trabajo, oportunidades de mejora.

## 7. Proximo salto de madurez recomendado

Si hubiera que elegir una sola mejora de proceso para el repo, seria esta:

crear un circuito fijo de iteracion:

1. reproducir,
2. corregir,
3. agregar smoke,
4. actualizar friction log,
5. actualizar backlog priorizado,
6. decidir si tambien impacta UX/producto.

Eso te deja una base muy reusable para otros desarrollos con agentes y automatizaciones fragiles.
