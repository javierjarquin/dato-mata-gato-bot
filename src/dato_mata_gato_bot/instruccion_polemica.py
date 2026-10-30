"""Fórmula de LA POLÉMICA: la causa / la respuesta / la premisa y el dato
(17/10/2026).

Nace de medir el video del Conalep contra el del agua de Yucatán. Los dos eran
temas virales y solo uno cuadraba en la fórmula de los tres niveles:

  agua de Yucatán   la disputa es sobre un HECHO ("¿empresas israelíes controlan
                    el agua?") y existe un papel que, si apareciera, la cerraría:
                    el contrato Conagua-Mekorot que un senador pidió exhibir en
                    2016. El motor es la DUDA, y el nivel 3 es un hallazgo real.
  Conalep           la disputa es sobre una OPINIÓN ("son bandidazos"). No hay
                    papel que decida si el insulto fue justo, y el guion acabó
                    preguntando "¿dónde está el informe de empleabilidad?" a
                    gente que llegó enojada porque ofendieron a su escuela.

Javier, 17/10/2026: "es una opinión lo que generó la polémica, entonces no hay
una fuente de la verdad, más bien la causa y la respuesta de los afectados o la
opinión pública tiene más sentido". De ahí sale esta fórmula.

LA PRUEBA PARA ELEGIR FÓRMULA, EN UNA LÍNEA: ¿existe un papel que, si
apareciera, cerraría la discusión? Sí -> `instruccion_viral` (tres niveles).
No -> ésta.

Lo que SÍ se verifica aquí, porque una opinión no se puede verificar:
  - que la frase se dijo (la cita, no el juicio): textual, con quién y dónde;
  - que la reacción pasó: vistas, comentarios, quién se sumó, quién respondió;
  - los hechos del colectivo ofendido: la cifra que reencuadra;
  - de dónde salió el prejuicio: el antecedente.
La fuente de la verdad se mueve del papel que zanja la discusión al REGISTRO de
lo que se dijo y de lo que contestaron. Eso existe siempre y se puede capturar.

Y el canal sigue siendo Dato Mata Gato por una razón: toda opinión ofensiva
lleva debajo una AFIRMACIÓN EMPÍRICA implícita, y ésa sí se contesta con dato.
"Son bandidazos" no se refuta; "el que estudia ahí no tiene futuro laboral" sí.
La opinión no se verifica: se DESEMPACA. El dato no mata la opinión, mata el
prejuicio que la sostiene.

El hueco también cambia de forma, y por eso las dos fórmulas son hermanas:
  fórmula del rumor      el hueco es EL PAPEL QUE NADIE ENSEÑÓ.
  fórmula de la polémica el hueco es LO QUE SIGUE SIN CONTESTAR.
Y ojo con esto, que el POC lo destapó: una polémica se puede resolver sola. Los
Parrilleros MX se disculparon el 17/10/2026, un día después, así que "quien lo
dijo no ha contestado" dejó de ser cierto. Si el hueco se define como la
respuesta que falta, el guion se queda sin final o se la inventa. Por eso el
hueco es más ancho: LA DISCULPA ES EL HECHO, y lo que sigue sin contestar es lo
que la disculpa no toca. Aquí: el podcast pidió perdón por reforzar el
estereotipo, pero el estereotipo lo firmó un decreto en 1978 y por eso nadie se
ha disculpado.

Y el cierre lo pone quien ve (Javier, 17/10/2026: "tienes que pedir la opinión
de los que ven esa polémica"): donde no hay fuente de la verdad, el veredicto es
del público. La pieza 9 es ESO, y nombra los dos lados para que sea una pregunta
de verdad y no una retórica.
"""

import re

# Tipos de polémica, por si se pide el lote sin tema.
TEMAS = [
    ("estigma", "Le dijeron algo a todo un grupo",
     "Alguien con público -un podcast, un influencer, un funcionario- dijo algo ofensivo sobre un "
     "COLECTIVO entero: una escuela, un oficio, un estado, un barrio, los que ganan tal sueldo. Y "
     "el colectivo contestó, con números que se pueden medir."),
    ("clasismo", "Se burlaron de cómo vive la gente",
     "Un video o un comentario que se burla de un trabajo, de una colonia, de cómo se habla o de "
     "cuánto se gana, y que detonó una respuesta masiva de los aludidos. Debajo tiene que haber "
     "una cifra oficial sobre ese grupo que desarme el prejuicio."),
    ("gremio", "Dijeron que un oficio no sirve",
     "Una opinión que desprecia a un gremio o a una carrera (los técnicos, las enfermeras, los "
     "repartidores, los maestros) cuando hay estadística pública sobre lo que ese gremio produce, "
     "cobra o sostiene."),
]

