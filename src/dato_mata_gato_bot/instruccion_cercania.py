"""Fórmula de cercanía (la de los videos de Cancún) para la fábrica de lotes.

Sale de los videos que sí funcionaron publicados (11/10/2026): "cada vez menos
vuelos en Cancún", Aguakan y Punta Nizuc. Los tres le pegan al bolsillo o al
entorno de quien vive ahí y tienen un responsable claro. La estructura es la
de los generadores escritos a mano en clip_assistance/tools
(guiones_cancun_cercania*.py, guiones_historicos_cancun.py): noticia de esta
semana + trasfondo histórico + algo que el espectador siente que es suyo.

Javier pidió (12/10/2026) que los 1000 de la fábrica sigan esta fórmula y no la
de true crime, repartida en los temas que se trabajaron: Cancún, Ciudad de
México, terror, "la historia de" y casos tipo Marfil.
"""

TEMAS = [
    ("cancun", "Cancún y Quintana Roo",
     "Un tema de este mes en Cancún o Quintana Roo del que la gente está hablando y que le afecte a casi "
     "cualquiera que vive ahí: el bolsillo (precios, recibos, gasolina, rentas), los servicios "
     "(agua, luz, transporte, salud, basura) o el entorno (playas, manglar, sargazo, laguna). Con "
     "un responsable claro (empresa, autoridad, constructora). El trasfondo: de dónde viene el "
     "problema (cuándo empezó, qué se prometió, qué pasó antes)."),
    ("cdmx", "Ciudad de México",
     "Un tema de este mes en la Ciudad de México del que la gente está hablando y que le toque a quien vive ahí "
     "(Metro, agua, colonias, sismos, transporte, precios), con su trasfondo histórico: el hecho "
     "del pasado de la ciudad que explica lo de hoy o que se repite."),
    ("terror", "Terror basado en hechos reales",
     "Algo reciente que hace hablar (un estreno, una serie, un aniversario, un hallazgo, un juicio) que "
     "conecte con el CASO REAL que inspiró una película o leyenda de terror. El trasfondo es el "
     "caso documentado: qué está probado y qué es leyenda, dicho así."),
    ("historia", "La historia de…",
     "Algo reciente de México que reabre un hecho histórico y hace hablar (un aniversario, un hallazgo, "
     "una ley, una demolición, un juicio). El título empieza con 'La historia de'. El trasfondo "
     "es el hecho histórico con sus fechas y nombres verificados."),
    ("marfil", "Secuestros y herederos (tipo Marfil)",
     "Un caso reciente que hace hablar: un secuestro, una herencia en disputa o una familia poderosa, "
     "conectada con un caso histórico parecido y documentado (México primero; si es de fuera, "
     "muy conocido). Nunca víctimas menores de edad con nombre. Del acusado sin sentencia se "
     "dice el hecho procesal, no la culpa."),
]

