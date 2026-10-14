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
     "Una noticia de esta semana o este mes en Cancún o Quintana Roo que le afecte a casi "
     "cualquiera que vive ahí: el bolsillo (precios, recibos, gasolina, rentas), los servicios "
     "(agua, luz, transporte, salud, basura) o el entorno (playas, manglar, sargazo, laguna). Con "
     "un responsable claro (empresa, autoridad, constructora). El trasfondo: de dónde viene el "
     "problema (cuándo empezó, qué se prometió, qué pasó antes)."),
    ("cdmx", "Ciudad de México",
     "Una noticia de esta semana o este mes en la Ciudad de México que le toque a quien vive ahí "
     "(Metro, agua, colonias, sismos, transporte, precios), con su trasfondo histórico: el hecho "
     "del pasado de la ciudad que explica lo de hoy o que se repite."),
    ("terror", "Terror basado en hechos reales",
     "Una noticia reciente (un estreno, una serie, un aniversario, un hallazgo, un juicio) que "
     "conecte con el CASO REAL que inspiró una película o leyenda de terror. El trasfondo es el "
     "caso documentado: qué está probado y qué es leyenda, dicho así."),
    ("historia", "La historia de…",
     "Una noticia reciente de México que reabre un hecho histórico (un aniversario, un hallazgo, "
     "una ley, una demolición, un juicio). El título empieza con 'La historia de'. El trasfondo "
     "es el hecho histórico con sus fechas y nombres verificados."),
    ("marfil", "Secuestros y herederos (tipo Marfil)",
     "Una noticia reciente de un secuestro, una herencia en disputa o una familia poderosa, "
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
  2. ESTÁ PASANDO AHORITA (saliencia o actualidad: lo de ahorita pesa más que lo que pasará o
     ya pasó). Noticia de esta semana o de este mes, con fecha en la nota. Por eso Aguakan pegó
     y el subsidio de la luz no.
  3. ALGO NO CUADRA (brecha de curiosidad, Loewenstein 1994: cuando algo no cuadra, el cerebro
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
La narración le HABLA a esa persona: "tu recibo", "tu colonia", "si vives en…", "la próxima vez
que cargues gasolina…". El "te imaginas a quien…" de p01 es alguien como ella. El gancho (p00)
junta 1 y 3: el dato que la toca, con lo que no cuadra.
En "_schema.condiciones" escribe, una por una, cómo cumple el guion cada pieza (con la fecha
de la noticia en la 2). Un guion al que le falte una se descarta en la revisión.
En los temas que no son locales (terror, "la historia de", tipo Marfil), la 1 es que le toque a
quien vive en México hoy, y la 5 que haya un lugar, un objeto o un documento real que mostrar.

VERIFICACIÓN (lo más importante: si un dato no se puede verificar, NO va)
1. Busca la noticia reciente y ÁBRELA (WebFetch). No te quedes con el resumen del buscador:
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
- p02 "contexto", p03 "el_hecho", p04 "bucle_abierto", p05 "el_desenlace": la noticia con sus
  cifras y nombres, atribuidos.
- p06 "contexto": el TRASFONDO histórico (cuándo empezó, qué pasó antes).
- p07 "cierre_bucle": vuelve a la pregunta abierta, sin moraleja.
- p08 "identidad_cierre": "Aquí el dato mata al gato. ¿[pregunta al espectador sobre SU vida]?
  Cuéntamelo en los comentarios." Su visual: {"tipo": "grafico_movimiento", "descripcion":
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
  "_schema": {"descripcion": "Short de Dato Mata Gato, fórmula de cercanía: noticia reciente +
               trasfondo histórico.", "fuentes": {"precio": "URL (lo que dice)"},
              "condiciones": {"1_te_afecta": "Todo el que tiene coche o usa taxi en Cancún.",
                              "2_esta_pasando_ahorita": "PorEsto, 29/09/2026: la Magna llegó a 25.39.",
                              "3_algo_no_cuadra": "Hay un acuerdo para que no pase de 24 pesos y aquí cuesta 25.39.",
                              "4_coraje": "La gasolinera de la 20 de Noviembre tiene el margen más alto de 8 regiones, según Profeco.",
                              "5_se_puede_grabar": "Cualquier gasolinera de la avenida 20 de Noviembre."},
              "restriccion_etica": "Lo que no se usó y por qué."},
  "titulo": "Gasolina en Cancún", "gancho": "25.39 EL LITRO", "claves": ["gasolina", "magna"],
  "plus": {"mapa": {"plano": "p02", "consulta": "Avenida 20 de Noviembre, Cancún", "etiqueta": "AV. 20 DE NOVIEMBRE · CANCÚN"},
           "contradiccion": {"plano": "p04", "arriba": {"titulo": "EL ACUERDO", "renglones": ["Magna a menos de 24 pesos"]},
                             "abajo": {"titulo": "LO QUE PAGAS", "renglones": ["25.39 el litro en Cancún"]},
                             "abajo_en": "aquí", "resaltar": "25.39 el litro en Cancún", "fuente": "PorEsto, 29/09/2026"}},
  "hashtags": ["#DatoMataGato", "#Cancun", "#QuintanaRoo"],
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

"plus" (en la raíz del guion): tres animaciones que se arman con datos que YA están en el
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

AL TERMINAR responde SOLO este bloque JSON:
{"guiones": [{"slug": "...", "titulo": "...", "resumen_hechos": "2 líneas con los hechos y sus fuentes"}]}
""".strip()


HERRAMIENTAS = "C:/dato-mata-gato-bot/.venv/Scripts/python.exe -m dato_mata_gato_bot.herramientas_guion"

# Para la sesión ligera (13/10/2026). Medido en la fábrica: un guion daba 14 a
# 27 pasos, y cada paso relee todo lo acumulado. Se iban 6 pasos en buscar
# fotos de dos en dos y otros 6 en revisar y corregir con Edit tras Edit. Las
# reglas del guion no cambian: solo cómo se trabaja.
COMO_TRABAJAR = r"""
CÓMO TRABAJAR (cada respuesta tuya relee todo lo anterior: menos respuestas = menos costo)
- Junta en UNA respuesta todas las llamadas que no dependan entre sí: 3 o 4 búsquedas a la
  vez, y después 3 o 4 notas abiertas a la vez (WebFetch). No de una en una ni de dos en dos.
- Fotos de Wikimedia: NO las busques con WebFetch. Una sola llamada con Bash, con todas tus
  consultas juntas (te da nombre exacto, tamaño y descripción de cada archivo):
      <<H>> fotos "Avenida Tulum Cancún" "Laguna Nichupté" "Palacio Municipal Benito Juárez"
- Escribe el guion.json COMPLETO una sola vez (Write) y córrele la revisión automática:
      <<H>> revisar <slug>
  Revisa la fórmula, el largo, las frases, que las fotos existan, que el titular de cada
  nota nombre el caso y que "plus" cuadre con el guion. Si marca algo, corrige TODO en una sola reescritura (Write) y vuelve
  a correrla. No revises a mano con PowerShell ni corrijas con varios Edit.
- Meta: unas 10 respuestas por guion. La verificación NO se recorta: cada dato sigue
  saliendo de una nota que abriste.
""".replace("<<H>>", HERRAMIENTAS)


def instruccion(clave: str, n: int, ya_hechos: str, ligera: bool = False) -> str:
    tema = next(t for t in TEMAS if t[0] == clave)
    texto = (INSTRUCCION.replace("<<N>>", str(n)).replace("<<TEMA>>", tema[1])
             .replace("<<DESCRIPCION>>", tema[2]).replace("<<CLAVE>>", tema[0]))
    if ligera:
        texto = texto.replace(
            "(consulta https://commons.wikimedia.org/w/api.php?action=query&list=search&srnamespace=6&\n"
            "  srsearch=...&format=json)", "(búscalo con la herramienta de fotos, abajo)")
        texto = texto.replace("\nAL TERMINAR responde", COMO_TRABAJAR + "\nAL TERMINAR responde")
    return texto + "\n\nYA ESTÁN HECHOS -- no repitas ninguno: " + ya_hechos


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