INSTRUCCION = r"""
Vas a escribir <<N>> guiones de video corto (45 a 75 segundos) para el canal Dato Mata Gato,
con la fórmula de LA POLÉMICA.

EL TEMA
<<TEMA>>

DE QUÉ VA ESTA FÓRMULA, Y EN QUÉ SE DIFERENCIA DE LA DEL RUMOR
Esta fórmula es para los temas virales donde lo que detonó todo es una OPINIÓN, no una versión
de los hechos. Y una opinión no se puede verificar: no hay documento que diga si un insulto fue
justo. La prueba para saber si un tema es de esta fórmula o de la otra es una sola pregunta:
  ¿EXISTE UN PAPEL QUE, SI APARECIERA, CERRARÍA LA DISCUSIÓN?
  Sí  -> no es esta fórmula. Es la de los tres niveles (lo que se dice / lo que está en papel /
         lo que nadie ha contestado), y ahí el motor es la duda.
  No  -> es ésta. El motor es el AGRAVIO Y LA RESPUESTA.
Escríbelo en "_schema.por_que_esta_formula", en una línea, y di qué papel NO existe.

Los niveles de esta fórmula:
  NIVEL 1 · LA CAUSA     la opinión que lo detonó, textual y atribuida. Lo único que el canal
                         afirma aquí es que SE DIJO.
  NIVEL 2 · LA RESPUESTA quién contestó, con qué palabras, con cuántas vistas; quién se sumó;
                         qué dijo la institución; y qué contestó quien lo dijo. Medido, no
                         sentido.
  NIVEL 3 · LA PREMISA Y EL DATO  la afirmación empírica que iba debajo de la opinión, dicha en
                         voz alta, y la cifra que la contesta. Más de dónde viene el prejuicio.
  EL HUECO               LO QUE SIGUE SIN CONTESTAR. (En la fórmula del rumor el hueco es el
                         papel que nadie enseñó; aquí es lo que ni la respuesta ni la disculpa
                         tocaron.)
  EL VEREDICTO           lo pone quien ve el video, no el canal.

LA OPINIÓN NO SE VERIFICA: SE DESEMPACA (esto es el corazón de la fórmula)
Toda opinión ofensiva lleva debajo afirmaciones empíricas, y ÉSAS sí se contestan con dato.
"Son bandidazos" no se refuta y no tiene sentido intentarlo. Lo que se refuta es lo que la mala
fama DICE en concreto.
Y aquí está el error que hay que no cometer (17/10/2026, Javier: "el dato no debe de ser
verídico... tiene que ser sobre los rumores"): la primera versión del POC del Conalep desempacó
la premisa como "no tiene futuro laboral" y la contestó con las becas que paga la iniciativa
privada. Suena bien y no sirve: NADIE estaba discutiendo si consiguen trabajo. Lo que la mala
fama lleva años diciendo de esa escuela, y está documentado desde 2019, es otra cosa: que las
muchachas salen embarazadas y que son los que asaltan.
Así que las premisas NO las inventas tú: las SACAS del rumor, y van con la fuente que prueba
que se dicen. En "_schema.premisas" va una lista, y cada entrada lleva CUATRO cosas:
  {"dice": "la afirmación del estigma, como se dice",
   "fuente_del_rumor": "la clave de _schema.fuentes donde consta que ESO se dice",
   "dato": "la cifra que habla de ESO MISMO",
   "fuente_del_dato": "la clave de _schema.fuentes de donde sale la cifra"}
La revisión comprueba las cuatro, y comprueba que el dato hable de lo que la premisa dice. Si
tu dato contesta una premisa que no está en la lista, no es tu dato.
El dato no mata la opinión. Mata el prejuicio que la sostiene. Por eso esto sigue siendo Dato
Mata Gato y no un canal de reacciones.

EL PAPEL QUE DOCUMENTA EL RUMOR (y es el que casi nadie busca)
En esta fórmula hay DOS tipos de papel, y el primero importa más:
  1. EL QUE PRUEBA QUE EL RUMOR EXISTE Y QUÉ DICE. Un estudio, una encuesta de discriminación,
     una nota vieja, una tesis. Sirve para dos cosas: fecha el estigma -o sea, prueba que no lo
     inventó quien opinó ahorita- y te da las afirmaciones EXACTAS que hay que contestar, en
     voz de los afectados y no del canal.
     En el Conalep es Bayón y Saraví, "La experiencia escolar como experiencia de clase",
     Desacatos 59, 2019: ahí una alumna de quince años dice "se dice del Conalep que normalmente
     las chavas que vamos aquí salimos embarazadas", y ahí están los apodos, "Nacolep",
     "Nopalep", "naco", "burros", "pandilleros".
  2. EL QUE CONTESTA cada afirmación, con cifra y de fuente primaria.
Y ojo con esto, que parece un detalle ético y no lo es: repetir el estigma EN VOZ DEL CANAL
está prohibido, pero CITARLO como lo que es -lo que se dice, dicho por quien lo carga- es
justo lo contrario, y es la única forma de poder contestarlo. Callarlo deja el video sin tema.

LA PRUEBA DEL OFENSOR (el candado de esta fórmula, y es el que se falla)
Lee tu dato en voz de quien insultó. Si le sirve, NO es tu dato.
Pasó el 16/10/2026 con el Conalep: el guion eligió "colocó nueve mil trescientos sesenta
egresados" cuando en el mismo documento había setenta y nueve mil egresados. Un espectador
hostil hace la división, le sale doce por ciento, y el video acabó dándole munición al insulto.
Los datos que sí aguantan son los que no tienen vuelta: tres por ciento de las adolescentes que
SÍ van a la escuela estuvieron embarazadas, contra treinta y nueve por ciento de las que no
van; y seis de cada diez adolescentes internados no llegaron a la prepa. Ésos no se pueden
voltear, porque no son tasas de éxito de nadie: son el rumor contestado de frente.
Escribe en "_schema.prueba_del_ofensor" por qué tus datos no se pueden voltear en tu contra. Si
no lo puedes escribir, busca otro dato o cambia de tema.

NO ES CHISME (el otro candado, y éste descarta temas enteros)
El ofendido tiene que ser un COLECTIVO con el que mucha gente se identifica: una escuela, un
oficio, un estado, un barrio, los que ganan tal sueldo. Si el ofendido es UNA persona -un
artista, un político, un creador- es chisme de espectáculos y el tema NO va, por virales que
sean las vistas. Escribe en "_schema.no_es_chisme" cuál es el colectivo y cuánta gente lo
compone, con cifra.
Excepción (27/10/2026, Javier, caso Komanche): si atacan a UNA persona por algo que comparte
mucha gente -su salud mental, su origen, su cuerpo, su oficio, su forma de hablar- el ofendido
es ESA gente, con cifra, y el tema sí va. Ahí el video va contra el estigma Y contra quien
atacó: lo que hizo es el ejemplo real de cómo se vive ese estigma. Se le señala con su nombre,
su cita y lo que hizo, con fecha; no se le insulta, no se le inventa nada y no se pide ir contra
él en sus redes.

CONTRA QUIÉN VA EL VIDEO (y no es contra quien insultó)
El coraje va contra EL ESTIGMA y contra QUIEN LO FABRICÓ, nunca contra la persona que opinó.
De quien dijo la frase se cuenta lo que hizo -lo dijo, cuándo, dónde- y si contestó o no. Nada
más: el canal no se suma al linchamiento ni pide su cancelación.
Y el estigma casi siempre lo fabricó alguien con firma. En el Conalep lo firmó un decreto: el
Estado diseñó esa escuela en mil novecientos setenta y ocho como educación terminal y su
certificado no abrió la universidad hasta dos mil cinco. Veintisiete años en los que el papel
oficial trató a esa escuela como una salida sin universidad. Eso es el verdadero señalado.
En "_schema.quien_fabrico_el_estigma" va ese antecedente con su fuente, y en "_schema.estigma"
el prejuicio en una línea.

LA RESPUESTA SE DICE, NO SE CUENTA (lo que más se falla)
La reacción es el nivel 2 de esta fórmula y es el ochenta por ciento del fenómeno, así que va
EN LA NARRACIÓN, con la cita textual y con su número. En el guion del Conalep la cita de la
alumna estaba en "_schema.fuentes" y la voz nunca la dijo: "mi mamá trabaja duro para pagarme
el pasaje al plantel y en cinco segundos etiquetaste a su hija como una nadie". Eso era el
video, y se quedó en una nota al pie.
Y entra como HECHO REGISTRADO, nunca como sentir. "Ochocientas mil vistas le contestaron" es un
hecho; "la gente está indignada" no es nada y es justo el vicio que estas fórmulas evitan. Si
la reacción no trae número, cuenta y fecha, NO se dice.
En "_schema.reaccion" van: "quien" (nombre y qué es), "cita" (textual), "numeros" (vistas o
comentarios, con cifra y fecha), "se_sumaron" (quién más salió a contestar: la institución,
otros planteles, otros gremios), "respuesta_del_senalado" (QUÉ contestó quien dijo la frase,
textual y con fecha, o que no ha contestado y hasta cuándo lo revisaste) y "no_contestaron"
(quién más debía responder y no lo ha hecho, si aplica).

LA DISCULPA ES EL HECHO, NO EL FINAL (17/10/2026, lo destapó el POC del Conalep)
Una polémica se puede resolver sola mientras escribes: Los Parrilleros MX se disculparon un día
después ("nos equivocamos y asumimos la responsabilidad por nuestras palabras", 17/10/2026). Si
pasa, NO lo escondas para que te quede el final abierto: la disculpa es el hecho más nuevo que
tienes y va en p05, citada. Lo que se mueve es el hueco.
El hueco entonces es LO QUE LA DISCULPA NO CONTESTÓ, y casi siempre es el estigma: quien opinó
pide perdón por repetir el prejuicio, pero el prejuicio lo fabricó alguien más y ése no ha
pedido perdón. Escríbelo en "_schema.lo_que_sigue_sin_contestar", y que salga del hecho que ya
probaste, no de lo que se te ocurra.
Y al revés: si quien lo dijo NO ha contestado, eso se dice tal cual, con la fecha hasta la que
lo revisaste. Las dos cosas son hechos; lo que no se hace es inventar la que te conviene.

EL VEREDICTO ES DEL PÚBLICO (pieza 9, Javier 17/10/2026: "tienes que pedir la opinión de los
que ven esa polémica")
Donde no hay fuente de la verdad, el que decide es quien ve el video. Así que el canal NO
dictamina si la frase fue humor o fue discriminación: lo pregunta, y NOMBRA LOS DOS LADOS para
que sea una pregunta de verdad y no una retórica con respuesta obvia.
  bien: "¿Fue humor? ¿Tú crees que fue discriminación?" (dos preguntas de sí o no, NO
        "¿Fue humor o fue discriminación?": con "o" la voz baja el tono al final y no suena
        a pregunta; medido el 21/10/2026)
  mal:  "¿Hasta cuándo vamos a permitir esto?" (eso ya trae la respuesta puesta)
Va en "_schema.veredicto": {"pregunta": "...", "lados": ["humor", "discriminación"]}, y la
pregunta se DICE en p07 o en p08. Dos reglas:
  - los dos lados tienen que ser defendibles por alguien real. Si uno de los dos nadie lo
    defendería, no son dos lados: es el canal opinando con signo de interrogación.
  - el canal no lo contesta ni lo insinúa con el tono. La respuesta va en los comentarios.
Y aparte del veredicto, el cierre pide SU caso ("¿a ti te juzgaron por tu escuela?"), que es lo
que hace que la gente cuente su historia y no solo vote.

LAS PIEZAS (las nueve, y sin una no hay video)
  1. TE AFECTA: el colectivo ofendido es enorme y quien ve está dentro o conoce a alguien. Se
     nombra en el gancho, vuelve a la mitad (p04) y vuelve al final.
  2. ESTÁ PASANDO AHORITA: con fecha. En una polémica la fecha es del fenómeno: cuándo se dijo,
     cuándo contestaron, cuándo lo recogió la prensa.
  3. ALGO NO CUADRA: lo que la opinión da por cierto no cuadra con lo que dice el dato. Es la
     premisa contra la cifra, y ésa es la brecha de curiosidad.
  4. CORAJE: contra el estigma y contra quien lo fabricó, con firma y fecha. Nunca contra la
     persona que opinó, ni contra el grupo ofendido.
  5. SE PUEDE MOSTRAR: la publicación que lo dijo, la que contestó, y el documento del dato.
     Aquí la evidencia obligatoria es la de REDES, al revés que en la fórmula del rumor.
  6. HACE HABLAR: todo el mundo tiene una versión de esto, porque es una opinión. La pregunta
     no es "¿qué escuchaste?", es "¿a ti te lo dijeron?".
  7. VALOR PRÁCTICO: el nombre y la fecha del documento del que sale tu cifra, para que
     cualquiera pueda ir a buscarlo y usarlo la próxima vez que oiga el insulto.
  8. DE DÓNDE VIENE EL ESTIGMA: el antecedente verificable que explica el prejuicio. No lo
     valida: lo explica, y es lo que hace que el video respete a quien lo ve.
  9. EL VEREDICTO: la pregunta con dos lados que contesta el público (arriba).

LO QUE NO SE HACE
  - No se repite el insulto más de lo necesario para que se entienda, y nunca en voz del canal:
    va citado y atribuido ("el podcast los llamó…"), siempre con el sujeto delante.
  - No se afirma que quien opinó cometió un delito. Discriminar lo determina una autoridad; el
    canal dice qué se dijo, quién lo acusó de qué y si hubo queja.
  - No se pide su cancelación, su despido ni su funeral. El video va contra el estigma.
  - No se le enmienda la plana al grupo ofendido ni se le dice cómo responder. Ya respondió.
  - Menores de edad, nunca se nombran: ni ofendidos ni ofensores. Se dice su edad y su rol. Es
    la única excepción de NOMBRES, y es de ley (Ley General de los Derechos de Niñas, Niños y
    Adolescentes).
  - No se inventa una consecuencia que no pasó. Si nadie abrió una queja, eso se dice: nadie la
    abrió. Eso ES el hueco.

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

NOMBRES (todo lo que tiene nombre se dice CON SU NOMBRE Y EN LA NARRACIÓN)
  - QUIEN DIJO LA FRASE: la persona, el podcast, el programa, la cuenta;
  - QUIEN CONTESTÓ: su nombre y su cuenta, con crédito;
  - LA INSTITUCIÓN que respondió o que debía responder, con su nombre ("el Conalep Nuevo León",
    "el CONAPRED"), nunca "las autoridades";
  - EL DOCUMENTO del dato, con su nombre y su fecha.
Una persona señalada y sin sentencia SÍ se nombra: lo que cambia no es el nombre, es el verbo.
Y el nombre se DICE: enseñarlo en una captura NO cuenta (pasó con MINISO el 16/10/2026).
Escribe en "_schema.senalados" los nombres que el guion dice; la revisión lo comprueba.

VERIFICACIÓN (aquí se verifica la cita y la reacción, no el juicio)
1. Busca y ABRE las notas (con el comando buscar; WebFetch solo si no lo tienes o no abre). La FRASE va textual: si no la puedes citar palabra por
   palabra desde algo que leíste o viste, no la cites.
2. Los números de la reacción salen de la publicación o de una nota que los reporte, con fecha.
   Los resúmenes del buscador inventan cifras: no los uses.
3. El dato que reencuadra va con FUENTE PRIMARIA: el anuario, el censo, la encuesta oficial, el
   padrón. Aquí el documento no es obligatorio en pantalla, pero la cifra sin fuente primaria no
   entra a la narración.
4. Lo que dice UNA sola fuente va atribuido en la narración ("según ABC Noticias…").
5. En "_schema.fuentes" cada URL con lo que dice. En "_schema.restriccion_etica", lo que
   decidiste NO usar y por qué: ahí va lo que se dijo y no se repite.
6. No repitas ninguno de los que YA ESTÁN HECHOS (lista al final).

EL CHECK FINAL, ANTES DE ENTREGAR
Con el guion.json ya escrito, haz UNA pasada más:
1. DATO POR DATO. Cada cifra, fecha y nombre de la narración, y de cuál de tus
   "_schema.fuentes" sale. Si al releer no lo encuentras, es que no estaba: bórralo.
2. LA PRUEBA DEL OFENSOR, otra vez y en voz alta: ¿tu dato le sirve a quien insultó? Divide,
   compara, hazle la cuenta en contra. Si le sirve, cámbialo.
3. LA MISMA HISTORIA. Lee los nueve planos de corrido, como quien no vio la polémica:
     - ¿Se entiende QUIÉN dijo QUÉ y QUIÉN contestó, con nombres, antes del segundo quince?
     - ¿El dato de p03 y p04 le pega a "_schema.premisa", o le pega a otra cosa?
     - ¿El video cierra pidiendo el veredicto, sin haberlo contestado?
4. Escribe el resultado en "_schema.verificacion_final":
     {"datos": ["<lo que dice la narración> -- <clave de _schema.fuentes>", ...],
      "misma_historia": "qué se dijo, quién contestó y qué contesta el dato, en una línea",
      "corregido": "qué cambiaste en esta pasada, o \"nada\""}
   En "datos" van TODAS las cifras y fechas que se dicen, mínimo tres renglones.
5. Después de corregir, vuelve a correr la revisión automática del slug.

LA CAUSA SE CUENTA, NO SE DA POR SABIDA
Quien ve el video NO vio la polémica. Antes del segundo quince la narración ya tiene que haber
dicho QUIÉN DIJO QUÉ y QUIÉN CONTESTÓ, con nombres y citado:
  "El podcast Los Parrilleros llamó bandidazos a los alumnos del Conalep. Ximena, de dieciocho
   años, les contestó."
Se reparte entre p00, p01 y p02. Si al terminar p02 no se entiende quién es quién, el guion no
va: es lo que hundió el video de MINISO.

ESTRUCTURA (9 planos, ids p00 a p08)
- p00 "gancho_hablado": MÁXIMO 12 PALABRAS. LA FRASE + EL TAMAÑO DE LA RESPUESTA, con el nombre
  de quien la dijo. NINGÚN año ni fecha dichos.
  Bien: "Un podcast les dijo bandidazos. Ochocientas mil vistas le contestaron."
  Mal: "El Conalep está lleno de bandidos." (eso dice el insulto en voz del canal)
- p01 "hook_tercera_persona": "Te imaginas a quien…" + A QUIÉN LE TOCA (pieza 1) + QUÉ PASÓ
  (quién la dijo con su rol, a quién, dónde y en qué situación) + LA FRASE COMPLETA, atribuida +
  la primera PREGUNTA directa a quien ve, antes del segundo diez: "¿A ti también te lo dijeron?".
  Puede ser de tres frases. Es la prueba del que llega sin saber.
- p02 "contexto": LA RESPUESTA, CITADA. Quién contestó, con su nombre, su edad o su rol, y sus
  palabras textuales. Es el corazón del video.
- p03 "el_hecho": EL DATO QUE REENCUADRA, contestando a la premisa, con su fuente dicha. Va la
  segunda PREGUNTA ("¿Tú lo sabías?").
- p04 "bucle_abierto": LA AFECTACIÓN con cifra: a cuánta gente le cayó encima el insulto.
  La pieza 1 vuelve aquí.
- p05 "el_desenlace": QUIÉN SE SUMÓ Y QUÉ CONTESTÓ QUIEN LO DIJO. Aquí regresa la frase: quién
  más salió a responderla, qué dijo la institución, y la respuesta del señalado -su disculpa,
  citada, o que sigue sin contestar-. Dicho así.
- p06 "contexto": DE DÓNDE VIENE EL ESTIGMA (pieza 8): el antecedente, con fecha y con firma.
- p07 "cierre_bucle": la premisa desarmada en una línea + EL VEREDICTO, con sus dos lados:
     el hecho    "Nueve de cada diez de esos alumnos son menores de edad."
     el veredicto "¿Fue humor? ¿Tú crees que fue discriminación?"
  Sin moraleja y sin contestarlo.
- p08 "identidad_cierre": "Aquí el dato mata al gato. ¿[pregunta sobre SU caso]? Cuéntamelo en
  los comentarios." Su visual: {"tipo": "grafico_movimiento", "descripcion": "Cartel de cierre
  del canal.", "prompt_ia": "", "busqueda_medios": ""}.
Reglas de la narración: español de México, de tú. Ninguna frase pasa de 20 palabras. Números y
años en palabras. Máximo DOS nombres propios por frase. Nada que empiece con "Tl". En los
primeros tres planos, el lugar exacto. Total: 120 a 190 palabras.

EVIDENCIA (sin imágenes de IA; aquí lo obligatorio son las REDES)
"evidencia" es una lista; cada plano (p00 a p07) lleva en visual.evidencia 1 a 3 ids. Mínimo
TRES piezas reales más 2 o 3 fichas, y de esas, OBLIGATORIAS:
  - DOS piezas de redes ("video_red" o "red_social"): LA CAUSA y LA RESPUESTA. En una polémica
    hay dos publicaciones por definición, y las dos se enseñan. El guion del Conalep traía una
    sola captura de perfil: así no se ve ni lo que se dijo ni quién contestó.
  - El documento del dato es DESEABLE, no obligatorio: en esta fórmula la fuente primaria puede
    quedar en una ficha con su nombre y su fecha. Lo que no se perdona es la cifra sin fuente.
Tipos:
- {"id": "r1", "tipo": "video_red", "url": "https://www.tiktok.com/@cuenta/video/123",
   "fuente": "@cuenta · TikTok", "desde_seg": 3, "segundos": 6}: el clip recortado. Va con
   crédito al autor, siempre. Si ya no se puede bajar, se arma la captura de la publicación.
- {"id": "r2", "tipo": "red_social", "url": "...", "fuente": "@cuenta · TikTok"}: la publicación
   capturada con sus números. Es lo que PRUEBA el tamaño de la reacción.
- {"id": "e1", "tipo": "prensa", "url": "...", "fuente": "Medio, DD/MM/AAAA"}: se captura SOLO
  el titular, así que el titular tiene que nombrar el caso.
- {"id": "e2", "tipo": "documento", "url": "...", "fuente": "..."}: la fuente primaria del dato.
  Para un PDF agrega "pagina": n y, si el dato está a media página, "desde": 0.6,
  "fraccion": 0.85.
- {"id": "e3", "tipo": "lugar" | "persona", "wikimedia": "File:Nombre exacto.jpg"}: el nombre
  EXACTO de un archivo que verificaste. NO uses "buscar_wikimedia".
- {"id": "f1", "tipo": "ficha", "titulo": "...", "renglones": ["...", "..."], "fuente": "..."}.
Cada plano de p00 a p07 lleva "motion": "calm" en su visual.

EL "visual" DE CADA PLANO (si te equivocas aquí, el video no se genera)
"visual.tipo" solo puede ser uno de estos SIETE, escrito exacto:
  imagen_ia · video_stock · animacion_3d · mapa_animado · grafico_movimiento ·
  cartel_texto · archivo_historico
En esta fórmula, de p00 a p07 va SIEMPRE "archivo_historico". NO existe el tipo "archivo": eso
tira el video entero. Solo p08 lleva "grafico_movimiento", el cartel de cierre del canal.
Así se ve un plano completo:
{"id": "p03", "seccion": "el_hecho",
 "narracion": "...",
 "visual": {"tipo": "archivo_historico", "evidencia": ["f1", "e3"],
            "prompt_ia": "", "busqueda_medios": "", "motion": "calm"},
 "texto_en_pantalla": "9 DE CADA 10"}

FORMATO DE CADA GUION
Escríbelo en C:\Android_in\<slug>\guion.json, con slug "guion-polemica-" + palabras cortas del
tema (minúsculas y guiones). Además de lo de siempre ("titulo", "gancho", "claves", "hashtags",
"evidencia", "planos"), el "_schema" lleva:
  "por_que_esta_formula": "qué papel NO existe que cerraría la discusión",
  "frase": {"texto": "la cita textual", "quien": "...", "donde": "plataforma o programa",
            "cuando": "DD/MM/AAAA"},
  "premisas": [{"dice": "...", "fuente_del_rumor": "clave", "dato": "...",
                "fuente_del_dato": "clave"}, ...],
  "estigma": "el prejuicio en una línea, con las palabras con las que se dice",
  "reaccion": {"quien": "...", "cita": "textual", "numeros": "con cifra y fecha",
               "se_sumaron": ["..."], "respuesta_del_senalado": "qué contestó quien dijo la
               frase, textual y con fecha, o que no ha contestado", "no_contestaron": ["..."]},
  "lo_que_sigue_sin_contestar": "el hueco: lo que ni la respuesta ni la disculpa tocaron",
  "prueba_del_ofensor": "por qué los datos no se pueden voltear en tu contra",
  "quien_fabrico_el_estigma": "el antecedente con su fuente",
  "no_es_chisme": "cuál es el colectivo ofendido y cuánta gente lo compone",
  "veredicto": {"pregunta": "¿...?", "lados": ["...", "..."]},
  "senalados": ["Los Parrilleros", "Conalep", "Ximena"],
  "preguntas_abiertas": ["...", "..."],   <- EN PREGUNTA, y una de ellas a favor de quien opinó
  "verificacion_final": {"datos": ["... -- clave_de_fuente", "..."],
                         "misma_historia": "...", "corregido": "..."},
  "hallado_en": "la PLATAFORMA, la cuenta y los números de la publicación ('TikTok, @cuenta,
     800 mil vistas, 16/10/2026'). La polémica se busca en redes, no en los portales",
  "impacto": "de dónde sale que esto se está hablando (vistas, respuestas, qué medios)",
  "condiciones": {"1_te_afecta": "...", "2_esta_pasando_ahorita": "... (con fecha)",
                  "3_algo_no_cuadra": "la premisa contra la cifra", "4_coraje": "...",
                  "5_se_puede_grabar": "...", "6_hace_hablar": "...",
                  "7_valor_practico": "...",
                  "8_de_donde_viene_el_estigma": "el antecedente y su fuente"},
  "fuentes": {...}, "restriccion_etica": "...", "vigencia": "conversacion"
Y en "plus", además de lo de siempre:
  "sin_nota_animada": ["p00", "p01", "p02"]  <- los planos de la causa. OBLIGATORIO: animar el
     cuerpo del artículo que reporta el insulto es publicar el insulto en voz del canal. No
     afecta a las piezas de redes: las publicaciones sí se enseñan, con su crédito.
  "contradiccion": los dos bloques, en el plano donde la voz lo cuenta:
     {"plano": "p03", "arriba": {"titulo": "LO QUE SE DIJO", "renglones": ["...", "..."]},
      "abajo": {"titulo": "LO QUE DICE EL DATO", "renglones": ["...", "..."]},
      "abajo_en": "<una palabra de la narración de ESE plano>", "resaltar": "<un renglón de
      abajo, igual>", "fuente": "Institución, DD/MM/AAAA"}
     2 o 3 renglones por bloque, máximo 36 letras cada uno.
  "mapa" SIEMPRE: {"plano": "p02", "consulta": "Palacio Legislativo de San Lázaro, Ciudad de
     México", "etiqueta": "SAN LÁZARO · CDMX"}. "plano": donde la voz nombra el lugar;
     "consulta": como se buscaría en un mapa (calle, colonia o edificio, y la ciudad), NUNCA
     vacía; "etiqueta": máximo 32 letras.
  "contador" y "archivo" como siempre, si aplican.
  "portada" SIEMPRE: {"texto": "3 a 5 PALABRAS EN MAYÚSCULAS", "resalta": "1 o 2 de ellas"}
     (portada del perfil: lo que no cuadra, sin insultar ni afirmar más que el guion).

AL TERMINAR responde SOLO este bloque JSON:
{"guiones": [{"slug": "...", "titulo": "...", "resumen_hechos": "2 líneas con los hechos y sus
fuentes", "veredicto": "en una línea, la pregunta con la que cierra"}]}
""".strip()