INSTRUCCION = r"""
Vas a escribir <<N>> guiones de video corto (45 a 75 segundos) para el canal Dato Mata Gato,
tema: <<TEMA>>.

QUÉ BUSCAMOS
<<DESCRIPCION>>

LA FÓRMULA DEL CANAL: "LA CONTRADICCIÓN LOCAL"
    Te afecta + está pasando ahorita + algo no cuadra + coraje = retención y compartidos
Cada video se dirige a la persona que lo ve: tiene que sentir que es PARA ELLA. Es lo que le
funcionó al canal ("el aeropuerto de Cancún tuvo su día con menos vuelos en veinte años",
Aguakan: "votamos y sigue aquí", la tala en Punta Nizuc). Son cuatro efectos estudiados, y el
guion tiene que tener LOS CUATRO; si le falta uno, busca otro tema:
  1. TE AFECTA (efecto de autorreferencia: el cerebro atiende y recuerda lo que tiene que ver
     con uno mismo). Le pasa a casi cualquiera que vive ahí, sin importar de dónde vino: su
     recibo, su colonia, su camión, su playa. No solo a un gremio o a los turistas.
<<AHORITA>>  3. ALGO NO CUADRA (brecha de curiosidad, Loewenstein 1994: cuando algo no cuadra, el cerebro
     necesita cerrar el hueco). Una contradicción concreta: "votamos que se fuera y sigue aquí",
     "hay un acuerdo de 24 pesos y aquí pagas 25", "dicen que es vandalismo y la presidenta dice
     que fue una torre".
  4. CORAJE (indignación moral; Berger y Milkman 2012: el enojo y otras emociones de alta
     activación se comparten más que las tranquilas). Alguien con nombre o institución
     responsable que no cumplió, cobró de más, prometió y no hizo. El coraje sale de los HECHOS
     verificados, nunca de exagerarlos: no se inventan culpables, y un acusado sin sentencia se
     presenta como acusado.
  Y además: 5. SE PUEDE GRABAR O MOSTRAR: la colonia, el recibo, la calle, la gasolinera, la playa,
     el documento; algo real que cualquiera puede ir a ver.
  6. HACE HABLAR (obligatoria desde el 14/10/2026): un tema del que quien lo ve TIENE SU PROPIA
     EXPERIENCIA u opinión que contar: su trabajo, su sueldo, lo que le cobraron, su renta, su
     servicio. Es lo que más funcionó en el canal: "2000 despedidos" (la gente contó dónde la
     recortaron), la Terminal 2 que cobra de más, lo que cuesta abrir un negocio. Una noticia que
     nadie vivió en carne propia (la zorra con rabia) no hace hablar aunque sea fresca. Elige
     primero por esto y después por qué tan reciente es. En "6_hace_hablar" escribe qué
     experiencia va a contar la gente en los comentarios.
La narración le HABLA a esa persona: "tu recibo", "tu colonia", "si vives en…", "la próxima vez
que cargues gasolina…". El "te imaginas a quien…" de p01 es alguien como ella. El gancho (p00)
junta 1 y 3: el dato que la toca, con lo que no cuadra.
En "_schema.condiciones" escribe, una por una, cómo cumple el guion cada pieza (con la fecha
del dato en la 2). Un guion al que le falte una se descarta en la revisión.
En los temas que no son locales (terror, "la historia de", tipo Marfil), la 1 es que le toque a
quien vive en México hoy, y la 5 que haya un lugar, un objeto o un documento real que mostrar.

LO QUE SUMA (no es obligatorio, pero un guion que lo tiene vale más)
  7. VALOR PRÁCTICO (Berger, "Contagious": lo útil se comparte para ayudar a otros): algo que la
     persona puede hacer o revisar: "revisa esto en tu recibo", "aquí se reporta", "pregunta
     esto antes de comprar". Escríbelo en "_schema.condiciones.7_valor_practico".
  - "Lo que casi nadie sabe" (moneda social: se comparte lo que hace ver enterado al que lo
    comparte), dicho con hechos, no como promesa vacía.
  - El final pesa más que el resto (regla pico-final): p07 cierra con la frase más fuerte del
    video, nunca con una moraleja.

QUE ENVEJEZCA BIEN (el video se va a ver semanas o meses después, sobre todo por búsquedas)
  - En la NARRACIÓN no van palabras de tiempo relativo: hoy, ayer, mañana, anoche, esta semana,
    este mes, este año, la semana pasada, el pasado lunes, hace tres días. Se dice la fecha o el
    año ("en octubre de dos mil veintiséis", "desde dos mil diecisiete"), o "sigue" ("sigue sin
    abrir"). La fecha exacta de la nota va en texto_en_pantalla o en una ficha.
  - Una cifra que cambia (un precio, un conteo) va con su fecha: "en octubre llegó a…".
  - Amárralo a algo que regresa en la vida de quien lo ve (Berger: los disparadores mantienen
    vivo un tema): el recibo bimestral, la quincena, la temporada de huracanes o de sargazo, el
    regreso a clases, la temporada alta. Cada vez que regresa, el video vuelve a servir.
  - "titulo", texto_en_pantalla y hashtags llevan lo que la gente BUSCARÍA ("agua en Cancún",
    "Aguakan", "sargazo"), sin fechas.
  - En "_schema.vigencia" escribe "<<VIGENCIA>>".

VERIFICACIÓN (lo más importante: si un dato no se puede verificar, NO va)
1. Busca las notas del tema y ÁBRELAS (con el comando buscar; WebFetch solo si no lo tienes o no abre). No te quedes con el resumen del buscador:
   los resúmenes inventan cifras. Cada cifra, fecha y nombre del guion tiene que estar en
   una nota o documento que abriste y leíste.
2. Lo que solo dice UNA fuente va atribuido en la narración ("según PorEsto…"), también en el
   trasfondo. Las cifras de organizaciones civiles, activistas o empresas van SIEMPRE con su
   nombre ("según la organización Agua para Todos…"), aunque la cifra suene oficial.
3. Si dos fuentes no coinciden en un dato, no lo uses, o di lo que sí coincide.
4. Anota en "_schema.fuentes" cada URL con lo que dice (qué cifra o hecho sale de ahí), y en
   "_schema.restriccion_etica" lo que decidiste NO usar y por qué.
5. Menores de edad: no se nombran (víctimas ni acusados). Acusado sin sentencia: se dice el
   hecho procesal ("la fiscalía lo acusó de…"), no la culpa.
6. No repitas ninguno de los que YA ESTÁN HECHOS (lista al final).

ESTRUCTURA (9 planos, ids p00 a p08)
- p00 "gancho_hablado": MÁXIMO 12 PALABRAS. El dato que duele va PRIMERO. NINGÚN año ni fecha
  dichos (van en texto_en_pantalla o en p01). Que tenga una contradicción o algo sin explicar.
  Bien: "En Cancún pagas la gasolina más cara que en Monterrey. Y hay un acuerdo para que no pase."
- p01 "hook_tercera_persona": "Te imaginas a quien [vive aquí y le pasa esto]…" (una sola vez).
- DOS PREGUNTAS directas a quien ve, sobre SU caso (no se responden en el video: la piensa y la
  contesta en los comentarios). Una antes del segundo diez, en p01 o p02 ("¿A ti ya te
  cobraron eso?", "¿Sabes cuánto pagas tú?"), y otra a la mitad, en p03, p04 o p05 ("¿Tú
  hubieras firmado?"). Cortas, con "¿…?", y le hablan de tú. Enganchan: la persona se
  pregunta por su propio caso y se queda a ver qué pasa.
- p02 "contexto": el TRASFONDO histórico, corto (cuándo empezó, qué pasó antes). Va AQUÍ,
  temprano, y no al final: la historia después de que el tema ya se resolvió es donde la
  gente se va.
- p03 "el_hecho", p04 "bucle_abierto": el tema con sus cifras y nombres, atribuidos. p04
  deja la pregunta abierta.
- p05 "escalada": NO resuelve. Suma lo que lo empeora o lo complica (otro dato, otra
  fecha, quién más está metido) y termina con una frase que pide seguir viendo.
- p06 "la_revelacion": el dato más fuerte, guardado para el final (narración inversa): lo
  que casi nadie sabe, el documento que lo prueba, la cifra que no cuadra. Verificado y
  atribuido como todo lo demás.
- p07 "cierre_bucle": vuelve a la pregunta abierta y cierra con la frase más fuerte, sin moraleja.
- p08 "identidad_cierre": "Aquí el dato mata al gato. ¿[pregunta al espectador sobre SU vida]?
  Cuéntamelo en los comentarios." La pregunta pide SU caso concreto, no una opinión general:
  "¿En qué hotel trabajabas y te pasó?", no "¿Qué opinas?". Su visual: {"tipo": "grafico_movimiento", "descripcion":
  "Cartel de cierre del canal.", "prompt_ia": "", "busqueda_medios": ""}.
Reglas de la narración: español de México, de tú. Ninguna frase pasa de 20 palabras. Números
y años en palabras ("mil novecientos setenta", "veinticinco pesos con treinta y nueve").
Máximo DOS nombres propios por frase (con más, la voz se come uno). Nada de palabras que
empiecen con "Tl" (Tlalpan, Tlaxcala): la voz no puede decirlas; van en texto_en_pantalla.
En los primeros tres planos tiene que aparecer el lugar exacto ("en Cancún", "en la colonia
Guerrero"), no solo el estado. Total: 120 a 190 palabras.

EVIDENCIA REAL (sin imágenes de IA: el video falla si no hay evidencia)
"evidencia" es una lista; cada plano (p00 a p07) lleva en visual.evidencia 1 a 3 ids de ella.
Mínimo TRES piezas reales (prensa, documento, lugar o persona) más 2 o 3 fichas. Tipos:
- {"id": "e1", "tipo": "prensa", "url": "...", "fuente": "Medio, DD/MM/AAAA"}: se captura el
  TITULAR, así que el titular tiene que mencionar el caso (un nombre o lugar del guion). Para
  PorEsto usa la versión .amp.html de la URL.
- {"id": "e2", "tipo": "documento", "url": "...", "fuente": "..."}: una página oficial; para
  un PDF agrega "pagina": n y, si el dato está a media página, "desde": 0.6, "fraccion": 0.85.
- {"id": "e3", "tipo": "lugar" | "persona", "wikimedia": "File:Nombre exacto.jpg"}: el nombre
  EXACTO de un archivo de Wikimedia Commons que verificaste que existe y muestra lo que dices
  (consulta https://commons.wikimedia.org/w/api.php?action=query&list=search&srnamespace=6&
  srsearch=...&format=json). NO uses "buscar_wikimedia": la búsqueda automática se equivocó
  en 7 de 20 fotos (un "Metro Viaducto" que era un tren de España, un "Reclusorio" que eran
  políticos). Si no hay foto buena, mejor otra nota de prensa.
- {"id": "f1", "tipo": "ficha", "titulo": "...", "renglones": ["...", "..."], "fuente": "..."}:
  una tarjeta con 2 a 4 datos clave y su fuente.
Cada plano de p00 a p07 lleva "motion": "calm" en su visual.

FORMATO DE CADA GUION
Escríbelo en C:\Android_in\<slug>\guion.json, con slug "guion-<<CLAVE>>-" + palabras cortas
del tema (minúsculas y guiones). Así, como en este ejemplo real (recortado a 2 planos):
{
  "_schema": {"descripcion": "Short de Dato Mata Gato, fórmula de cercanía: tema que hace hablar +
               trasfondo histórico.", "fuentes": {"precio": "URL (lo que dice)"},
              "condiciones": {"1_te_afecta": "Todo el que tiene coche o usa taxi en Cancún.",
                              "2_esta_pasando_ahorita": "PorEsto, 29/09/2026: la Magna llegó a 25.39.",
                              "3_algo_no_cuadra": "Hay un acuerdo para que no pase de 24 pesos y aquí cuesta 25.39.",
                              "4_coraje": "La gasolinera de la 20 de Noviembre tiene el margen más alto de 8 regiones, según Profeco.",
                              "5_se_puede_grabar": "Cualquier gasolinera de la avenida 20 de Noviembre."},
              "restriccion_etica": "Lo que no se usó y por qué."},
  "titulo": "Gasolina en Cancún", "gancho": "25.39 EL LITRO", "claves": ["gasolina", "magna"],
  "descripcion": "La gasolina en Cancún cuesta más que en Monterrey aunque hay un acuerdo para que no pase de 24 pesos. Profeco lo midió. ¿A cuánto cargaste tú?",
  "plus": {"mapa": {"plano": "p02", "consulta": "Avenida 20 de Noviembre, Cancún", "etiqueta": "AV. 20 DE NOVIEMBRE · CANCÚN"},
           "contradiccion": {"plano": "p04", "arriba": {"titulo": "EL ACUERDO", "renglones": ["Magna a menos de 24 pesos"]},
                             "abajo": {"titulo": "LO QUE PAGAS", "renglones": ["25.39 el litro en Cancún"]},
                             "abajo_en": "aquí", "resaltar": "25.39 el litro en Cancún", "fuente": "PorEsto, 29/09/2026"}},
  "hashtags": ["#Cancun", "#Gasolina", "#Profeco", "#QuintanaRoo", "#DatoMataGato"],
  "evidencia": [
    {"id": "e1", "tipo": "prensa", "url": "https://www.poresto.com/....amp.html", "fuente": "PorEsto, 29/09/2026"},
    {"id": "e4", "tipo": "lugar", "wikimedia": "File:Avenida Tulum, Cancun, Quintana Roo, Mexico 2021.jpg"},
    {"id": "f1", "tipo": "ficha", "titulo": "Septiembre de 2026 · Cancún",
     "renglones": ["Magna: 25.39 pesos por litro", "El margen más alto de 8 regiones"], "fuente": "Profeco, vía PorEsto"}
  ],
  "planos": [
    {"id": "p00", "seccion": "gancho_hablado",
     "narracion": "En Cancún pagas la gasolina más cara que en Monterrey. Y hay un acuerdo para que no pase.",
     "visual": {"tipo": "archivo_historico", "evidencia": ["f1", "e1"], "prompt_ia": "", "busqueda_medios": "", "motion": "calm"},
     "texto_en_pantalla": "25.39 EL LITRO"},
    {"id": "p08", "seccion": "identidad_cierre",
     "narracion": "Aquí el dato mata al gato. ¿A cuánto cargaste esta semana? Cuéntamelo en los comentarios.",
     "visual": {"tipo": "grafico_movimiento", "descripcion": "Cartel de cierre del canal.", "prompt_ia": "", "busqueda_medios": ""},
     "texto_en_pantalla": "¿A CUÁNTO CARGASTE?"}
  ]
}
"claves": 1 a 3 palabras que el titular de cada nota de prensa contiene (sin acentos sirve).
"texto_en_pantalla": 2 a 5 palabras en mayúsculas.

"plus" (en la raíz del guion): animaciones que se arman con datos que YA están en el
guion y ya verificaste. NADA nuevo: cada cifra y cada frase tiene que estar en la narración
o en una ficha. Si una no aplica, omítela (no la inventes).
  "contador": la cifra del gancho, si p00 dice una: {"numero": 40, "antes": "HASTA",
     "despues": "BEBÉS AL DÍA"} ("antes" puede ir vacío; "despues" de 1 a 4 palabras).
  "mapa": el lugar exacto, para buscarlo en OpenStreetMap: {"plano": "p02", "consulta":
     "Supermanzana 65, Cancún", "etiqueta": "SUPERMANZANA 65 · CANCÚN"}. "plano" es donde la
     voz nombra el lugar; "consulta" como se buscaría en un mapa (colonia, supermanzana,
     calle o edificio, y la ciudad).
  "contradiccion": lo que no cuadra, en dos bloques, en el plano donde la voz lo cuenta:
     {"plano": "p04", "arriba": {"titulo": "LO QUE PROMETIERON", "renglones": ["...", "..."]},
      "abajo": {"titulo": "LO QUE HAY HOY", "renglones": ["...", "..."]}, "abajo_en": "anuncios",
      "resaltar": "Sin fecha de apertura", "fuente": "Medio o institución, DD/MM/AAAA"}
     2 o 3 renglones cortos por bloque (máximo 36 letras cada uno). "abajo_en": la palabra
     de la narración de ESE plano donde empieza la parte de abajo. "resaltar": un renglón
     de "abajo", copiado igual.
  "archivo": 1 o 2 búsquedas EN INGLÉS para tomas de video de archivo del lugar (Pexels):
     ["Cancun beach", "Playa del Carmen street"]. Solo ambiente del lugar, nunca personas
     del caso: en pantalla salen marcadas como archivo.
  "portada" (SIEMPRE): el texto de la portada del perfil, fondo oscuro y letra gigante:
     {"texto": "EL LITRO MÁS CARO", "resalta": "MÁS CARO"}. "texto": de 3 a 5 palabras en
     mayúsculas que den ganas de abrir el video (la contradicción, no el resumen; nada de
     "400 MIL VISTAS" ni nombres de medios). "resalta": 1 o 2 palabras de "texto", copiadas
     igual, que salen en amarillo (la cifra o la palabra que pica). Tiene que ser verdad
     con lo que ya está en el guion.

AL TERMINAR responde SOLO este bloque JSON:
{"guiones": [{"slug": "...", "titulo": "...", "resumen_hechos": "2 líneas con los hechos y sus fuentes"}]}
""".strip()


