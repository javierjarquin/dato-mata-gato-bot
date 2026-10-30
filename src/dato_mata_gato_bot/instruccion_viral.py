"""Fórmula del TEMA VIRAL: lo que se dice / lo que está en papel / lo que nadie
ha contestado (15/10/2026).

Nace del POC del agua de Yucatán y las empresas israelíes: un video de Vicky
Wolff que TikTok bajó hizo que la península hablara del agua en cuatro días. El
canal no puede afirmar el rumor (no hay documento) ni desmentirlo (tampoco lo
hay): lo que sí puede es enseñar los tres niveles y decir en voz alta dónde está
el hueco. "Dato Mata Gato" es el nombre para eso: el dato mata al rumor.

Lo que el POC enseñó y aquí se corrige (Javier, 15/10/2026): "la primera mitad
del video estuvo buena pero la otra no, no hay rumores, afectación, la fama en
este caso del país". Los tres niveles iban en SECUENCIA, así que el rumor
desaparecía al segundo veinte y los datos quedaban huérfanos. En esta fórmula
los niveles van INTERCALADOS: cada dato contesta una pieza del rumor, y el rumor
vuelve a mitad del video (p05). Y entra la pieza 8, POR QUÉ SE CREE: el
antecedente verificable que hace creíble el rumor, que es lo que le faltaba.

Lo que falló en el video de MINISO (Javier, 16/10/2026): "el título dice de un
caso de Miniso, pero realmente no se da un contexto claro de quién y qué pasó".
El nombre SÍ estaba en pantalla -la captura del titular de Infobae- y la voz
nunca lo dijo: la narración hablaba de "la tienda" y de "el gerente", nunca contó
qué había pasado, y en p05 preguntaba "¿y la amenaza?" sin haber contado jamás
cuál amenaza. De ahí los dos cambios de ese día: NOMBRES (todo se dice con su
nombre, y los menores son la única excepción) y EL CHECK FINAL, que relee el
guion contra sus fuentes antes de entregarlo.

Reglas que NO se negocian, por el tipo de tema que es:
  - El nivel 1 va SIEMPRE en voz atribuida ("se está diciendo que…", "los
    colectivos lanzaron la campaña…"), nunca en voz del canal. Atribuir no es
    callar: se dice el nombre de quien está señalado y el de quien lo señaló.
  - De quien preguntó no se dice que se equivoca: se dice lo que hizo.
  - Si no hay documento para afirmar NI para desmentir, se dice eso, no se
    elige un lado. Decir "es falso" sin prueba es el mismo salto que decir
    "es cierto".
  - Nada de notas animadas en los planos del rumor (ver `plus.sin_nota_animada`):
    animar el cuerpo del artículo que afirma el rumor ES publicar el rumor. Del
    nivel 1 se enseña el TITULAR que lo reporta, nunca el cuerpo que lo afirma.
"""

import re

# Tipos de tema viral, por si se pide el lote sin nombre.
TEMAS = [
    ("rumor", "Un rumor que está corriendo",
     "Algo que se está diciendo en redes y que mucha gente ya vio, sobre quién se queda con "
     "algo que es de todos: el agua, la tierra, la luz, un servicio, un apoyo. Tiene que haber "
     "DEBAJO un dato propio verificable sobre ese mismo tema, con responsable identificado."),
    ("borrado", "Lo que una plataforma bajó",
     "Un video, una publicación o una cuenta que una plataforma dio de baja y de lo que se está "
     "hablando por eso mismo. Que lo bajaran es un hecho verificable y es el gancho; lo que "
     "decía va atribuido, nunca afirmado."),
    ("privatizan", "\"Van a privatizar\"",
     "Una versión que dice que van a privatizar o entregar algo (el agua, la luz, el campo, una "
     "playa, un padrón) cuando hay una ley, un decreto o un contrato que se puede leer. El "
     "trasfondo es lo que el papel dice de verdad, a favor o en contra de la versión."),
]