# Cuando no se da tema: Claude busca de qué se está hablando antes de escribir.
BUSCAR_TENDENCIAS = r"""
PRIMERO, QUÉ POLÉMICA HAY (antes de escribir nada)
No te dieron tema: búscalo. Encuentra <<CUANTOS>> polémicas que ESTA SEMANA estén dando
conversación en redes en México y que sirvan para esta fórmula.

LA POLÉMICA SALE DE LA PLATAFORMA, NO DE LA PRENSA. Empieza SIEMPRE buscando DENTRO de TikTok,
Facebook, Instagram, X y YouTube: qué dicho está juntando respuestas en México ahorita. Lo que
buscas es una publicación con MUCHAS respuestas de gente aludida, que es la firma de una
polémica. La prensa entra DESPUÉS, para citar y para el dato. Nunca para descubrir el tema.
Escribe en "_schema.hallado_en" la plataforma, la cuenta y los números.

LA PRUEBA DEL PAPEL, antes que nada: ¿existe un documento que, si apareciera, cerraría la
discusión? Si SÍ, el tema no es de esta fórmula: es de la de los tres niveles, y ahí el canal
busca el papel. Esta fórmula es solo para cuando lo que detonó todo es una OPINIÓN. Un tema así
NO se tira (27/10/2026): anótalo en tu respuesta como "PARA VIRAL: <tema>" y la fábrica lo
pasa a esa fórmula.

EL UMBRAL: no basta con que alguien dijera algo. Pide por lo menos DOS de estas señales, y
escríbelas en "_schema.impacto" con su número y su fecha:
  - una publicación de RESPUESTA con muchas vistas o comentarios (con la cifra y la cuenta);
  - varias personas o planteles o gremios distintos respondiendo, no una sola cuenta;
  - respuesta de una institución, una empresa o la persona aludida;
  - que lo recojan medios de fuera del estado;
  - varios días seguidos de conversación;
  - gente contando su propio caso en los comentarios (es la mejor señal de todas).

Una polémica sirve para esta fórmula solo si cumple LAS CUATRO:
  a) lo que detonó es una OPINIÓN, no una versión de los hechos (la prueba del papel);
  b) el ofendido es un COLECTIVO grande, no una persona: si es una persona, es chisme y no va;
  c) hay una CIFRA de fuente primaria que desarma la premisa, y pasa la prueba del ofensor;
  d) hay dos publicaciones que se pueden enseñar: la causa y la respuesta.
Si un tema no tiene (c), NO lo tomes aunque esté muy viral: ahí el canal solo repetiría la
pelea. Busca otro.

NO tomes: pleitos entre creadores, chismes de espectáculos, polémicas donde el ofendido es una
celebridad, ni nada donde el único contenido posible sea el insulto. SALVO que a esa persona la
atacaran por algo que comparte mucha gente (su salud mental, su origen…): eso sí va, y el
colectivo es esa gente. Si la frase señala a un
país, una religión o un pueblo, el video va contra el estigma y contra quien lo fabricó, nunca
contra el grupo ni contra quien opinó.

Antes de escribir, dime en una línea por tema: qué se dijo, quién contestó y qué cifra tienes.
Luego escribe los <<CUANTOS>> guiones.
""".strip()