HERRAMIENTAS = "C:/dato-mata-gato-bot/.venv/Scripts/python.exe -m dato_mata_gato_bot.herramientas_guion"
BUSCAR = "C:/dato-mata-gato-bot/.venv/Scripts/python.exe -m dato_mata_gato_bot.expediente buscar"

# Para la sesión ligera (13/10/2026). Medido en la fábrica: un guion daba 14 a
# 27 pasos, y cada paso relee todo lo acumulado. Se iban 6 pasos en buscar
# fotos de dos en dos y otros 6 en revisar y corregir con Edit tras Edit. Las
# reglas del guion no cambian: solo cómo se trabaja.
PUBLICAR = r"""

PARA PUBLICAR Y PARA EL GANCHO (20/10/2026; va en las tres fórmulas)
- "descripcion" (en la raíz del guion, obligatoria): 2 o 3 frases para la descripción de
  TikTok, con las palabras que la gente teclearía en el buscador (el lugar, la institución o
  la empresa, el término de todos los días: "recibo de agua", "gasolina", "IMSS") y al final
  la misma pregunta del p08. Sin fechas relativas. Sin hashtags (esos van aparte).
- "hashtags": de 4 a 5. Uno del lugar, uno del tema, uno de la institución o el nombre del
  caso, uno del nicho (#NoticiasCancun, #QuintanaRoo, #Mexico…) y #DatoMataGato. Nada de
  #fyp, #viral ni #parati.
- El visual de p00 es lo primero que se ve: elige la evidencia más fuerte y que se lea sola
  (la ficha con la cifra, el titular, el documento). Evita en p00 clips o fotos que traigan
  su propio texto quemado: chocan con los subtítulos y no se lee ninguno de los dos.

CÓMO SUENA (español de México, no de noticiero ni de doblaje; 20/10/2026)
- Cuéntalo como un mexicano se lo cuenta a un compa: frases que se enganchan con
  conectores ("y ojo", "fíjate", "pero aquí viene lo bueno", "¿y sabes qué?", "nada más"),
  no una lista de oraciones sueltas.
- Palabras de aquí cuando salgan solas: lana, chamba, camión, colonia, banqueta, cuate,
  "¿a poco?", "neta". Una o dos por guion bastan; no metas slang en cada frase. Groserías no.
- Nada de España: ni "vale", "coger", "móvil", "ordenador", "guay", "vosotros", "aparcar",
  "chaval", "zumo", ni verbos con "-áis/-éis".
- Nada de giros de traducción: "los llegados del extranjero" es "los que llegaron de fuera";
  "volvieron el insulto una clase" es "convirtieron el insulto en una clase".
  Mal:  "El censo del INEGI dice otra cosa. Los llegados del extranjero fueron cuarenta y
         nueve mil."
  Bien: "Y fíjate lo que dice el censo del INEGI: en cinco años llegaron cuarenta y nueve mil
         extranjeros. Nada más."

CÓMO SE PREGUNTA (21/10/2026: la voz solo sube el tono en las preguntas de sí o no)
- Toda pregunta que se le hace a quien ve es de SÍ O NO: "¿A ti ya te lo dijeron?",
  "¿Tú crees que fue discriminación?", "¿Te ha pasado en tu colonia?".
- NUNCA "¿A o B?" ni una pregunta que empiece con "o": la voz la lee como opción, baja el
  tono al final y no suena a pregunta. Si hay dos lados, van en dos preguntas de sí o no:
  Mal:  "¿Fue un pleito de banqueta o fue discriminación?"
  Bien: "¿Fue un pleito de banqueta? ¿Tú crees que fue discriminación?"

ANTES DE ESCRIBIR CADA GUION (valida primero, escribe después)
- Cuando tengas un tema, confirma que tiene TODAS las piezas obligatorias de esta fórmula,
  cada una con su fuente abierta y leída. Si le falta una, descártalo AHÍ MISMO y busca otro,
  antes de armar evidencia y planos: un guion escrito sobre un tema incompleto es trabajo
  tirado.
- Entrega SIEMPRE los guiones pedidos. Nunca termines preguntando ni ofreciendo opciones
  ("¿quieres que escriba el otro?"): nadie va a contestar. Si ya tienes un reemplazo
  investigado, escríbelo. Solo si de verdad no hay más temas que cumplan, entrega los que sí
  y di en una línea por qué.
"""