INSTRUCCION = r"""
Vas a escribir <<N>> guiones de video corto (45 a 75 segundos) para el canal Dato Mata Gato,
con la fórmula del TEMA VIRAL.

EL TEMA
<<TEMA>>

DE QUÉ VA ESTA FÓRMULA
El canal entra a un tema del que YA se está hablando y hace lo único que nadie está haciendo:
separar tres cosas que en redes van revueltas.
  NIVEL 1 · LO QUE SE DICE        la versión que circula, atribuida a quién la dice y dónde.
  NIVEL 2 · LO QUE ESTÁ EN PAPEL  lo que sí está documentado, con su fuente abierta y leída.
  NIVEL 3 · LO QUE NADIE HA CONTESTADO  el hueco entre las dos, dicho en voz alta.
El canal NO afirma el rumor y NO lo desmiente: casi nunca hay documento para ninguna de las
dos cosas, y elegir un lado sin papel es justo lo que hace que la gente no le crea a nadie.
Y ANTES DE EMPEZAR, LA PRUEBA DEL PAPEL (17/10/2026): esta fórmula es para disputas sobre un
HECHO. Pregúntate si existe un papel que, si apareciera, cerraría la discusión. Si lo que
detonó el tema es una OPINIÓN -un insulto, una burla, un juicio sobre un grupo-, no hay tal
papel y el tema NO es de esta fórmula: es de la de LA POLÉMICA, donde el nivel 2 es la
respuesta de los afectados. Dilo en el resumen y no lo fuerces aquí.

LOS NIVELES VAN INTERCALADOS, NO EN FILA (lo más importante de esta fórmula)
El error que hundió el primer video: poner el rumor al principio y treinta segundos de datos
después. A la mitad el espectador ya no sabe de qué le estás hablando y se va.
Cada dato del nivel 2 CONTESTA una pieza del rumor, y se dice contestándola:
  mal:  "El video decía que X. (…) Semarnat contó quinientas siete granjas."
  bien: "¿Se llevan el agua? El que la está ensuciando tiene nombre: quinientas siete granjas."
Y en p05 el rumor REGRESA: lo que de esa versión sí resultó cierto, o la parte que todavía
nadie puede negar. El video nunca deja de ser sobre el tema por el que la gente llegó.

LAS PIEZAS (las ocho, y sin una no hay video)
  1. TE AFECTA: le pasa a casi cualquiera. Y NO se dice una sola vez: se nombra en el gancho,
     vuelve a la mitad (p04) y vuelve al final. Es lo que sostiene el video cuando el rumor
     ya se contó.
  2. ESTÁ PASANDO AHORITA: el tema está vivo esta semana, con fecha. En un tema viral la
     fecha también es del fenómeno: cuándo se viralizó, cuándo lo bajaron, cuándo lo cubrió
     la prensa.
  3. ALGO NO CUADRA, variante 3b NADIE HA CONTESTADO: la contradicción es entre lo que se
     dice y lo que está en papel, y el hueco no lo ha llenado nadie. Esa es la brecha de
     curiosidad y se queda abierta de verdad: no la cierres inventando una respuesta.
  4. CORAJE: contra la OPACIDAD y contra la omisión documentada, nunca contra un país, una
     religión, un pueblo ni contra quien preguntó. El coraje sale de un hecho: un documento
     que no se exhibió, un permiso que no se revisó, una respuesta que no llegó.
  5. SE PUEDE MOSTRAR: el documento, el acta, el expediente, el lugar. En esta fórmula la
     evidencia es media pieza del video: sin documento en pantalla, no se graba.
  6. HACE HABLAR: en un tema viral esto sobra, pero la pregunta cambia de tipo. No es "¿a ti
     ya te cobraron?", es "¿tú qué versión escuchaste?". Todo el mundo tiene una versión.
  7. VALOR PRÁCTICO: el nombre y la fecha del documento que cualquiera puede ir a buscar, o
     dónde se consulta. Es lo que convierte al espectador en alguien que puede verificar.
  9. LA PREGUNTA QUE QUEDA (15/10/2026, Javier: "eso hay que cuestionarlo, lanzar preguntas que
     la gente responde y opine, y dar suposiciones: ¿acaso quieren ocultar algo?"). El nivel 3
     no se cierra con un punto final -- "nadie lo ha enseñado" hace que el que ve asienta y se
     vaya. Se cierra ABRIENDO: dos o tres explicaciones posibles de por qué falta lo que falta,
     dichas EN PREGUNTA, y que el canal NO elige. Escríbelas en "_schema.preguntas_abiertas".
     Tres reglas para que esto sea periodismo y no un señalamiento:
       - Van en pregunta, nunca en afirmación. "¿O no quieren que lo veas?" sí; "lo esconden
         porque hay corrupción" no: eso afirma un delito sin documento y el canal no lo tiene.
       - SIEMPRE entre ellas una explicación inocente ("¿se perdió?", "¿nunca existió?",
         "¿nadie lo pidió bien?"). No es por suavizar: es lo que hace que la gente DISCUTA en
         los comentarios en vez de solo asentir, y además es honesto, porque de verdad no
         sabemos cuál es.
       - Salen del hueco que ya probaste en el nivel 3. Si el nivel 3 es que un documento no
         está público, las preguntas son sobre ESE documento, no sobre lo que se te ocurra.
     La pregunta de p08 remata lo mismo: "¿Tú por qué crees que no lo enseñan?" pide la
     opinión sobre el hueco, que es lo que más comentarios da en este formato.
  8. POR QUÉ SE CREE (nueva, 15/10/2026, y es la que faltaba): el ANTECEDENTE VERIFICABLE que
     hace creíble el rumor. La gente no se lo cree por tonta: se lo cree porque algo parecido
     ya pasó, o porque quien está señalado tiene un historial que se puede documentar. Aquí va
     ese historial, con su fuente: el convenio que sí existe, la concesión que no se revirtió
     ni votando, la campaña internacional que sí hay contra esa empresa, la vez que el mismo
     gobierno no enseñó un papel. Se dice como lo que es -antecedente, no prueba- y por eso
     NO valida el rumor: lo explica. Es lo que hace que el video respete a quien lo ve en vez
     de corregirlo. En "_schema.condiciones.8_por_que_se_cree" escribe el antecedente y su
     fuente.

EL CANDADO, QUE SON DOS COSAS (y la segunda es la que más se falla)
  a) El NIVEL 2 tiene que valer el video SOLO. Si le quitas el rumor y ya no hay nada que
     contar, es un video SOBRE el rumor y lo estás amplificando.
  b) Y tiene que ser SOBRE LO MISMO QUE EL RUMOR. Contesta la pregunta que la gente se está
     haciendo, no una parecida.
La (b) se salta sola y arruina el video. Pasó el 15/10/2026 con el hombre que fingía una
discapacidad en un crucero de Cancún: el guion arrancó con ese video y se fue a las multas
por invadir cajones de estacionamiento. Dos temas que solo comparten una palabra. Javier:
"empezaste hablando del video, pero nunca profundizaste, te desviaste del tema". Si la
gente pregunta "¿este señor finge?", el nivel 2 va de ESO -- cuántos tarjetones se
cancelaron, si hubo carpeta, qué pasó con casos iguales -- no del reglamento de
estacionamientos porque es el documento que encontraste primero.
Antes de escribir, di en una línea la PREGUNTA que la gente se está haciendo. Todos los
planos del nivel 2 contestan esa pregunta. Si tu documento contesta otra, no es tu documento:
sigue buscando, o cambia de tema.
En "_schema.vale_sin_el_rumor" escribe por qué se sostiene sin el rumor, y en
"_schema.pregunta_del_publico" la pregunta. Si no las puedes escribir, el tema no va.

LA PRUEBA DEL QUE LLEGA SIN SABER (27/10/2026, Javier: "después del gancho ya no entendí qué
pasó... supe que una tiktoker opinó, pero no sobre qué")
Quien ve el video NO vio la polémica. Al terminar p01 tiene que poder contar QUÉ PASÓ en una
frase: quién (con su rol: "una creadora de contenido"), a quién, dónde (en qué red, en qué
publicación) y qué dijo o qué se dice, COMPLETO. Pasó con el video de las madres buscadoras: la
frase era "vale más mi gato que sus desaparecidos" y la narración solo dijo "vale más mi gato";
sin el "que sus desaparecidos" nadie entiende de qué va, y el video saltó a los datos.
  - La frase (o lo que se dice) va COMPLETA al menos una vez en p00-p01. Recortarla para el
    gancho está bien; recortarla en todo el video, no.
  - Escribe esa frase de qué pasó en "_schema.que_paso", y que la narración de p00 a p02 la
    diga (con tus palabras, pero con todas sus partes).
  - Los datos van DESPUÉS de que se entendió qué pasó, nunca antes.

MUERTES Y LO QUE SE DICE DE ELLAS (27/10/2026, caso Komanche)
Una muerte SÍ es tema si alrededor hay una versión que circula ("dicen que se quitó la vida",
"dicen que lo orillaron") o una frase que ofendió a un grupo. Y se cuenta así:
  - Lo que la gente dice de la causa va ATRIBUIDO ("en redes dicen que…") y SIEMPRE con que NO
    está confirmado, y quién lo confirmaría (la fiscalía, el dictamen). El canal nunca afirma la
    causa por su cuenta.
  - Palabras suaves en la narración, en el texto en pantalla, el título y los hashtags: "se quitó
    la vida", "lo que dicen de su muerte", "decidió irse". Nunca la palabra "suicidio" ni sus
    variantes, y sin describir cómo pasó.

NOMBRES (16/10/2026, decisión de Javier: "que sea claro y diga nombres de manera
transparente"). Todo lo que tiene nombre se dice CON SU NOMBRE Y EN LA NARRACIÓN:
  - la EMPRESA, la marca o el establecimiento señalado: "una tienda MINISO del Centro
    Histórico", no "una tienda"; "un restaurante del Zócalo llamado X", no "un restaurante";
  - la INSTITUCIÓN y el CARGO de quien respondió o de quien debía responder ("el COPRED", "la
    alcaldía Cuauhtémoc", "el fiscal Fulano de Tal"), nunca "las autoridades";
  - QUIEN PUBLICÓ el caso, con su cuenta y su crédito ("el creador Max Cintio, en TikTok");
  - QUIEN RESPONDIÓ y qué dijo, citado;
  - el DOCUMENTO con su nombre y su fecha.
UNA sola excepción, y es de ley: MENORES DE EDAD, víctimas o señalados, no se nombran (Ley
General de los Derechos de Niñas, Niños y Adolescentes protege su identidad). Se dice su edad
y su rol. Fuera de esa, NO hay nombre que se calle.
Una persona señalada y sin sentencia SÍ se nombra. Lo que cambia no es el nombre: es el
verbo. Se dice quién la acusa y de qué ("el creador lo acusó de insultarlo", "la empresa dijo
que lo desvinculó"), no se da el hecho por probado. Eso es reportar; callar el nombre no
protege a nadie y deja el video sin caso.
Y el nombre se DICE: enseñarlo en una captura NO cuenta. En el video de MINISO el nombre
estaba en el titular que salía en pantalla y la voz nunca lo pronunció, así que quien lo vio
se quedó sin saber de quién le estaban hablando.
Escribe en "_schema.senalados" la lista de los nombres que el guion dice -empresa,
institución, cuenta, funcionario-. Cada uno tiene que aparecer, escrito igual, en alguna
narración; la revisión automática lo comprueba.

LO QUE NO SE HACE
  - No se afirma lo que no tiene documento, ni se niega lo que no tiene documento. Se dice
    "no está público", que es lo que sí se puede probar.
  - No se señala a un país, una religión ni un pueblo como culpable: se señala a quien firmó,
    a quien no exhibió, a quien no revisó. Con nombre y con cargo. Esto NO es permiso para
    callar un nombre: una empresa, una dependencia o una persona con cargo se nombran siempre
    (ver NOMBRES). Lo que no se hace es convertir a un grupo entero en el responsable.
  - No se ridiculiza ni se corrige a quien hizo la pregunta. Si le bajaron el video, eso se
    cuenta como lo que es: le bajaron el video.
  - Menores de edad, nunca: ni víctimas ni señalados. Es la única excepción de NOMBRES.
  - Lo que se VE en el material se describe tal cual y es el contenido del video ("se quita
    las muletas y camina", "el recibo dice veinticinco pesos"). Eso es un hecho observable y
    no necesita que una autoridad lo confirme primero. Lo que no se ve -- la intención, el
    delito, el diagnóstico -- se dice como lo que es: lo que no se sabe. La diferencia no es
    de tono, es de qué se puede probar con el material en la mano.

VERIFICACIÓN (en esta fórmula es el producto, no un trámite)
1. Busca y ABRE las notas (con el comando buscar; WebFetch solo si no lo tienes o no abre). Cada cifra, fecha y nombre sale de algo que leíste.
   Los resúmenes del buscador inventan cifras: no los uses.
2. Busca la FUENTE PRIMARIA del nivel 2 y del 3: el decreto, el punto de acuerdo, la
   sentencia, el padrón, el informe. Un artículo de opinión no sostiene el nivel 2; sirve
   para saber qué buscar. Si el documento está en un PDF oficial, ése es el que va.
3. Lo que dice UNA sola fuente va atribuido en la narración ("según PorEsto…"). Las cifras de
   organizaciones civiles, activistas o empresas van SIEMPRE con su nombre.
4. Si una cifra junta dos fuentes de años distintos, se dicen las dos con su año. Nunca se
   presentan como una sola cifra de hoy.
5. En "_schema.fuentes" cada URL con lo que dice. En "_schema.restriccion_etica", lo que
   decidiste NO usar y por qué: ahí va, explícito, lo que no se puede afirmar ni negar.
6. En "_schema.tres_niveles" escribe los tres, y en "no_se_sabe" incluye QUÉ SE PIDIÓ para
   saberlo (la solicitud de transparencia, la llamada, el registro consultado). El hueco se
   dice habiendo tocado la puerta, no de lejos.
7. No repitas ninguno de los que YA ESTÁN HECHOS (lista al final).

EL CHECK FINAL, ANTES DE ENTREGAR (16/10/2026, Javier: "verifica si la información es
correcta y si la historia es la misma... me dio la impresión de que desviabas el tema")
Con el guion.json ya escrito, haz UNA pasada más. No se salta, y no es releer por encima:
1. DATO POR DATO. Lee cada cifra, cada fecha y cada nombre de la narración y di de cuál de
   tus "_schema.fuentes" sale. Si al releer no encuentras de dónde salió, es que no estaba:
   bórralo o cámbialo por el que sí leíste. No lo rellenes de memoria, que es justo donde se
   inventan las cifras.
2. LA MISMA HISTORIA. Lee los nueve planos de corrido, como quien ve el video sin haber
   visto el viral, y contesta tres cosas:
     - ¿Se entiende QUIÉN es quién y QUÉ PASÓ, con nombres, antes del segundo quince?
     - Los planos del nivel 2 (p03 a p07), ¿contestan "_schema.pregunta_del_publico", o
       contestan otra parecida? (Es el desvío del 15/10: arrancó con el video de un hombre
       fingiendo discapacidad y terminó en multas de estacionamiento.)
     - ¿El video cierra hablando del mismo tema con el que arrancó?
   Si una sale que no, el guion se desvió. Corrígelo antes de entregarlo; no lo entregues
   explicando el desvío.
3. Escribe el resultado en "_schema.verificacion_final":
     {"datos": ["<lo que dice la narración> -- <clave de _schema.fuentes>", ...],
      "misma_historia": "de qué arranca y qué contestan p03 a p07, en una línea",
      "corregido": "qué cambiaste en esta pasada, o \"nada\""}
   En "datos" van TODAS las cifras y fechas que se dicen, mínimo tres renglones, y cada
   renglón nombra la clave de "_schema.fuentes" de la que sale.
4. Después de corregir, vuelve a correr la revisión automática del slug.

EL NIVEL 1 SE CUENTA, NO SE DA POR SABIDO (16/10/2026)
Quien ve el video NO vio el viral. Antes del segundo quince la narración ya tiene que haber
dicho QUÉ SE DICE QUE PASÓ, con nombres y atribuido a quien lo contó:
  "El creador Max Cintio contó que el gerente de una tienda MINISO lo insultó y lo siguió
   por los pasillos."
Eso es atribuir, no afirmar: el sujeto de la frase es quien lo contó. Se reparte entre p00,
p01 y p02, y si al terminar p02 todavía no se entiende quién es quién y qué pasó, el guion
no va. Es exactamente lo que hundió el video de MINISO.

ESTRUCTURA (9 planos, ids p00 a p08) -- los niveles intercalados
- p00 "gancho_hablado": MÁXIMO 12 PALABRAS. El HECHO del fenómeno, CON EL NOMBRE de quien
  está señalado: que lo bajaron, que millones lo vieron, que una campaña arrancó. NINGÚN año
  ni fecha dichos.
  Bien: "Le bajaron a Vicky Wolff el video que preguntaba quién se queda con el agua."
  Bien: "Dos millones y medio vieron a un gerente de MINISO correr a un cliente."
  Mal: "Israel va a controlar el agua de Yucatán." (eso AFIRMA el rumor)
  Nombrar a quien está señalado NO es afirmar el rumor: lo que afirma es el verbo, no el
  nombre. "Dos millones vieron el video de X" es un hecho; "X lo hizo" es una afirmación.
- p01 "hook_tercera_persona": "Te imaginas a quien…" + A QUIÉN LE TOCA (pieza 1) + QUÉ SE
  DICE QUE PASÓ, atribuido y COMPLETO (quién lo dice, dónde, de quién y qué exactamente), + la
  primera PREGUNTA directa a quien ve, antes del segundo diez: "¿Tú lo viste?", "¿Qué
  escuchaste tú?". Puede ser de tres frases. Es la prueba del que llega sin saber.
- p02 "contexto": POR QUÉ SE CREE (pieza 8). El antecedente verificable, atribuido. Aquí es
  donde el video se gana a quien llegó creyendo el rumor.
- p03 "el_hecho": el nivel 2 CONTESTANDO al rumor, con la cifra más fuerte y su fuente. Va la
  segunda PREGUNTA ("¿Tú lo sabías?").
- p04 "bucle_abierto": la AFECTACIÓN real, con cifra: a quién le está pegando ya y cuánto.
  La pieza 1 vuelve aquí.
- p05 "el_desenlace": EL RUMOR REGRESA. Qué parte de lo que se dice sí está documentada, y
  qué parte sigue sin poderse probar ni descartar. Dicho así, con esas palabras.
- p06 "contexto": el trasfondo: lo que YA pasó antes en este país con algo igual, con fechas y
  nombres. Es la memoria que explica la desconfianza. Corto (una o dos frases) y que termine
  empujando a p07: la historia que se alarga al final es donde la gente se va.
- p07 "cierre_bucle": LO QUE NADIE HA CONTESTADO, y NO se cierra: se pregunta. Son dos cosas
  pegadas, el hecho y la pregunta que deja:
     el hecho verificado   "Un senador lo pidió en dos mil dieciséis y sigue sin aparecer."
     la pregunta que queda "¿Se perdió? ¿O no quieren que lo veas?"
  Sin moraleja, y sin responderla: la respuesta la ponen en los comentarios.
- p08 "identidad_cierre": "Aquí el dato mata al gato. ¿[pregunta sobre SU caso]? Cuéntamelo en
  los comentarios." Su visual: {"tipo": "grafico_movimiento", "descripcion": "Cartel de cierre
  del canal.", "prompt_ia": "", "busqueda_medios": ""}.
Reglas de la narración: español de México, de tú. Ninguna frase pasa de 20 palabras. Números y
años en palabras. Máximo DOS nombres propios por frase. Nada que empiece con "Tl". En los
primeros tres planos, el lugar exacto. Total: 120 a 190 palabras.

EVIDENCIA (sin imágenes de IA; y aquí hay que ENSEÑAR el fenómeno, no contarlo)
"evidencia" es una lista; cada plano (p00 a p07) lleva en visual.evidencia 1 a 3 ids. Mínimo
TRES piezas reales más 2 o 3 fichas, y de esas, OBLIGATORIAS:
  - AL MENOS UNA de tipo "documento": sin fuente primaria en pantalla el video es una opinión.
  - AL MENOS UNA de redes ("video_red" o "red_social"): el tema nació en redes y el canal
    tiene que ENSEÑARLO. Contar un video viral sin mostrarlo nunca es lo que hacía que estos
    videos salieran planos (Javier, 15/10/2026).
Tipos:
- {"id": "r1", "tipo": "video_red", "url": "https://www.tiktok.com/@cuenta/video/123",
   "fuente": "@cuenta · TikTok", "desde_seg": 3, "segundos": 6}: el clip en sí, recortado.
   Es la prueba en movimiento. Sirve TikTok, Instagram, Facebook, X, YouTube y Threads.
   "desde_seg" es dónde empieza lo que importa. Va con crédito al autor, siempre.
   Si el video ya no se puede bajar (lo borraron, es privado), se arma solo la captura de la
   publicación: no se cae el tema.
- {"id": "r2", "tipo": "red_social", "url": "...", "fuente": "@cuenta · TikTok"}: la
   publicación capturada con sus números (vistas, likes, comentarios). Es lo que PRUEBA el
   tamaño del fenómeno, que es lo que justifica el tema.
- {"id": "e1", "tipo": "prensa", "url": "...", "fuente": "Medio, DD/MM/AAAA"}: se captura SOLO
  el titular, así que el titular tiene que nombrar el caso. Para PorEsto usa la .amp.html.
- {"id": "e2", "tipo": "documento", "url": "...", "fuente": "..."}: la fuente primaria. Para un
  PDF agrega "pagina": n y, si el dato está a media página, "desde": 0.6, "fraccion": 0.85.
  Si el servidor oficial tiene el certificado roto (pasa con sil.gobernacion.gob.mx), avísalo
  en el resumen: se arma a mano con tools/evidencia_pdf_local.py.
- {"id": "e3", "tipo": "lugar" | "persona", "wikimedia": "File:Nombre exacto.jpg"}: el nombre
  EXACTO de un archivo que verificaste. NO uses "buscar_wikimedia".
- {"id": "f1", "tipo": "ficha", "titulo": "...", "renglones": ["...", "..."], "fuente": "..."}.
Cada plano de p00 a p07 lleva "motion": "calm" en su visual.

EL "visual" DE CADA PLANO (si te equivocas aquí, el video no se genera)
"visual.tipo" solo puede ser uno de estos SIETE, escrito exacto:
  imagen_ia · video_stock · animacion_3d · mapa_animado · grafico_movimiento ·
  cartel_texto · archivo_historico
En esta fórmula, de p00 a p07 va SIEMPRE "archivo_historico" (es el que usa la
evidencia real). NO existe el tipo "archivo": eso tira el video entero.
Solo p08 lleva "grafico_movimiento", que es el cartel de cierre del canal.
Así se ve un plano completo:
{"id": "p03", "seccion": "el_hecho",
 "narracion": "...",
 "visual": {"tipo": "archivo_historico", "evidencia": ["f1", "e3"],
            "prompt_ia": "", "busqueda_medios": "", "motion": "calm"},
 "texto_en_pantalla": "507 GRANJAS"}

FORMATO DE CADA GUION
Escríbelo en C:\Android_in\<slug>\guion.json, con slug "guion-viral-" + palabras cortas del
tema (minúsculas y guiones). Además de lo de siempre ("titulo", "gancho", "claves",
"hashtags", "evidencia", "planos"), el "_schema" lleva:
  "tres_niveles": {"se_dice": "...", "esta_documentado": "...", "no_se_sabe": "...",
                   "pendiente_de_pedir": "..."},
  "vale_sin_el_rumor": "...",
  "senalados": ["MINISO", "Max Cintio", "COPRED"],   <- los nombres que DICE la narración
  "verificacion_final": {"datos": ["... -- clave_de_fuente", "..."],
                         "misma_historia": "...", "corregido": "..."},
  "hallado_en": "la PLATAFORMA, la cuenta y los números de la publicación donde encontraste el
     tema ('TikTok, @cuenta, 1.2 M de vistas y 8 mil comentarios, 12/10/2026'). El tema se
     busca en redes, no en los portales",
  "impacto": "de dónde sale que esto se está hablando (vistas, que lo bajaron, qué medios)",
  "condiciones": {"1_te_afecta": "...", "2_esta_pasando_ahorita": "... (con fecha)",
                  "3_algo_no_cuadra": "...", "4_coraje": "...", "5_se_puede_grabar": "...",
                  "6_hace_hablar": "...", "7_valor_practico": "...",
                  "8_por_que_se_cree": "el antecedente verificable y su fuente"},
  "fuentes": {...}, "restriccion_etica": "...", "vigencia": "conversacion"
Y en "plus", además de lo de siempre:
  "sin_nota_animada": ["p00", "p01", "p02"]  <- los planos del nivel 1. OBLIGATORIO, y es SOLO
     contra animar el cuerpo del ARTÍCULO de prensa que afirma el rumor (el render bajaba a su
     párrafo y lo resaltaba, o sea publicaba la acusación como si fuera del canal). NO afecta a
     las piezas de redes: la publicación original sí se enseña, con su crédito, porque es la
     prueba de lo que se está diciendo.
  "contradiccion": los dos bloques, en el plano donde la voz lo cuenta:
     {"plano": "p03", "arriba": {"titulo": "LO QUE SE DICE", "renglones": ["...", "..."]},
      "abajo": {"titulo": "LO QUE ESTÁ EN PAPEL", "renglones": ["...", "..."]},
      "abajo_en": "<una palabra de la narración de ESE plano>", "resaltar": "<un renglón de
      abajo, igual>", "fuente": "Medio o institución, DD/MM/AAAA"}
     2 o 3 renglones por bloque, máximo 36 letras cada uno.
  "mapa" SIEMPRE: {"plano": "p02", "consulta": "Palacio Legislativo de San Lázaro, Ciudad de
     México", "etiqueta": "SAN LÁZARO · CDMX"}. "plano": donde la voz nombra el lugar;
     "consulta": como se buscaría en un mapa (calle, colonia o edificio, y la ciudad), NUNCA
     vacía; "etiqueta": máximo 32 letras.
  "contador" y "archivo" como siempre, si aplican.
  "portada" SIEMPRE: {"texto": "3 a 5 PALABRAS EN MAYÚSCULAS", "resalta": "1 o 2 de ellas"}
     (portada del perfil; el hueco, no el rumor afirmado: "LA RESOLUCIÓN NO APARECE").

AL TERMINAR responde SOLO este bloque JSON:
{"guiones": [{"slug": "...", "titulo": "...", "resumen_hechos": "2 líneas con los hechos y sus
fuentes", "nivel_3": "en una línea, qué es lo que nadie ha contestado"}]}
""".strip()


