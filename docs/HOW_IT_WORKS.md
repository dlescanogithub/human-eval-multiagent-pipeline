# Cómo funciona

Esto es para contarlo en una entrevista, en criollo. **100% sintético; dominio ficticio.** Mirá: la empresa se llama Nortia Learning y el curso es "Foundations of Fictional Logistics". No es un cliente real. Fijate que los números de acuerdo entre revisores no salen de personas.

## La analogía

Pensalo como la redacción de un boletín interno. Hay un redactor, un corrector que solo puede afirmar lo que está en una ficha, y un editor que devuelve el texto. Nadie manda el boletín a la imprenta si el jefe de sección no firmó. El cuaderno de "esto ya lo dijimos" está arriba de la mesa: es el running summary. Si el redactor vuelve a contar el mismo párrafo, el corrector lo frena, aunque el párrafo suene bien.

## El recorrido, paso a paso

1. El curso entra como un archivo: objetivos, nada de magia. El corpus es otra ficha, chica y ficticia, con ids (`F-WAYBILL`, `F-HUB`, y el resto).
2. El writer es un paso que se reproduce desde un cassette. En el camino por defecto no hay una llamada a un modelo.
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
| Kappa / alpha | Métricas de acuerdo. `python -m hemp agreement-demo` las corre sobre 48 ítems sintéticos, con tres confiabilidades documentadas y un intervalo bootstrap. No es un estudio con personas. El curso de 4 lecciones no alcanza para citar un acuerdo. |
| Gate | `python -m hemp eval`. Si el cassette malo no hace fallar la calidad, el comando de regresión no sale en rojo y CI lo marca. |
| [EST] | Un número ilustrativo, no medido en un equipo real. |

## Límites, en serio

- No mira un vector database. La ficha entra entera, son cinco hechos.
- No publica afuera. No hay LMS ni mail.
- No sabe si algo es verdad en el mundo. Sabe si se parece a la ficha y si citaste el id.
- La página local no tiene login. Es para tu máquina.
- El acuerdo que muestra el demo es un computation demo: raters sintéticos, semilla, intervalo. No lo cites como personas. Si más adelante hay etiquetas reales, el camino es el CSV `fixtures/agreement/human_labels_template.csv` y `python -m hemp agreement-import`. Este repo no publica una cifra de acuerdo humano.
- El costo en dólares sale de una tarifa inventada. Los tokens del demo sí salen del cassette.
- El acuerdo juez-contra-humano no está medido. La frase, hasta que completes la planilla, es: judge-vs-human agreement: not measured yet.

## ¿Qué parte es de verdad multiagente?

Mirá: el nombre del repo dice multiagente, y eso se puede leer de más. En el modo por defecto el writer, el verifier y el critic no llaman a un modelo. Son respuestas guardadas en un cassette, en orden. Eso alcanza para probar la orquestación, el checker y los gates. CI corre solo ese modo. Los fakes son deterministas: si repetís el comando, el gate da lo mismo.

live ejecutado en n=1 y n=3, muestra chica, sin tasa. Con `LIVE_LLM=1`, un tope `MAX_LIVE_SPEND_USD` mayor a cero, y la URL, la clave y el modelo en el entorno, el outline, el writer, el verifier y el critic le pegan a una API de chat compatible (completions por HTTP). Cada paso tiene un prompt de sistema que dice qué paso es, qué entra, el esquema JSON de salida con un ejemplo mínimo, y que hay que devolver solo JSON. Cada rol puede tener su modelo: `LLM_MODEL_WRITER`, `LLM_MODEL_VERIFIER`, `LLM_MODEL_CRITIC`. Si no los ponés, usan `LLM_MODEL`. El texto del corpus y lo que dijo el rol anterior viajan como datos, entre marcas `<untrusted-data>`, no como órdenes. El checker sigue siendo código: cada claim citado, nada sin cita se publica, y la redundancia se mide igual. El comando es `python -m hemp live --pieces N`. `make live` es ese comando con `--pieces 1`.

Sin esa configuración el comando sale con código 2 y no abre la red. Si el gasto o los tokens se pasan del tope, sale con código 3 (`BUDGET_EXHAUSTED`). Eso no es un gate rojo: el gate rojo sigue siendo el código 1. Un JSON que no cumple el esquema de ese paso se rechaza con un error que dice qué falta, y hay como máximo dos reintentos con ese error como dato. Cada reintento reserva el peor caso contra el tope antes de llamar. Los precios no están en el repo. Si querés un costo en dólares, exportá `LLM_PRICE_IN_PER_MTOK` y `LLM_PRICE_OUT_PER_MTOK`. Esa cuenta aplica el precio de entrada a cada token de prompt, también a los cacheados si el proveedor los informa, así que el número es una sobreestimación cuando hay caché. El ledger anota `cached_tokens` y no les pone un precio distinto. Si no tenés los dos precios, poné `MAX_LIVE_TOKENS` y el costo queda como `unknown`. El 2026-10-17 hubo dos corridas independientes, afuera de CI, con `LIVE_LLM=1`, tope `MAX_LIVE_SPEND_USD=0.15` y el modelo xAI `grok-4.20-0309-non-reasoning` en writer, verifier y critic. `python -m hemp live --pieces 1` salió 0: 7 llamadas (outline, draft L1, verifier, critic, revise, verifier, critic), el checker aceptó 1/1, el ítem quedó pending, no se publicó nada y `live_result_claimed` quedó en false. Costo real US$0.00785; el repo estimó 0.00879 porque cobra los tokens de prompt cacheados al precio de entrada. `python -m hemp live --pieces 3` salió 0: 25 llamadas, el checker aceptó 1/3 (L2 rechazada por `weak_grounding` y `repetition`; L3 por `prerequisite_not_accepted` y `repetition`), 0 errores de parseo y 0 reintentos por formato. Costo real US$0.03416; el repo estimó 0.03994, por la misma razón. Esas dos corridas no alcanzan para una tasa. La tabla está en el README. judge-vs-human agreement: not measured yet.

Una instrucción metida adentro de un documento del corpus no alcanza para publicar ni para sacar la cita. Hay un fake que obedece esa instrucción a propósito (`EMBEDDED-INSTRUCTION`). El gate igual se pone rojo y no publica. Eso está en la regresión forzada.

El panel de 48 ítems sigue siendo un computation demo de la fórmula. El acuerdo con una persona es otra cosa: `python -m hemp review export --n 30` escribe `labels/human_labels.template.csv` con `human_verdict` vacío. Hasta que lo completes a mano, judge-vs-human agreement: not measured yet.

Si te preguntan "¿y en producción?", la respuesta honesta está en [ADAPT_TO_A_REAL_CLIENT.md](ADAPT_TO_A_REAL_CLIENT.md): primero discovery, después sombra, después el gate. Este repo es el ensayo con datos ficticios.