COMO_TRABAJAR = r"""
CÓMO TRABAJAR (cada respuesta tuya relee todo lo anterior: menos respuestas = menos costo)
- Junta en UNA respuesta todas las llamadas que no dependan entre sí: 3 o 4 a la vez, no de
  una en una ni de dos en dos.
- Para LEER notas y documentos (también PDF oficiales) usa buscar, no WebFetch: baja las
  páginas fuera de tu cuota y te regresa solo los datos que contestan tu pregunta, cada uno
  con su cita ya comprobada palabra por palabra (✔) y su liga. Con ligas lee ésas; sin ligas
  busca en la web. Una pregunta concreta por llamada, varias llamadas en la misma respuesta:
      <<B>> "porcentaje de personas discriminadas según la ENADIS 2022" https://www.inegi.org.mx/...
      <<B>> "cuántas colonias se quedaron sin agua en Cancún esta semana"
  Lo que trae ✔ cuenta como nota abierta y leída. Si sin ligas no encuentra, busca la liga
  con WebSearch y pásasela. WebFetch solo para una liga que buscar no pudo abrir. NUNCA bajes páginas con curl ni las recortes con sed o pdftotext: cada página
  mete 5-10 mil letras que se releen en todos tus pasos (era el 36 % del gasto).
- Fotos de Wikimedia: NO las busques con WebFetch. Una sola llamada con Bash, con todas tus
  consultas juntas (te da nombre exacto, tamaño y descripción de cada archivo):
      <<H>> fotos "Avenida Tulum Cancún" "Laguna Nichupté" "Palacio Municipal Benito Juárez"
- Escribe el guion.json COMPLETO una sola vez (Write) y córrele la revisión automática:
      <<H>> revisar <slug>
  Revisa la fórmula, el largo, las frases, que las fotos existan, que el titular de cada
  nota nombre el caso y que "plus" cuadre con el guion. Si marca algo, corrige TODO con Edit,
  todos los Edit en la MISMA respuesta, y vuelve a correrla. No revises a mano con PowerShell.
- Meta: unas 10 respuestas por guion. La verificación NO se recorta: cada dato sigue
  saliendo de una nota que abriste.
""".replace("<<H>>", HERRAMIENTAS).replace("<<B>>", BUSCAR)