# Cuando no se da tema: Claude busca de qué se está hablando antes de escribir.
BUSCAR_TENDENCIAS = r"""
PRIMERO, DE QUÉ SE ESTÁ HABLANDO (antes de escribir nada)
No te dieron tema: búscalo. Encuentra <<CUANTOS>> temas que ESTA SEMANA estén dando
conversación en redes en México y que sirvan para esta fórmula.

EL TEMA SALE DE LA PLATAFORMA, NO DE LA PRENSA (16/10/2026, Javier: "esos temas virales los
tienes que buscar en redes sociales... el tema de Vicky Wolff salió porque era un tema popular
en la plataforma"). Esto manda sobre todo lo demás de este apartado.
Empieza SIEMPRE buscando DENTRO de TikTok, Facebook, Instagram, X y YouTube: qué publicación
está juntando vistas y comentarios en México ahorita. El tema lo elige lo que la gente está
viendo, no lo que un portal decidió titular como "se hace viral".
La prensa entra DESPUÉS, para verificar y para el nivel 2. Nunca para descubrir el tema. Si lo
encontraste en un portal y no en una plataforma, NO es un tema viral: es una noticia, y para
eso está la fórmula de cercanía. Un tema que sólo existe en notas no pasa.
Escribe en "_schema.hallado_en" dónde lo encontraste, con la plataforma, la cuenta y los
números de la publicación: "TikTok, @vickywolff, 1.2 M de vistas y 8 mil comentarios,
12/10/2026". Si no lo puedes escribir, no lo buscaste en redes: regresa a buscarlo.
Así nació el POC del agua de Yucatán: de un video de Vicky Wolff que TikTok bajó y del que la
península estuvo hablando cuatro días. No de una nota.

Dónde mirar, en este orden (junta las búsquedas de 3 o 4 en una sola respuesta):
  1. Las propias plataformas, que es donde se descubre: busca el tema EN TikTok, Facebook,
     Instagram, X y YouTube y MIRA LOS NÚMEROS de las publicaciones (vistas, comentarios,
     compartidos). Ahí se ve el tamaño real y de ahí sale el tema.
  2. Publicaciones o cuentas que una plataforma haya dado de baja y de las que se esté
     hablando por eso mismo.
  3. Campañas o convocatorias de colectivos con lema propio, buscadas por su lema en redes.
  4. Sólo para CONFIRMAR lo que ya encontraste arriba: lo que la prensa publicó del tema.

EL UMBRAL (15/10/2026): no basta con que exista la nota.
Una nota replicada el mismo día en tres portales locales NO es un fenómeno: eso fue el error
del video del hombre que fingía discapacidad, que Javier describió como "un tema que no está
dando de qué hablar". Pide por lo menos DOS de estas señales, y escríbelas en
"_schema.impacto" con su número y su fecha:
  - una publicación con MUCHAS vistas o comentarios (dilo con la cifra y de qué cuenta);
  - que una plataforma lo haya bajado o restringido;
  - que lo recojan medios de FUERA del estado, o de otro país;
  - varios días seguidos de conversación, no un solo día;
  - respuesta de una autoridad, una empresa o la persona señalada;
  - gente contando su propio caso en los comentarios (es la mejor señal de todas).
Si solo tienes "lo publicaron tres portales el mismo día", el tema NO va.

LA PRUEBA DEL PAPEL (17/10/2026): ESTA FÓRMULA ES PARA DISPUTAS SOBRE UN HECHO
Antes de quedarte con un tema, contesta una pregunta:
  ¿EXISTE UN PAPEL QUE, SI APARECIERA, CERRARÍA LA DISCUSIÓN?
Si SÍ -> es tema de esta fórmula. El agua de Yucatán lo era: el contrato de Conagua con
Mekorot existe o no existe, y un senador pidió exhibirlo en 2016.
Si NO, porque lo que detonó todo es una OPINIÓN -> NO es de esta fórmula. Va en la de LA
POLÉMICA (`instruccion_polemica`), donde el nivel 2 es la respuesta de los afectados y no un
documento. Dilo y cambia de tema; no lo fuerces aquí.
Pasó el 16/10/2026 con el Conalep: un podcast llamó "bandidazos" a los alumnos y el guion acabó
preguntando "¿dónde está el informe de empleabilidad?" a gente que llegó enojada porque
ofendieron a su escuela. "Son bandidazos" no es una versión de los hechos: es un juicio, y
ningún documento decide si fue justo. Señal de que te está pasando: tu nivel 3 queda en "nadie
puede probarlo ni descartarlo" sobre algo que NADIE iba a poder probar nunca. En el agua esa
frase es un hallazgo (el papel podría existir y no está); en un insulto es una obviedad.

Un tema sirve para esta fórmula solo si cumple LAS TRES:
  a) se está hablando de verdad y lo pruebas con el umbral de arriba;
  b) debajo hay un DATO PROPIO verificable QUE CONTESTA LA MISMA PREGUNTA, con responsable
     identificado y de preferencia con fuente primaria (decreto, contrato, padrón, informe);
  c) pasa el candado completo, (a) y (b) del apartado del candado.
Si un tema no tiene (b), NO lo tomes aunque esté muy viral: ahí el canal solo repetiría el
rumor. Busca otro.

NO tomes: rumores sobre personas privadas, chismes de espectáculos, bulos de salud que
convenga repetir aunque sea para negarlos, ni nada donde el único contenido posible sea la
acusación. Si un tema señala a un país, una religión o un pueblo, el video va contra quien
firmó o quien no exhibió el papel, nunca contra el grupo.

Antes de escribir, dime en una línea por tema cuál elegiste y qué dato propio tiene debajo.
Luego escribe los <<CUANTOS>> guiones.
""".strip()