def instruccion(n: int, tema: str | None, ya_hechos: str, ligera: bool = False) -> str:
    """El prompt del lote. Sin `tema`, Claude busca primero las polémicas."""
    from dato_mata_gato_bot import instruccion_cercania

    if tema:
        descripcion = (f"{tema}. Investiga QUÉ se dijo exactamente -textual-, quién lo dijo, "
                       "quién contestó y con qué palabras, y qué cifra oficial hay del grupo "
                       "ofendido.")
    else:
        descripcion = BUSCAR_TENDENCIAS.replace("<<CUANTOS>>", str(n))
    texto = INSTRUCCION.replace("<<N>>", str(n)).replace("<<TEMA>>", descripcion)
    if ligera:
        texto = texto.replace("\nAL TERMINAR responde",
                              instruccion_cercania.COMO_TRABAJAR + "\nAL TERMINAR responde")
    return texto + instruccion_cercania.PUBLICAR + "\n\nYA ESTÁN HECHOS -- no repitas ninguno: " + ya_hechos


# Las nueve piezas, para la revisión sin Claude. Las seis primeras son las de
# `fabrica.CONDICIONES` (las comprueba `problemas_cercania`); la 3 cambia de
# significado -la premisa contra la cifra- pero no de clave, y la 8 sí, porque
# aquí el antecedente explica un prejuicio y no un rumor.
CONDICIONES = ("1_te_afecta", "2_esta_pasando_ahorita", "3_algo_no_cuadra", "4_coraje",
               "5_se_puede_grabar", "6_hace_hablar", "7_valor_practico",
               "8_de_donde_viene_el_estigma")