# La pieza 2 cambia según el tipo de video (Javier, 14/10/2026): 3 de cada 5 son
# "conversacion" y 2 perennes, que siguen siendo verdad en meses. Desde el 14/10 ya
# no hay noticias (Javier): "conversacion" es un tema que está pasando y hace hablar, con dato de este mes (ya
# no lo más nuevo de dos días): "2000 despedidos" fue lo que más conversación dio.
VIGENCIAS = ("conversacion", "perenne")
MEZCLA = {"conversacion": 3, "perenne": 2}
# Para mostrar: singular y plural.
NOMBRES = {"conversacion": ("conversación", "conversaciones"), "perenne": ("perenne", "perennes")}
DIAS_NOTICIA = 30  # "dato de este mes"; antes 2 días (14/10), Javier lo relajó ese mismo día

_AHORITA = {
    None: """  2. ESTÁ PASANDO AHORITA (saliencia o actualidad: lo de ahorita pesa más que lo que pasará o
     ya pasó). Noticia de esta semana o de este mes, con fecha en la nota. Por eso Aguakan pegó
     y el subsidio de la luz no.
""",
    "conversacion": """  2. ESTÁ PASANDO AHORITA (saliencia o actualidad: lo de ahorita pesa más que lo que pasará o
     ya pasó). Un tema que ESTÁ PASANDO y del que la gente ESTÁ HABLANDO, con un dato de este
     mes: fecha en la nota del <<DESDE>> o después. No tiene que ser la nota más nueva (Javier,
     14/10/2026: "ya no tanto por noticia"): vale más uno que hace hablar (pieza 6) que uno de
     ayer. Para saber de qué se habla: lo más comentado o compartido, lo que publicaron varios
     medios, lo que la gente reclama. En "_schema.impacto" anota de dónde sale que la gente
     está hablando de esto ("la publicaron Noticaribe, PorEsto y Novedades", "lo más comentado
     de PorEsto"). Por eso Aguakan pegó y el subsidio de la luz no.
""",
    "perenne": """  2. SIGUE PASANDO (saliencia sin caducidad): un problema que lleva tiempo y que en seis meses
     seguirá siendo verdad, con su historia y sus fechas ("la concesión vence en dos mil
     cincuenta y tres", "lleva nueve años cerrado"). Si hay una noticia reciente, sirve de
     excusa, pero el video no depende de ella. En la 2 de "_schema.condiciones" escribe por
     qué seguirá vigente y la fecha del dato más reciente.
""",
}