def instruccion(n: int, tema: str | None, ya_hechos: str, ligera: bool = False) -> str:
    """El prompt del lote. Sin `tema`, Claude busca primero las tendencias."""
    from dato_mata_gato_bot import instruccion_cercania

    if tema:
        descripcion = (f"{tema}. Investiga QUÉ se está diciendo exactamente sobre esto, quién lo "
                       "dice, desde cuándo y qué documentos hay debajo.")
    else:
        descripcion = BUSCAR_TENDENCIAS.replace("<<CUANTOS>>", str(n))
    texto = INSTRUCCION.replace("<<N>>", str(n)).replace("<<TEMA>>", descripcion)
    if ligera:
        texto = texto.replace("\nAL TERMINAR responde",
                              instruccion_cercania.COMO_TRABAJAR + "\nAL TERMINAR responde")
    return texto + instruccion_cercania.PUBLICAR + "\n\nYA ESTÁN HECHOS -- no repitas ninguno: " + ya_hechos


# Las ocho piezas, para la revisión sin Claude.
CONDICIONES = ("1_te_afecta", "2_esta_pasando_ahorita", "3_algo_no_cuadra", "4_coraje",
               "5_se_puede_grabar", "6_hace_hablar", "7_valor_practico", "8_por_que_se_cree")