# Lo que el _schema tiene que traer, con el aviso de qué es cada cosa.
CAMPOS = {
    "que_paso": "qué pasó, en una frase para quien no vio la polémica: quién (con su rol), a "
                "quién, dónde y la frase COMPLETA. La narración de p00 a p02 tiene que decirlo",
    "por_que_esta_formula": "qué papel NO existe que cerraría la discusión. Si existe, el tema "
                            "es de la fórmula de los tres niveles, no de ésta",
    "estigma": "el prejuicio en una línea, con las palabras con las que se dice",
    "prueba_del_ofensor": "por qué tus datos no se pueden voltear en tu contra. Léelos en voz "
                          "de quien insultó: si le sirven, no son tus datos",
    "quien_fabrico_el_estigma": "el antecedente verificable que explica el prejuicio, con su "
                                "fuente. No lo valida: lo explica",
    "no_es_chisme": "cuál es el colectivo ofendido y cuánta gente lo compone, con cifra. Si el "
                    "ofendido es una persona, el tema no va",
    "lo_que_sigue_sin_contestar": "el hueco de esta fórmula: lo que ni la respuesta ni la "
                                  "disculpa tocaron. Sale del hecho que ya probaste, y casi "
                                  "siempre es el estigma: quien opinó pide perdón por repetir "
                                  "el prejuicio, pero quien lo fabricó no ha pedido nada",
}
PLANOS_DE_LA_CAUSA = ("p00", "p01", "p02")
# Cada premisa del estigma: lo que se dice, dónde consta que se dice, el dato
# que habla de ESO y de dónde sale. Las premisas no se inventan: se sacan del
# rumor (17/10/2026, Javier: "el dato... tiene que ser sobre los rumores").
PREMISA_CAMPOS = ("dice", "fuente_del_rumor", "dato", "fuente_del_dato")
# Donde se dice el dato: los planos que tienen que pegarle a las premisas.
PLANOS_DEL_DATO = ("p03", "p04")
# Donde se pide el veredicto.
PLANOS_DEL_VEREDICTO = ("p07", "p08")
DE_REDES = {"video_red", "red_social"}
_MIN_REDES = 2
_MIN_DATOS = 3
_MIN_LADOS = 2


