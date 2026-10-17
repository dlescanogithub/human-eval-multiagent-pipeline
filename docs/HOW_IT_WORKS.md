# Cómo funciona

Esto es para contarlo en una entrevista, en criollo. **100% sintético; dominio ficticio.** Mirá: la empresa se llama Nortia Learning y el curso es "Foundations of Fictional Logistics". No es un cliente real. Fijate que los números de acuerdo entre revisores no salen de personas.

## La analogía

Pensalo como la redacción de un boletín interno. Hay un redactor, un corrector que solo puede afirmar lo que está en una ficha, y un editor que devuelve el texto. Nadie manda el boletín a la imprenta si el jefe de sección no firmó. El cuaderno de "esto ya lo dijimos" está arriba de la mesa: es el running summary. Si el redactor vuelve a contar el mismo párrafo, el corrector lo frena, aunque el párrafo suene bien.

## El recorrido, paso a paso

1. El curso entra como un archivo: objetivos, nada de magia. El corpus es otra ficha, chica y ficticia, con ids (`F-WAYBILL`, `F-HUB`, y el resto).
2. El writer (un cassette, no un modelo pago) propone el índice.
3. Para cada lección, el writer recibe el índice de esa lección y el resumen de lo que ya se aceptó. La primera versión de la lección 2, en el cassette feliz, suelta el dato del hub sin cita. El checker lo ve.
4. El verifier cassette opina. El checker no le cree: vuelve a mirar si cada claim tiene un id que existe y si el texto se parece a esa ficha (Jaccard de palabras).
5. El critic cassette devuelve puntajes y un flag `request_revision`. Si el checker no está limpio, o el critic pide otra vuelta, y todavía hay presupuesto (máximo 3 en el curso feliz), se llama otra vez al writer. En el demo, la lección 2 se arregla en la segunda pasada y ahí para.
6. Si la lección queda limpia, sus temas entran al resumen. La siguiente lección los ve. Si no queda limpia, no entra: por eso un cassette que repite la lección 1 no contamina el resumen, y el objetivo que debía cubrir queda descubierto.
7. Lo que pasó el checker va a una cola. No está publicado. Publicar es un estado local, `approved`.
8. El demo llena la cola con etiquetas sintéticas, con semilla, y lo dice en el reporte. Vos podés no usarlas: `python -m hemp generate` deja la cola en `pending`, y `python -m hemp review decide` o la página en `127.0.0.1` anotan un revisor.
9. Si la confianza del critic es menor a 0.7, la lección pide 3 revisores en vez de 2. En el curso feliz eso le pasa a L4 (confianza 0.55).
10. La regla de publicación mira la rúbrica `1.0.0`: cantidad de etiquetas, safety en 5 para cada una, y el promedio de cada dimensión contra el mínimo. Recién ahí el estado pasa a `approved`.
11. Todo queda en un JSONL: cada revisión, la versión de la rúbrica, quién (o qué cassette) actuó, y la decisión.

El gate de eval no compara la lista de llamadas. Pregunta invariantes: ¿se publicó algo sin cita? ¿algo marcado como bloqueante? ¿hubo una acción externa? ¿el resumen coincide con lo aceptado? ¿el costo simulado entra en el tope? ¿las etiquetas dicen que son sintéticas?

## Glosario

| Palabra | Qué es acá |
| --- | --- |
| Cassette | Un JSON escrito a mano con la respuesta de cada paso. No es una grabación de un proveedor. |
| Running summary | La lista de lecciones, temas y objetivos ya aceptados. Se manda en el pedido del writer y se guarda en el trace. |
| Claim | Una oración que se anima a afirmar algo, con ids de ficha. |
| Checker | Código. No es otro modelo. |
| Rúbrica | `rubrics/rubric-v1.json`. Accuracy, clarity, flow, no-redundancy, safety. |
| Kappa / alpha | Acuerdo entre etiquetas. En este repo las etiquetas son sintéticas. |
| Gate | `python -m hemp eval`. Si el cassette malo no hace fallar la calidad, el comando de regresión no sale en rojo y CI lo marca. |
| [EST] | Un número ilustrativo, no medido en un equipo real. |

## Límites, en serio

- No mira un vector database. La ficha entra entera, son cinco hechos.
- No publica afuera. No hay LMS ni mail.
- No sabe si algo es verdad en el mundo. Sabe si se parece a la ficha y si citaste el id.
- La página local no tiene login. Es para tu máquina.
- El kappa de claridad 0.5 del demo está sembrado a propósito. No lo cites como un estudio.
- El costo en dólares sale de una tarifa inventada. Los tokens sí salen del cassette.

Si te preguntan "¿y en producción?", la respuesta honesta está en [ADAPT_TO_A_REAL_CLIENT.md](ADAPT_TO_A_REAL_CLIENT.md): primero discovery, después sombra, después el gate. Este repo es el ensayo con datos ficticios.