NIVELES = ("se_dice", "esta_documentado", "no_se_sabe")
PLANOS_DEL_RUMOR = ("p00", "p01", "p02")
# Dónde se descubre un tema viral: en la plataforma, no en un portal.
PLATAFORMAS = ("tiktok", "facebook", "instagram", "youtube", "threads", " x ", "twitter")
# Los planos del nivel 2: los que tienen que contestar la pregunta del público.
PLANOS_DEL_DATO = ("p03", "p04", "p05", "p06", "p07")
DE_REDES = {"video_red", "red_social"}
_MIN_DATOS = 3
# Palabras sin carga: no sirven para saber si el nivel 2 habla del mismo tema.
_VACIAS = {"que", "para", "como", "cuando", "donde", "porque", "pero", "esto", "esta",
           "este", "esos", "esas", "cual", "cuales", "quien", "quienes", "sobre", "ellos",
           "tiene", "tienen", "hace", "hacen", "ahora", "todo", "toda", "todos", "nada",
           "mucho", "mucha", "gente", "dice", "dicen", "pasa", "pasan", "estan", "despues",
           "entonces", "tambien", "algun", "alguna", "otros", "otras", "siempre", "nunca"}


def _sin_acentos(t: str) -> str:
    from dato_mata_gato_bot import revision_guion

    return revision_guion._sin_acentos(t)