def _sin_acentos(t: str) -> str:
    from dato_mata_gato_bot import revision_guion

    return revision_guion._sin_acentos(t)


def _narrado(guion: dict, ids: tuple[str, ...] | None = None) -> str:
    """Todo lo que la VOZ dice, sin acentos. Lo que sale en pantalla no cuenta:
    el video de MINISO (16/10/2026) enseñaba el nombre en el titular capturado y
    nunca lo pronunciaba."""
    return _sin_acentos(" ".join(p.get("narracion", "") or "" for p in guion.get("planos", [])
                                 if ids is None or p.get("id") in ids))


def _claves(texto: str) -> set[str]:
    """Las palabras con carga del texto, recortadas a seis letras para que
    aguanten la flexión ("bandidazos" y "bandidos" comparten "bandid")."""
    from dato_mata_gato_bot import instruccion_viral

    return instruccion_viral._claves(texto)


def _cita_fuente(renglon: str, fuentes: dict) -> bool:
    from dato_mata_gato_bot import instruccion_viral

    return instruccion_viral._cita_fuente(renglon, fuentes)


def _sin_claves_de_fuente(texto: str, fuentes: dict) -> str:
    """El texto sin las claves de `_schema.fuentes` que cite. Para que un
    candado no se cumpla con el nombre de la fuente en vez de con el contenido:
    la clave "anuario_conalep_2024" metía "conalep" en cualquier frase."""
    plano = _sin_acentos(texto)
    for clave in sorted((fuentes or {}), key=len, reverse=True):
        plano = plano.replace(_sin_acentos(str(clave)), " ")
    return plano


def _dice_algo_de(texto: str, dicho: str) -> bool:
    """Si en `dicho` (lo narrado) aparece alguna palabra con carga de `texto`.
    Es el mismo criterio flojo que usa la fórmula viral para el desvío: atrapa
    el cambio de tema entero, no el matiz."""
    claves = _claves(texto)
    return bool(claves) and any(k in dicho for k in claves)