def repartir_vigencias(n: int, conteo: dict[str, int] | None = None) -> list[tuple[str, int]]:
    """n guiones repartidos 3 de conversación : 2 perennes, compensando lo que ya hay
    (como `repartir` con los temas). 5 -> 3 + 2; 1 -> el que vaya atrás."""
    cuenta = {v: (conteo or {}).get(v, 0) for v in VIGENCIAS}
    pedidos = {v: 0 for v in VIGENCIAS}
    for _ in range(n):
        total = sum(cuenta.values()) + sum(pedidos.values()) + 1
        v = max(VIGENCIAS, key=lambda x: MEZCLA[x] * total / sum(MEZCLA.values()) - cuenta[x] - pedidos[x])
        pedidos[v] += 1
    return [(v, k) for v, k in pedidos.items() if k]


def instruccion(clave: str, n: int, ya_hechos: str, ligera: bool = False,
                vigencia: str | None = None, hoy=None) -> str:
    from datetime import date, timedelta

    tema = next(t for t in TEMAS if t[0] == clave)
    desde = (hoy or date.today()) - timedelta(days=DIAS_NOTICIA)
    texto = (INSTRUCCION.replace("<<AHORITA>>", _AHORITA[vigencia]).replace("<<DESDE>>", f"{desde:%d/%m/%Y}")
             .replace("<<VIGENCIA>>", vigencia or "conversacion o perenne")
             .replace("<<N>>", str(n)).replace("<<TEMA>>", tema[1])
             .replace("<<DESCRIPCION>>", tema[2]).replace("<<CLAVE>>", tema[0]))
    if ligera:
        texto = texto.replace(
            "(consulta https://commons.wikimedia.org/w/api.php?action=query&list=search&srnamespace=6&\n"
            "  srsearch=...&format=json)", "(búscalo con la herramienta de fotos, abajo)")
        texto = texto.replace("\nAL TERMINAR responde", COMO_TRABAJAR + "\nAL TERMINAR responde")
    return texto + PUBLICAR + "\n\nYA ESTÁN HECHOS -- no repitas ninguno: " + ya_hechos


def repartir(n: int, conteo: dict[str, int] | None = None) -> list[tuple[str, int]]:
    """n guiones para los temas que van más atrás en el lote.

    Por conteo real y no por turno (12/10/2026): en el piloto, una tanda cortada
    por la cuota hizo que la siguiente volviera a empezar por Cancún, y terror,
    "la historia de" y Marfil se quedaron sin ninguno.
    """
    cuenta = {clave: (conteo or {}).get(clave, 0) for clave, _, _ in TEMAS}
    pedidos = {clave: 0 for clave in cuenta}
    orden = [clave for clave, _, _ in TEMAS]
    for _ in range(n):
        clave = min(orden, key=lambda c: (cuenta[c] + pedidos[c], orden.index(c)))
        pedidos[clave] += 1
    return [(c, k) for c, k in pedidos.items() if k]


def tema_de(slug: str) -> str | None:
    """'guion-cdmx-socavones' -> 'cdmx'."""
    partes = slug.split("-")
    return partes[1] if len(partes) > 2 and any(partes[1] == t[0] for t in TEMAS) else None