def _narrado(guion: dict, ids: tuple[str, ...] | None = None) -> str:
    """Todo lo que la VOZ dice, sin acentos. Lo que sale en pantalla no cuenta:
    el video de MINISO (16/10/2026) enseñaba el nombre en el titular capturado y
    nunca lo pronunciaba, así que quien lo vio no supo de quién le hablaban."""
    return _sin_acentos(" ".join(p.get("narracion", "") or "" for p in guion.get("planos", [])
                                 if ids is None or p.get("id") in ids))


def _claves(texto: str) -> set[str]:
    """Las palabras con carga del texto, recortadas a seis letras para que
    aguanten la flexión ("discriminan" y "discriminación" comparten "discri")."""
    palabras = re.findall(r"[a-z]+", _sin_acentos(texto))
    return {p[:6] for p in palabras if len(p) >= 5 and p not in _VACIAS}


def _cita_fuente(renglon: str, fuentes: dict) -> bool:
    """Si el renglón nombra una de las claves de `_schema.fuentes` (o el dominio
    de su URL)."""
    texto = _sin_acentos(renglon)
    for clave, valor in (fuentes or {}).items():
        if _sin_acentos(str(clave)) in texto:
            return True
        dominio = re.search(r"https?://(?:www\.)?([\w.-]+)", str(valor))
        if dominio and dominio.group(1).split(".")[0] in texto:
            return True
    return False