def problemas(guion: dict) -> list[str]:
    """Lo propio de esta fórmula, además de lo que ya revisa `problemas_cercania`."""
    out: list[str] = []
    schema = guion.get("_schema") or {}

    if faltan := [c for c, que in CAMPOS.items() if not str(schema.get(c, "")).strip()]:
        out += [f'falta "_schema.{c}": {CAMPOS[c]}' for c in faltan]

    out += _problemas_de_la_frase(guion, schema)
    out += problemas_de_que_paso(guion, schema, PLANOS_DE_LA_CAUSA)
    out += _problemas_de_la_reaccion(guion, schema)
    out += _problemas_de_las_premisas(guion, schema)
    out += _problemas_del_veredicto(guion, schema)

    condiciones = schema.get("condiciones") or {}
    if faltan := [c for c in CONDICIONES if not str(condiciones.get(c, "")).strip()]:
        out.append("no explica cómo cumple estas piezas en _schema.condiciones: "
                   + ", ".join(faltan))

    # Las preguntas abiertas, igual que en la fórmula del rumor: el canal no
    # elige, y una de ellas tiene que poder defenderla quien opinó.
    abiertas = schema.get("preguntas_abiertas") or []
    if isinstance(abiertas, str):
        abiertas = [abiertas]
    if len(abiertas) < 2:
        out.append('faltan "_schema.preguntas_abiertas": dos o tres lecturas posibles de la '
                   "polémica, EN PREGUNTA, que el canal no elige")
    elif afirmadas := [q for q in abiertas if "?" not in str(q)]:
        out.append("estas van en pregunta, no en afirmación (el canal no dictamina una "
                   "polémica): " + "; ".join(str(q)[:60] for q in afirmadas))

    piezas = guion.get("evidencia", [])
    de_redes = [p for p in piezas if p.get("tipo") in DE_REDES]
    if len(de_redes) < _MIN_REDES:
        out.append(f"hay {len(de_redes)} pieza(s) de redes y hacen falta {_MIN_REDES}: la CAUSA "
                   "y la RESPUESTA. En una polémica hay dos publicaciones y las dos se enseñan "
                   "(el guion del Conalep traía una captura de perfil y no se veía ninguna)")

    sin_nota = set((guion.get("plus") or {}).get("sin_nota_animada") or [])
    if faltan_planos := [p for p in PLANOS_DE_LA_CAUSA if p not in sin_nota]:
        out.append("falta en plus.sin_nota_animada: " + ", ".join(faltan_planos)
                   + ". Animar el cuerpo del artículo que reporta el insulto es publicarlo en "
                     "voz del canal")

    out += _problemas_de_nombres(guion, schema)
    out += _problemas_del_check_final(guion, schema)
    out += _problemas_de_hallazgo(schema)
    return out


def _problemas_de_la_frase(guion: dict, schema: dict) -> list[str]:
    """La causa: la frase va textual, con quién y dónde, y se DICE. Lo único que
    el canal afirma del nivel 1 es que se dijo."""
    frase = schema.get("frase")
    frase = frase if isinstance(frase, dict) else {}
    out: list[str] = []
    if faltan := [c for c in ("texto", "quien", "donde") if not str(frase.get(c, "")).strip()]:
        out.append('falta en "_schema.frase": ' + ", ".join(faltan)
                   + ". La frase va textual, con quién la dijo y dónde: es lo único que el "
                     "canal afirma del nivel 1")
        return out
    dicho = _narrado(guion, PLANOS_DE_LA_CAUSA)
    if dicho and not _dice_algo_de(frase["texto"], dicho):
        out.append(f'la narración de {", ".join(PLANOS_DE_LA_CAUSA)} no dice la frase de '
                   f'"_schema.frase.texto" ("{str(frase["texto"])[:50]}"). Quien ve el video no '
                   "vio la polémica: si no se cita, no se entiende de qué va")
    elif dicho and _cuanto_dice(frase["texto"], dicho) < MINIMO_COMPLETA:
        # 27/10/2026: "vale más mi gato" sin "que sus desaparecidos" pasaba el criterio flojo.
        out.append(f'la frase va recortada en {", ".join(PLANOS_DE_LA_CAUSA)}: dila COMPLETA al '
                   f'menos una vez ("{str(frase["texto"])[:80]}"). Recortada no se entiende de qué va')
    return out


MINIMO_COMPLETA = 0.75


def _cuanto_dice(texto: str, dicho: str) -> float:
    """Qué parte de las palabras con carga de `texto` aparecen en `dicho`."""
    claves = _claves(texto)
    return sum(k in dicho for k in claves) / len(claves) if claves else 1.0


def problemas_de_que_paso(guion: dict, schema: dict, planos: tuple[str, ...],
                          minimo: float = 0.6) -> list[str]:
    """La prueba del que llega sin saber (27/10/2026): lo que pasó, dicho antes de los datos.
    La usa también la fórmula viral."""
    que_paso = str(schema.get("que_paso", "")).strip()
    if not que_paso:
        return []  # lo reporta CAMPOS (polémica) o la revisión viral
    dicho = _narrado(guion, planos)
    if dicho and _cuanto_dice(que_paso, dicho) < minimo:
        return [f'la narración de {", ".join(planos)} no cuenta qué pasó ("_schema.que_paso": '
                f'"{que_paso[:90]}"). Quien llega sin saber tiene que entenderlo antes de los datos']
    return []


def _problemas_de_la_reaccion(guion: dict, schema: dict) -> list[str]:
    """La respuesta es el nivel 2 de esta fórmula: va medida y va DICHA. Entra
    como hecho registrado ("ochocientas mil vistas le contestaron"), nunca como
    sentir ("la gente está indignada")."""
    reaccion = schema.get("reaccion")
    reaccion = reaccion if isinstance(reaccion, dict) else {}
    if not reaccion:
        return ['falta "_schema.reaccion": quién contestó, con qué cita textual, con cuántas '
                "vistas, quién se sumó y qué contestó quien dijo la frase. La respuesta es el "
                "nivel 2 de esta fórmula"]
    out: list[str] = []
    # "respuesta_del_senalado" es obligatoria y admite las dos verdades: la
    # disculpa o el silencio. Pedir "quién no ha contestado" obligaba a que
    # alguien callara: Los Parrilleros MX se disculparon un día después y el
    # guion se habría quedado sin final, o se lo habría inventado (17/10/2026).
    pedidos = ("quien", "cita", "numeros", "respuesta_del_senalado")
    if faltan := [c for c in pedidos if not str(reaccion.get(c, "")).strip()]:
        out.append('falta en "_schema.reaccion": ' + ", ".join(faltan)
                   + ('. "respuesta_del_senalado" es qué contestó quien dijo la frase, textual y '
                      "con fecha, o que no ha contestado y hasta cuándo lo revisaste: la "
                      "disculpa es un hecho y va en el video"
                      if "respuesta_del_senalado" in faltan else ""))
    numeros = str(reaccion.get("numeros", ""))
    if numeros.strip() and not re.search(r"\d", numeros):
        out.append('"_schema.reaccion.numeros" no trae cifra: la reacción va como hecho '
                   "registrado (vistas, comentarios, con su fecha), no como sentir. \"La gente "
                   "está indignada\" no es un dato")
    cita = str(reaccion.get("cita", ""))
    dicho = _narrado(guion)
    if cita.strip() and dicho and not _dice_algo_de(cita, dicho):
        out.append("la narración no dice nada de \"_schema.reaccion.cita\" "
                   f'("{cita[:50]}"). La respuesta se DICE, no se cuenta: en el guion del '
                   "Conalep la cita de la alumna se quedó en _schema.fuentes y la voz nunca la "
                   "pronunció, que era el video entero")
    return out