def problemas(guion: dict) -> list[str]:
    """Lo propio de esta fórmula, además de lo que ya revisa `problemas_cercania`."""
    out: list[str] = []
    schema = guion.get("_schema") or {}

    niveles = schema.get("tres_niveles") or {}
    if faltan := [n for n in NIVELES if not str(niveles.get(n, "")).strip()]:
        out.append("falta en _schema.tres_niveles: " + ", ".join(faltan))
    elif not str(niveles.get("pendiente_de_pedir", "")).strip():
        out.append('falta "_schema.tres_niveles.pendiente_de_pedir": qué se pidió para llenar '
                   "el hueco (transparencia, llamada, registro consultado)")

    if not str(schema.get("que_paso", "")).strip():
        out.append('falta "_schema.que_paso": qué se dice que pasó, en una frase para quien no lo '
                   "vio: quién lo dice, dónde, de quién y qué exactamente")
    else:
        from dato_mata_gato_bot.instruccion_polemica import problemas_de_que_paso
        out += problemas_de_que_paso(guion, schema, PLANOS_DEL_RUMOR)

    if not str(schema.get("vale_sin_el_rumor", "")).strip():
        out.append('falta el candado "_schema.vale_sin_el_rumor": por qué el video se sostiene '
                   "sin el rumor. Si no se puede escribir, cambia de tema")

    condiciones = schema.get("condiciones") or {}
    if faltan := [c for c in CONDICIONES if not str(condiciones.get(c, "")).strip()]:
        out.append("no explica cómo cumple estas piezas en _schema.condiciones: " + ", ".join(faltan))

    # Pieza 9: el nivel 3 se cierra abriendo. Dos o tres hipótesis en pregunta,
    # con una inocente entre ellas, para que la gente discuta en vez de asentir.
    abiertas = schema.get("preguntas_abiertas") or []
    if isinstance(abiertas, str):
        abiertas = [abiertas]
    if len(abiertas) < 2:
        out.append('faltan "_schema.preguntas_abiertas": dos o tres explicaciones posibles de '
                   "por qué falta lo que falta, EN PREGUNTA, que el canal no elige")
    elif afirmadas := [q for q in abiertas if "?" not in str(q)]:
        out.append("estas van en pregunta, no en afirmación (el canal no tiene documento para "
                   "afirmarlo): " + "; ".join(str(q)[:60] for q in afirmadas))

    if not str(schema.get("pregunta_del_publico", "")).strip():
        out.append('falta "_schema.pregunta_del_publico": la pregunta que la gente se está '
                   "haciendo. Sin ella el nivel 2 se va por otro lado (pasó el 15/10/2026: el "
                   "video del hombre que fingía discapacidad terminó hablando de multas de "
                   "estacionamiento)")

    tipos = {p.get("tipo") for p in guion.get("evidencia", [])}
    if "documento" not in tipos:
        out.append("sin evidencia de tipo \"documento\": en un tema viral el video necesita una "
                   "fuente primaria en pantalla (decreto, punto de acuerdo, contrato, informe)")
    if not (tipos & DE_REDES):
        out.append("sin evidencia de redes (\"video_red\" o \"red_social\"): el tema nació en "
                   "redes y hay que ENSEÑARLO, no contarlo de oídas")

    sin_nota = set((guion.get("plus") or {}).get("sin_nota_animada") or [])
    if faltan_planos := [p for p in PLANOS_DEL_RUMOR if p not in sin_nota]:
        out.append('falta en plus.sin_nota_animada: ' + ", ".join(faltan_planos)
                   + ". Animar el cuerpo del artículo que afirma el rumor es publicarlo")

    out += _problemas_de_nombres(guion, schema)
    out += _problemas_del_check_final(guion, schema)
    out += _problemas_de_hallazgo(schema)
    return out


def _problemas_de_hallazgo(schema: dict) -> list[str]:
    """De dónde salió el tema (16/10/2026, Javier: "esos temas virales los tienes
    que buscar en redes sociales... el tema de Vicky Wolff salió porque era un
    tema popular en la plataforma"). Un tema que se encontró en un portal es una
    noticia, y para eso está la fórmula de cercanía."""
    hallado = str(schema.get("hallado_en", "")).strip()
    if not hallado:
        return ['falta "_schema.hallado_en": en qué PLATAFORMA, en qué cuenta y con cuántas '
                "vistas o comentarios encontraste el tema. Un tema viral se busca en redes, no "
                "en los portales; si salió de una nota, es una noticia y va en la fórmula de "
                "cercanía"]
    bajo = _sin_acentos(hallado)
    out = []
    if not any(p.strip() in bajo for p in PLATAFORMAS):
        out.append('"_schema.hallado_en" no nombra una plataforma (TikTok, Facebook, Instagram, '
                   f"X, YouTube): \"{hallado[:70]}\". El tema se descubre dentro de la red")
    if not re.search(r"\d", hallado):
        out.append('"_schema.hallado_en" no trae los números de la publicación (vistas, '
                   "comentarios o compartidos): sin cifra no se sabe si de verdad está dando "
                   "conversación")
    return out


def _problemas_de_nombres(guion: dict, schema: dict) -> list[str]:
    """NOMBRES (16/10/2026): lo que tiene nombre se dice con su nombre, y se
    DICE. La única excepción son los menores de edad, y esa no se comprueba
    aquí: se comprueba que no falte ninguno de los que el guion sí declara."""
    out: list[str] = []
    senalados = schema.get("senalados") or []
    if isinstance(senalados, str):
        senalados = [senalados]
    senalados = [str(s).strip() for s in senalados if str(s).strip()]
    if not senalados:
        out.append('falta "_schema.senalados": a quién nombra el guion (la empresa, la '
                   "institución, la cuenta que lo publicó, el funcionario). Fuera de los "
                   "menores de edad no hay nombre que se calle")
        return out
    dicho = _narrado(guion)
    if not dicho:
        return out
    if mudos := [s for s in senalados if _sin_acentos(s) not in dicho]:
        out.append("la narración no dice estos nombres de _schema.senalados: "
                   + ", ".join(mudos) + ". Enseñarlos en una captura no basta (pasó con "
                   "MINISO: el nombre salía en el titular y la voz nunca lo pronunció)")
    return out


def _problemas_del_check_final(guion: dict, schema: dict) -> list[str]:
    """EL CHECK FINAL (16/10/2026, Javier: "verifica si la información es
    correcta y si la historia es la misma... me dio la impresión de que
    desviabas el tema")."""
    out: list[str] = []
    final = schema.get("verificacion_final")
    final = final if isinstance(final, dict) else {}
    datos = final.get("datos") or []
    if isinstance(datos, str):
        datos = [datos]
    if len(datos) < _MIN_DATOS:
        out.append(f'faltan renglones en "_schema.verificacion_final.datos" (hay {len(datos)}, '
                   f"mínimo {_MIN_DATOS}): al releer, cada cifra y cada fecha que dice la "
                   "narración con la clave de _schema.fuentes de donde sale")
    elif sueltos := [d for d in datos if not _cita_fuente(str(d), schema.get("fuentes") or {})]:
        out.append("estos renglones de _schema.verificacion_final.datos no nombran su clave de "
                   "_schema.fuentes: " + "; ".join(str(d)[:60] for d in sueltos))
    if not str(final.get("misma_historia", "")).strip():
        out.append('falta "_schema.verificacion_final.misma_historia": si los planos p03 a p07 '
                   "contestan la pregunta del público o se fueron a otro tema")

    # El desvío, medido. Basta UNA palabra de la pregunta en el nivel 2: esto
    # atrapa el cambio de tema entero (discapacidad -> multas de
    # estacionamiento), no el matiz. Pedir dos daba falsos positivos con los
    # verbos, que en español cambian de forma: "¿cómo le pagué?" contestado con
    # "agendarla no cuesta nada y sólo se paga en bancos" es la misma historia
    # (guion-viral-pasaporte-sitio-falso, 16/10/2026). Para el matiz está
    # "verificacion_final.misma_historia", que lo lee Claude y no una regex.
    pregunta = str(schema.get("pregunta_del_publico", "")).strip()
    nivel_2 = _narrado(guion, PLANOS_DEL_DATO)
    claves = _claves(pregunta)
    if pregunta and nivel_2 and claves and not any(k in nivel_2 for k in claves):
        out.append("los planos p03 a p07 no hablan de nada de lo que pregunta "
                   f'"_schema.pregunta_del_publico" ("{pregunta[:60]}"). El nivel 2 contesta '
                   "ESA pregunta, no una parecida (pasó el 15/10/2026 con el video del hombre "
                   "que fingía discapacidad, que terminó en multas de estacionamiento)")
    return out