def _problemas_de_las_premisas(guion: dict, schema: dict) -> list[str]:
    """Las premisas del estigma, con su dato cada una.

    Son plural y NO se inventan: se sacan del rumor, y van con la fuente que
    prueba que se dicen (17/10/2026, Javier: "el dato no debe de ser verídico...
    tiene que ser sobre los rumores. hace unos años atrás se decía que tienen
    mala fama porque nacen pandilleros, las niñas se embarazan"). La primera
    versión del POC desempacó una sola premisa -"no tiene futuro laboral"- que
    nadie estaba discutiendo, y la contestó con las becas del sector privado.
    """
    premisas = schema.get("premisas") or []
    if isinstance(premisas, dict):
        premisas = [premisas]
    if not isinstance(premisas, list) or not premisas:
        return ['falta "_schema.premisas": la lista de lo que la mala fama DICE en concreto, y '
                'el dato de cada cosa. Cada entrada lleva {"dice", "fuente_del_rumor", "dato", '
                '"fuente_del_dato"}. No las inventes: sácalas del rumor, con la fuente que '
                "prueba que se dicen"]
    out: list[str] = []
    fuentes = schema.get("fuentes") or {}
    for i, premisa in enumerate(premisas):
        donde = f"_schema.premisas[{i}]"
        if not isinstance(premisa, dict):
            out.append(f"{donde} tiene que ser un objeto con "
                       + ", ".join(f'"{c}"' for c in PREMISA_CAMPOS))
            continue
        if faltan := [c for c in PREMISA_CAMPOS if not str(premisa.get(c, "")).strip()]:
            out.append(f"falta en {donde}: " + ", ".join(faltan))
        dice, dato = str(premisa.get("dice", "")).strip(), str(premisa.get("dato", "")).strip()
        for campo in ("fuente_del_rumor", "fuente_del_dato"):
            clave = str(premisa.get(campo, "")).strip()
            if clave and clave not in fuentes:
                out.append(f'{donde}.{campo} ("{clave[:40]}") no es una clave de '
                           "_schema.fuentes"
                           + (". El rumor también se prueba: hace falta el estudio, la encuesta "
                              "o la nota donde consta que ESO se dice"
                              if campo == "fuente_del_rumor" else ""))
        if not dice or not dato:
            continue
        # La clave de la fuente se quita antes de comparar: "anuario_conalep_2024"
        # dentro del dato hacía que CUALQUIER dato pareciera hablar del tema, y
        # el candado se cumplía con la cita en vez de con el dato (17/10/2026).
        limpio = _sin_claves_de_fuente(dato, fuentes)
        if not _dice_algo_de(dice, limpio) and not _dice_algo_de(limpio, dice):
            out.append(f'{donde}.dato no habla de lo que dice {donde}.dice ("{dice[:50]}"). El '
                       "dato contesta lo que el rumor DICE, no lo que te convenga: el POC "
                       "contestaba \"no tiene futuro laboral\" con las becas del sector privado "
                       "cuando la mala fama hablaba de embarazos y de asaltos")

    narrado = _narrado(guion, PLANOS_DEL_DATO)
    dichas = [p for p in premisas if isinstance(p, dict)
              and (_dice_algo_de(str(p.get("dice", "")), narrado)
                   or _dice_algo_de(_sin_claves_de_fuente(str(p.get("dato", "")), fuentes),
                                    narrado))]
    if narrado and not dichas:
        out.append(f'la narración de {", ".join(PLANOS_DEL_DATO)} no dice ninguna de las '
                   "premisas ni sus datos. Ahí va la cifra, contestando lo que la mala fama dice")
    return out


def _problemas_del_veredicto(guion: dict, schema: dict) -> list[str]:
    """Pieza 9 (Javier, 17/10/2026: "tienes que pedir la opinión de los que ven
    esa polémica"). Donde no hay fuente de la verdad, el veredicto es del
    público: va en pregunta, con los dos lados nombrados, y el canal no lo
    contesta."""
    veredicto = schema.get("veredicto")
    veredicto = veredicto if isinstance(veredicto, dict) else {}
    if not veredicto:
        return ['falta "_schema.veredicto": la pregunta con la que le pides su opinión a quien '
                've la polémica, con los dos lados nombrados ({"pregunta": "¿Fue humor o fue '
                'discriminación?", "lados": ["humor", "discriminación"]}). Donde no hay fuente '
                "de la verdad, el veredicto es del público"]
    out: list[str] = []
    pregunta = str(veredicto.get("pregunta", "")).strip()
    if not pregunta:
        out.append('falta "_schema.veredicto.pregunta"')
    elif "?" not in pregunta:
        out.append(f'"_schema.veredicto.pregunta" no es una pregunta ("{pregunta[:60]}"). El '
                   "canal no dictamina la polémica: la pregunta")
    lados = veredicto.get("lados") or []
    if isinstance(lados, str):
        lados = [lados]
    lados = [str(x).strip() for x in lados if str(x).strip()]
    if len(lados) < _MIN_LADOS:
        out.append(f'"_schema.veredicto.lados" tiene {len(lados)}: hacen falta {_MIN_LADOS}, y '
                   "los dos tienen que poder defenderlos alguien real. Un solo lado no es un "
                   "veredicto, es el canal opinando con signo de interrogación")
    dicho = _narrado(guion, PLANOS_DEL_VEREDICTO)
    if pregunta and dicho and not _dice_algo_de(pregunta, dicho):
        out.append("la narración de " + " o ".join(PLANOS_DEL_VEREDICTO) + " no pide el "
                   f'veredicto de "_schema.veredicto.pregunta" ("{pregunta[:50]}"). El video '
                   "cierra pidiendo la opinión de quien lo ve, no cerrando la polémica")
    return out


def _problemas_de_nombres(guion: dict, schema: dict) -> list[str]:
    """Lo que tiene nombre se dice con su nombre, y se DICE: enseñarlo en una
    captura no cuenta (MINISO, 16/10/2026)."""
    senalados = schema.get("senalados") or []
    if isinstance(senalados, str):
        senalados = [senalados]
    senalados = [str(s).strip() for s in senalados if str(s).strip()]
    if not senalados:
        return ['falta "_schema.senalados": a quién nombra el guion (quien dijo la frase, quien '
                "contestó, la institución, el documento). Fuera de los menores de edad no hay "
                "nombre que se calle"]
    dicho = _narrado(guion)
    if not dicho:
        return []
    if mudos := [s for s in senalados if _sin_acentos(s) not in dicho]:
        return ["la narración no dice estos nombres de _schema.senalados: " + ", ".join(mudos)
                + ". Enseñarlos en una captura no basta"]
    return []


def _problemas_del_check_final(guion: dict, schema: dict) -> list[str]:
    final = schema.get("verificacion_final")
    final = final if isinstance(final, dict) else {}
    out: list[str] = []
    datos = final.get("datos") or []
    if isinstance(datos, str):
        datos = [datos]
    if len(datos) < _MIN_DATOS:
        out.append(f'faltan renglones en "_schema.verificacion_final.datos" (hay {len(datos)}, '
                   f"mínimo {_MIN_DATOS}): cada cifra y cada fecha que dice la narración con la "
                   "clave de _schema.fuentes de donde sale")
    elif sueltos := [d for d in datos if not _cita_fuente(str(d), schema.get("fuentes") or {})]:
        out.append("estos renglones de _schema.verificacion_final.datos no nombran su clave de "
                   "_schema.fuentes: " + "; ".join(str(d)[:60] for d in sueltos))
    if not str(final.get("misma_historia", "")).strip():
        out.append('falta "_schema.verificacion_final.misma_historia": qué se dijo, quién '
                   "contestó y qué contesta el dato, en una línea")
    return out


def _problemas_de_hallazgo(schema: dict) -> list[str]:
    """Una polémica se descubre en la plataforma: lo que se busca es una
    publicación con muchas RESPUESTAS de gente aludida."""
    from dato_mata_gato_bot import instruccion_viral

    return instruccion_viral._problemas_de_hallazgo(schema)
