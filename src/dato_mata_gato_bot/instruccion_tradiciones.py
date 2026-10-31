"""Nicho "EL PORQUÉ DE LAS TRADICIONES" (30/10/2026): una pregunta sobre un objeto
de una tradición mexicana, la respuesta que sorprende, dos giros (el origen y
la historia de fondo), la idea que lo cambia todo, de vuelta al objeto, y
"mándaselo a…". Sale del reel de @ingenioculto sobre el pan de muerto (43 mil
likes) y del POC del cempasúchil (clip_assistance/analisis/nicho_tradiciones).

No lleva evidencia ni planos: el video es 3D hecho con código
(illustrated-narrator/tradiciones_3d), y Claude escribe, además del texto, qué
se ve en cada escena con los objetos de CATALOGO. Si un prop o un objeto no está
aquí, la revisión lo rechaza: el render no sabría dibujarlo.

Datos: lo que tiene fuente es hecho; el saber popular sin evidencia fuerte se
dice ATRIBUIDO ("dicen que…", Javier 30/10/2026), no se quita; lo que se sabe
que es falso no entra.
"""

import difflib
import json
import re
from pathlib import Path

# Objeto -> (qué es, {prop: qué hace}). Lo mismo que dibuja tradiciones_3d/src/Objetos.tsx.
CATALOGO = {
    "Flor": ("pompón de pétalos (cempasúchil, flor de ofrenda); centro en 0,0,0, radio ~1, tallo abajo",
             {"paleta": "naranja|amarillo|magenta|rojo|blanco|morado", "brillo": "0-1", "giro": "radianes",
              "explota": "0-1: se separa en florecitas", "deshoje": "0-1: los pétalos caen al piso y forman un camino",
              "tallo": "true|false", "n": "número de pétalos (340)", "semilla": "texto: otra flor distinta"}),
    "Corona": ("florecitas que giran alrededor del centro (\"muchas\", \"cada una\")",
               {"cantidad": "6", "radio": "[x, y] (1.05, 1.75)", "velocidad": "0.35", "tamano": "0.13",
                "brillo": "0-1", "paleta": "como Flor"}),
    "Modelo": ("un modelo de la BIBLIOTECA (lista abajo), estilo juguete; se apoya en y = 0 (con Piso, "
               "posicion y = -1.6)",
               {"modelo": "nombre de la biblioteca, p. ej. food/corn", "alto": "altura en unidades (la Flor mide 2; "
                "una vela 0.4, un elote 0.4, un altar 0.8, el esqueleto 1.8)", "brillo": "0-1", "giro": "radianes"}),
    "Forma": ("una primitiva SOLO para detalles chicos (un papelito, una línea de luz, una base): máximo 2 por "
              "escena y nunca el protagonista",
              {"forma": "esfera|caja|cilindro|cono|capsula|dona|plano", "color": "#hex",
               "tamano": "número o [x, y, z]: la medida TOTAL (una esfera de tamano 1 mide 1 de ancho, o sea "
                         "radio 0.5; la Flor mide 2). Lo que va pegado a la superficie se pone a la mitad del "
                         "tamano desde el centro", "brillo": "0-1", "opacidad": "0-1", "giro": "radianes"}),
    "Particulas": ("chispas que suben ondulando: aroma, humo de copal, vapor, espíritu",
                   {"fuerza": "0-1", "color": "#hex", "cantidad": "70", "alto": "3.2", "ancho": "0.9"}),
    "Sol": ("halo de luz grande detrás de todo (\"como un pedazo de sol\")", {"fuerza": "0-1", "color": "#hex"}),
    "Calendario": ("rueda de casillas con una marcada (veintenas, meses, días)",
                   {"casillas": "18", "marcada": "índice de la casilla", "marca": "0-1: qué tanto brilla la marcada",
                    "giro": "radianes", "color": "#hex"}),
    "Lluvia": ("lluvia", {"fuerza": "0-1"}),
    "Campo": ("campo de flores que brota del piso (va con Piso y cámara campo)", {"crece": "0-1", "paleta": "como Flor"}),
    "Huevo": ("huevo estrellado; la yema se pinta con lo que le cae de arriba", {"pinta": "0-1"}),
    "Raices": ("corte de tierra con raíces que sueltan algo y gusanitos que se alejan", {"sustancia": "0-1"}),
    "Camino": ("camino de pétalos en el piso, de enfrente al fondo (z = -7); va con Piso",
               {"brillo": "0-1", "hasta": "0-1: cuánto del camino se ve", "paleta": "como Flor"}),
    "Ofrenda": ("altar de tres escalones con velas y flores, al fondo (z = -7); va con Piso y cámara recorre o eleva",
                {"paleta": "como Flor"}),
    "Velas": ("fila de velas encendidas", {"cantidad": "5", "fuerza": "0-1 (0 = apagadas)", "separacion": "0.5"}),
    "PapelPicado": ("tira de banderitas de papel picado que ondean",
                    {"cantidad": "7", "colores": "lista de #hex", "ondea": "0-1"}),
    "Piso": ("piso oscuro a y = -1.6", {"color": "#hex"}),
}
# La biblioteca de modelos (Kenney, CC0, estilo juguete; Javier lo escogió el 30/10/2026):
# la arma tradiciones_3d/scripts/biblioteca.py. {"food/corn": "elote", ...}
MODELOS_INDICE = Path(r"C:\illustrated-narrator\tradiciones_3d\public\modelos\indice.json")
# Lo que puede ser el objeto protagonista además de un Modelo: lo hecho por código y bien detallado.
PROTAGONISTAS = {"Flor": "flor de cempasúchil (o de otro color)", "PapelPicado": "papel picado",
                 "Velas": "velas encendidas", "Ofrenda": "ofrenda de tres escalones"}
MAX_FORMAS = 2


def modelos() -> dict[str, str]:
    try:
        return json.loads(MODELOS_INDICE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def protagonistas() -> dict[str, str]:
    """Todo lo que puede protagonizar un video: {"Flor": "...", "Modelo:food/corn": "elote", ...}."""
    return {**PROTAGONISTAS, **{f"Modelo:{k}": v for k, v in modelos().items()}}


# Todos los objetos aceptan estos, además de los suyos.
COMUNES = {"posicion": "[x, y, z]", "escala": "número", "rotacion": "[x, y, z] en radianes",
           "gira": "vueltas por segundo en radianes (0.3 = gira despacio)"}
CAMARAS = {
    "frente": "de frente al objeto, quieta", "acerca": "se acerca despacio al objeto",
    "aleja": "se aleja a la mitad de la escena", "cerca": "close-up, un poco abajo (raíces, detalle)",
    "plano": "de frente, recta (calendario, objetos planos)", "arriba": "desde arriba, como sobre una mesa",
    "campo": "alta, mirando al piso (Campo, Lluvia)", "suelo": "baja, mirando al piso enfrente (deshoje)",
    "recorre": "viaja por el piso hacia el fondo, a la Ofrenda", "eleva": "sube y se aleja desde la Ofrenda",
    "orbita": "rodea el objeto",
}
# Los 9 tiempos de la fórmula, en orden. giro_historia puede ir en dos escenas.
TIEMPOS = ("pregunta", "respuesta", "giro_origen", "giro_historia", "idea", "rasgos", "cierre_redondo",
           "presente", "mandar")
RESPALDOS = ("hecho", "saber_popular", "cuento", "sin_dato")


def _catalogo() -> str:
    lineas = []
    for nombre, (que, props) in CATALOGO.items():
        lineas.append(f'  - {nombre}: {que}. ' + ", ".join(f"{k} ({v})" for k, v in props.items()))
    lineas.append("  Todos aceptan además: " + ", ".join(f"{k} ({v})" for k, v in COMUNES.items()))
    por_paquete: dict[str, list[str]] = {}
    for nombre, que in modelos().items():
        por_paquete.setdefault(nombre.split("/")[0], []).append(f"{nombre} ({que})")
    lineas.append("BIBLIOTECA (para Modelo):")
    lineas += [f"  {', '.join(v)}" for v in por_paquete.values()]
    return "\n".join(lineas)


INSTRUCCION = r"""
Vas a escribir <<N>> guiones de video corto (55 a 75 segundos) para el canal Dato Mata Gato, con
la fórmula "EL PORQUÉ DE LAS TRADICIONES".

EL TEMA
<<TEMA>>

DE QUÉ VA
Una pregunta sobre UN objeto de una tradición mexicana ("¿Por qué el pan de muerto lleva
huesitos?", "¿Por qué ponemos cempasúchil?") y la historia que nadie te contó, contada como
cuento. Un objeto protagonista que abre el video, regresa a la mitad y lo cierra; todo lo demás
es un desvío que vuelve a él. Es cuento, no noticia: nada de fechas de publicación ni fuentes
en la voz.

LOS 9 TIEMPOS (cada escena lleva "tiempo"; los 9 tienen que estar, en este orden)
- pregunta (0-2 s): la pregunta sobre el objeto, con el objeto en pantalla desde el cuadro 0.
- respuesta (3-11 s): la respuesta que sorprende, de inmediato, sin rodeos.
- giro_origen: el origen que no esperas ("pero el pan no es de aquí", de dónde sale el nombre).
- giro_historia (una o dos escenas): el mito o la historia de fondo, contado como cuento.
- idea: la frase que lo cambia todo, corta ("un hueso no era el final, era una semilla").
- rasgos: de vuelta al objeto, qué significa cada rasgo.
- cierre_redondo: amarra la historia con el objeto.
- presente: lo que TÚ, quien ve, haces hoy por eso. De tú, nunca en primera persona:
    Mal:  "Por eso cada noviembre lo primero que cuelgo es el papel."
    Bien: "Por eso cada noviembre, antes que las flores, tú cuelgas el papel."
- mandar: "Mándaselo a quien…" + una persona que cualquiera conoce ("a quien siempre se
  come los huesitos primero"). Para que se comparta.
De 9 a 12 escenas; total de 160 a 220 palabras (unas 180 por minuto).

LOS DATOS (si no se puede verificar, NO va)
Cada escena lleva "respaldo":
- "hecho": tiene fuente que abriste y leíste (va en _schema.fuentes con el id de la escena).
- "saber_popular": lo que la gente cree sin evidencia fuerte NO se quita: se dice ATRIBUIDO, en
  la voz ("dicen que…", "según la tradición…", "se cree que…") y, si hay algo medido, después:
  "En el campo, dicen que ahuyenta plagas. Y algo de cierto hay: sus raíces sueltan…". También
  va en _schema.fuentes (de dónde sale la creencia y lo medido, si lo hay).
- "cuento": un mito o leyenda contado como tal ("cuenta la leyenda…", "según el mito…"), con
  su fuente (el códice, el cronista, el estudio).
- "sin_dato": la pregunta, el presente, el mandar, o una frase que solo repite lo ya dicho.
Lo que se sabe que es FALSO no entra, aunque sea muy popular: anótalo en
_schema.falsos_descartados con por qué. Una interpretación ("la cruz son los cuatro rumbos")
se dice como interpretación ("una lectura es…"), nunca como hecho.

LO QUE SE VE (todo es 3D hecho con código: objetos simples, luz cálida, fondo casi negro)
1. Lo que se dice es lo que se ve, LITERAL: si la voz dice "muchas florecitas", la flor se separa
   en florecitas; si dice "el camino", aparecen los pétalos en el piso.
2. Brillo en la parte de la que se habla, en el momento en que se dice (anima "brillo").
3. No salen personas ni caras: solo objetos.
4. La franja de arriba (subtítulos) y la de abajo (etiquetas) son del texto: el objeto va en el centro
   de la pantalla; no subas piezas por encima de y = 1 con las cámaras cerca o arriba.
5. Etiquetas: máximo dos por escena, palabras clave o el nombre de algo (CEMPŌHUALXŌCHITL,
   LUTEÍNA), de 34 letras o menos; subtítulo opcional de 50 o menos. No pongas fuentes.
Cada escena:
  "visual": de 1 a 6 objetos del CATÁLOGO, cada uno {"objeto": "<nombre>", <props>}.
  "camara": una de estas: <<CAMARAS>>
     o libre: {"pos": [x, y, z], "mira": [x, y, z]} (el objeto está en 0,0,0; la cámara a ~6 de
     distancia en z), o {"desde": {pos, mira}, "hasta": {pos, mira}, "entre": [0.2, 0.8]}.
  "etiquetas": [{"titulo": "...", "subtitulo": "...", "desde": 0.2, "hasta": 0.55}]
     (desde/hasta: 0 = empieza la escena, 1 = termina).
  "claves": de 2 a 4 palabras SUELTAS de ESA escena (una palabra cada una, tal cual la dice la
     voz: "noviembre", no "dos de noviembre") que se resaltan en los subtítulos.
Cualquier prop numérico (y posicion o escala) se puede ANIMAR dentro de la escena:
  {"de": 0, "a": 1, "desde": 0.55, "hasta": 0.85}  -> cambia entre el 55 % y el 85 % de la escena
  {"de": 0, "a": 1, "desde": 0, "hasta": 0.25, "regresa": [0.55, 0.7]}  -> sube y luego vuelve
Pon el cambio en el momento de la frase que lo dice (si "florecitas" está al final de la
escena, "desde" va cerca de 0.6).

CATÁLOGO (usa SOLO esto; con un prop o un objeto que no existe, el guion no pasa)
<<CATALOGO>>
EL PROTAGONISTA TIENE QUE EXISTIR: un Modelo de la biblioteca o uno de estos objetos hechos por
código: <<PROTAGONISTAS>>. Va en "protagonista" ({"objeto": "Flor"} o {"objeto": "Modelo",
"modelo": "food/corn"}), sale en la primera escena y en alguna de las tres últimas.
Si el tema necesita un protagonista que no hay (calaverita de azúcar, pan de muerto, piñata),
NO lo armes con Forma: se ve como figuras geométricas (30/10/2026). Cambia de tema y anota el
objeto en tu respuesta. Para lo de fondo que no esté, usa lo más cercano de la biblioteca.

EJEMPLO DE DOS ESCENAS (del cempasúchil)
  {"id": "pregunta", "tiempo": "pregunta", "respaldo": "sin_dato",
   "texto": "¿Por qué ponemos flor de cempasúchil para guiar a los muertos?",
   "camara": "acerca", "visual": [{"objeto": "Flor", "gira": 0.35, "brillo": 0.15}],
   "claves": ["cempasúchil", "muertos"]},
  {"id": "nombre", "tiempo": "giro_origen", "respaldo": "hecho",
   "texto": "Su nombre viene del náhuatl, cempoalxóchitl: veinte flores. Y veinte también quería decir muchas. Porque cada flor, en realidad, son muchas florecitas juntas.",
   "camara": "aleja",
   "visual": [{"objeto": "Flor", "giro": 2.6, "gira": 0.25, "brillo": 0.2,
               "explota": {"de": 0, "a": 1, "desde": 0.55, "hasta": 0.85}}],
   "etiquetas": [{"titulo": "CEMPŌHUALXŌCHITL", "subtitulo": "cempōhualli: veinte, muchas · xōchitl: flor", "desde": 0.08, "hasta": 0.5},
                 {"titulo": "MUCHAS FLORECITAS EN UNA", "desde": 0.6, "hasta": 1}],
   "claves": ["náhuatl", "veinte", "muchas", "florecitas"]}

CÓMO SUENA (español de México; de tú; como se lo cuentas a un compa)
- Frases que se enganchan ("pero aquí viene lo bueno", "y fíjate", "¿y sabes qué?"). Ninguna
  pasa de 25 palabras. Números en palabras.
- Nada de España ("vale", "móvil", "vosotros", "-áis/-éis") ni giros de traducción.
- Las preguntas a quien ve son de sí o no; nunca "¿A o B?".
- Palabras en náhuatl: máximo una por escena; la voz las lee como suenan en español.

FORMATO DE CADA GUION
Escríbelo en C:\Android_in\<slug>\guion.json, con slug "guion-tradicion-" + palabras cortas del
tema (minúsculas y guiones):
{"formato": "tradiciones",
 "titulo": "la pregunta, como título",
 "objeto": "el objeto protagonista, en palabras",
 "protagonista": {"objeto": "Modelo", "modelo": "food/corn"},
 "descripcion": "2 o 3 frases con lo que la gente buscaría (la tradición, el objeto, la fiesta) y una pregunta de sí o no al final",
 "hashtags": ["4 o 5: la fiesta, el objeto, #TradicionesMexicanas o #Mexico, #DatoMataGato; sin #fyp ni #viral"],
 "plus": {"portada": {"texto": "3 A 5 PALABRAS EN MAYÚSCULAS", "resalta": "1 o 2 de ellas"}},
 "escenas": [ ... ],
 "_schema": {"fuentes": {"<id de escena>": "qué dice, quién lo dice y la liga"},
             "falsos_descartados": ["lo popular que es falso, y por qué"],
             "objetos_que_faltan": ["lo de fondo que no había y qué usaste en su lugar"]}}
La portada es la que se ve en el perfil: el giro que sorprende ("TE COMES UN ESQUELETO").

AL TERMINAR responde SOLO este bloque JSON:
{"guiones": [{"slug": "...", "titulo": "...", "resumen_hechos": "2 líneas: el giro y su fuente"}]}
""".strip()

BUSCAR_TEMA = r"""
No te dieron tema: escoge <<CUANTOS>> objetos de tradiciones mexicanas con una pregunta "¿por
qué…?" que casi nadie sabe contestar, de la temporada que viene (las fiestas de las próximas
semanas) o de todo el año. Que el objeto se pueda mostrar con formas simples.
""".strip()

COMO_TRABAJAR = r"""
CÓMO TRABAJAR (cada respuesta tuya relee todo lo anterior: menos respuestas = menos costo)
- Junta en UNA respuesta las llamadas que no dependan entre sí.
- Para LEER fuentes usa buscar, no WebFetch: baja las páginas fuera de tu cuota y te regresa
  solo los datos con su cita comprobada (✔) y su liga:
      <<B>> "qué significa cempoalxóchitl en náhuatl" https://es.wikipedia.org/wiki/...
  WebFetch solo para una liga que buscar no pudo abrir. Nunca curl ni sed.
- Escribe el guion.json COMPLETO una sola vez (Write) y córrele la revisión automática:
      <<H>> revisar <slug>
  Revisa los 9 tiempos, el largo, el respaldo de cada escena, y que cada objeto, prop y cámara
  exista. Si marca algo, corrige TODO con Edit en la MISMA respuesta y vuelve a correrla.
""".strip()


def instruccion(n: int, tema: str | None, ya_hechos: str, ligera: bool = False) -> str:
    """El prompt del lote. Sin `tema`, Claude escoge (o toma del expediente)."""
    from dato_mata_gato_bot import instruccion_cercania

    if tema:
        descripcion = (f"{tema}. Si te piden más de un guion, cada uno es una pregunta distinta sobre "
                       "esta tradición, con su propio objeto protagonista.")
    else:
        descripcion = BUSCAR_TEMA.replace("<<CUANTOS>>", str(n))
    texto = (INSTRUCCION.replace("<<N>>", str(n)).replace("<<TEMA>>", descripcion)
             .replace("<<CATALOGO>>", _catalogo())
             .replace("<<PROTAGONISTAS>>", "; ".join(f"{k} ({v})" for k, v in PROTAGONISTAS.items()))
             .replace("<<CAMARAS>>", "; ".join(f"{k} ({v})" for k, v in CAMARAS.items())))
    if ligera:
        trabajar = (COMO_TRABAJAR.replace("<<H>>", instruccion_cercania.HERRAMIENTAS)
                    .replace("<<B>>", instruccion_cercania.BUSCAR))
        texto = texto.replace("\nAL TERMINAR responde", "\n" + trabajar + "\n\nAL TERMINAR responde")
    return texto + "\n\nYA ESTÁN HECHOS -- no repitas ninguno: " + ya_hechos


# --- Revisión sin Claude --------------------------------------------------------

_ATRIBUIDO = re.compile(r"\b(dicen|se dice|según la tradición|según la leyenda|según el mito|se cree|"
                        r"creen|cuentan|cuenta la leyenda|cuenta el mito|la gente dice|hay quien dice|"
                        r"la tradición dice|se supone|una lectura|se piensa)\b", re.IGNORECASE)
_MANDAR = re.compile(r"\b(m[aá]ndaselo|m[aá]ndale|comp[aá]rtelo|comp[aá]rteselo|p[aá]saselo)\b", re.IGNORECASE)
# El POC del cempasúchil: 224 palabras en 74.6 s (180 por minuto).
MIN_PALABRAS, MAX_PALABRAS = 150, 230
_DE_TU = re.compile(r"\b(tú|tu|tus|te|ti|contigo)\b", re.IGNORECASE)
MAX_FRASE = 32  # la instrucción pide 25; el tope deja pasar la de la yema del POC (31)


def _vacio(x) -> bool:
    return not str(x or "").strip()


def _norma(w: str) -> str:
    return re.sub(r"[^\wáéíóúüñ]", "", w.lower())


def _es_num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _valor_ok(v) -> bool:
    """Un valor fijo o una animación {"de", "a", "desde", "hasta", "regresa"} bien hecha."""
    if not isinstance(v, dict):
        return True
    if set(v) - {"de", "a", "desde", "hasta", "regresa"} or "de" not in v or "a" not in v:
        return False
    ambos = (v["de"], v["a"])
    if not (all(_es_num(x) for x in ambos)
            or all(isinstance(x, list) and len(x) == len(v["de"]) and all(_es_num(y) for y in x) for x in ambos)):
        return False
    for k in ("desde", "hasta"):
        if k in v and not (_es_num(v[k]) and 0 <= v[k] <= 1):
            return False
    if "regresa" in v:
        r = v["regresa"]
        if not (isinstance(r, list) and len(r) == 2 and all(_es_num(x) and 0 <= x <= 1 for x in r)):
            return False
    return True


def _toma_ok(t) -> bool:
    return (isinstance(t, dict) and all(isinstance(t.get(k), list) and len(t[k]) == 3
                                        and all(_es_num(x) for x in t[k]) for k in ("pos", "mira")))


def _camara_ok(c) -> bool:
    if c is None or (isinstance(c, str) and c in CAMARAS):
        return True
    if isinstance(c, dict) and "desde" in c:
        return _toma_ok(c.get("desde")) and _toma_ok(c.get("hasta"))
    return _toma_ok(c)


def problemas_de_escena(e: dict) -> list[str]:
    out = []
    eid = e.get("id", "?")
    visual = e.get("visual")
    if not isinstance(visual, list) or not 1 <= len(visual) <= 6:
        out.append(f'{eid}: "visual" lleva de 1 a 6 objetos del catálogo')
        visual = visual if isinstance(visual, list) else []
    for v in visual:
        nombre = v.get("objeto") if isinstance(v, dict) else None
        if nombre not in CATALOGO:
            out.append(f'{eid}: el objeto "{nombre}" no existe; usa uno del catálogo o ármalo con Forma')
            continue
        validos = set(CATALOGO[nombre][1]) | set(COMUNES) | {"objeto"}
        if malos := sorted(set(v) - validos):
            out.append(f'{eid}: {nombre} no tiene {", ".join(malos)} (tiene: '
                       f'{", ".join(sorted(validos - {"objeto"}))})')
        if nombre == "Modelo" and v.get("modelo") not in (biblioteca := modelos()):
            parecidos = difflib.get_close_matches(str(v.get("modelo")), list(biblioteca), n=3, cutoff=0.5)
            out.append(f'{eid}: el modelo "{v.get("modelo")}" no está en la biblioteca'
                       + (f' (¿{", ".join(parecidos)}?)' if parecidos else ""))
        for k, x in v.items():
            if not _valor_ok(x):
                out.append(f'{eid}: {nombre}.{k} está mal animado: {{"de": 0, "a": 1, "desde": 0.2, '
                           '"hasta": 0.6}, con desde/hasta entre 0 y 1')
    if sum(isinstance(v, dict) and v.get("objeto") == "Forma" for v in visual) > MAX_FORMAS:
        out.append(f"{eid}: más de {MAX_FORMAS} Forma: con primitivas sueltas el objeto se ve como figuras "
                   "geométricas; usa un Modelo de la biblioteca")
    if not _camara_ok(e.get("camara")):
        out.append(f'{eid}: "camara" tiene que ser una de {", ".join(CAMARAS)} o {{"pos": [x, y, z], '
                   '"mira": [x, y, z]}')
    etiquetas = e.get("etiquetas") or []
    if len(etiquetas) > 2:
        out.append(f"{eid}: máximo dos etiquetas por escena")
    for et in etiquetas:
        if _vacio(et.get("titulo")) or len(str(et.get("titulo"))) > 34:
            out.append(f'{eid}: la etiqueta "{et.get("titulo")}" va de 1 a 34 letras')
        if len(str(et.get("subtitulo") or "")) > 50:
            out.append(f'{eid}: el subtítulo de "{et.get("titulo")}" pasa de 50 letras')
        if not (_es_num(et.get("desde")) and _es_num(et.get("hasta")) and 0 <= et["desde"] < et["hasta"] <= 1):
            out.append(f'{eid}: la etiqueta "{et.get("titulo")}" necesita desde < hasta, entre 0 y 1')
    dichas = {_norma(w) for w in str(e.get("texto", "")).split()}
    claves = e.get("claves") or []
    if not claves:
        out.append(f'{eid}: faltan "claves" (2 a 4 palabras de la escena que se resaltan)')
    if fuera := [c for c in claves if _norma(str(c)) not in dichas]:
        out.append(f'{eid}: las claves {", ".join(map(str, fuera))} no son palabras que diga la voz en esta '
                   "escena: cada clave es UNA palabra, tal cual se dice (el subtítulo resalta palabra por palabra)")
    return out


def _clave_protagonista(v) -> str | None:
    if not isinstance(v, dict):
        return None
    return f"Modelo:{v.get('modelo')}" if v.get("objeto") == "Modelo" else v.get("objeto")


def problemas_de_protagonista(guion: dict) -> list[str]:
    """El candado del 30/10/2026: la calaverita armada con esferas se veía como
    figuras geométricas. El protagonista tiene que existir de verdad, abrir el
    video y regresar al final."""
    clave = _clave_protagonista(guion.get("protagonista"))
    if clave not in protagonistas():
        return [f'"protagonista" ({json.dumps(guion.get("protagonista"), ensure_ascii=False)}) no existe: tiene que '
                f'ser {", ".join(PROTAGONISTAS)} o un Modelo de la biblioteca. Si el tema no tiene protagonista, '
                "cambia de tema"]
    escenas = guion.get("escenas") or []
    en = [any(_clave_protagonista(v) == clave for v in e.get("visual") or []) for e in escenas]
    out = []
    if en and not en[0]:
        out.append("el protagonista no sale en la primera escena (la pregunta lo enseña desde el cuadro 0)")
    if en and not any(en[-3:]):
        out.append("el protagonista no regresa en las tres últimas escenas (abre y cierra el video)")
    return out


def problemas(guion: dict) -> list[str]:
    """Todo lo que el guion necesita para que el video salga y la fórmula se cumpla."""
    from dato_mata_gato_bot import fabrica

    out = []
    if guion.get("formato") != "tradiciones":
        out.append('falta "formato": "tradiciones"')
    for k in ("titulo", "objeto"):
        if _vacio(guion.get(k)):
            out.append(f'falta "{k}"')
    escenas = guion.get("escenas")
    if not isinstance(escenas, list) or not escenas:
        return out + ['faltan las "escenas"']
    if not 9 <= len(escenas) <= 12:
        out.append(f"lleva {len(escenas)} escenas y van de 9 a 12")
    ids = [e.get("id") for e in escenas]
    if len(set(ids)) != len(ids) or any(_vacio(i) for i in ids):
        out.append('cada escena lleva un "id" propio')
    tiempos = [e.get("tiempo") for e in escenas]
    if malos := sorted({str(t) for t in tiempos if t not in TIEMPOS}):
        out.append(f'"tiempo" no reconocido: {", ".join(malos)} (van: {", ".join(TIEMPOS)})')
    if faltan := [t for t in TIEMPOS if t not in tiempos]:
        out.append(f"faltan estos tiempos de la fórmula: {', '.join(faltan)}")
    orden = [TIEMPOS.index(t) for t in tiempos if t in TIEMPOS]
    if orden != sorted(orden):
        out.append("los tiempos van en el orden de la fórmula: " + " → ".join(TIEMPOS))
    if "?" not in str(escenas[0].get("texto", "")):
        out.append("la primera escena es la PREGUNTA sobre el objeto (con signos de pregunta)")
    if not _MANDAR.search(str(escenas[-1].get("texto", ""))):
        out.append('la última escena pide mandarlo a alguien en concreto: "Mándaselo a quien…"')
    # Dos de dos en las corridas del 30/10/2026: "reviso… el mío", "lo primero que cuelgo".
    for e in escenas:
        if e.get("tiempo") == "presente" and not _DE_TU.search(str(e.get("texto", ""))):
            out.append(f'{e.get("id")}: el presente le habla a quien ve, de tú ("tú cuelgas", "tu puerta"); '
                       "no en primera persona")
    palabras = sum(len(str(e.get("texto", "")).split()) for e in escenas)
    if not MIN_PALABRAS <= palabras <= MAX_PALABRAS:
        out.append(f"lleva {palabras} palabras y van de 160 a 220 (55 a 75 segundos)")
    out += problemas_de_protagonista(guion)
    fuentes = (guion.get("_schema") or {}).get("fuentes") or {}
    for e in escenas:
        eid, texto = e.get("id", "?"), str(e.get("texto", ""))
        if _vacio(texto):
            out.append(f'{eid}: escena sin "texto"')
        for frase in re.split(r"(?<=[.?!:;])\s+", texto):
            if len(frase.split()) > MAX_FRASE:
                out.append(f'{eid}: la frase "{frase[:50]}…" pasa de {MAX_FRASE} palabras; pártela')
        resp = e.get("respaldo")
        if resp not in RESPALDOS:
            out.append(f'{eid}: "respaldo" tiene que ser {", ".join(RESPALDOS)}')
        elif resp != "sin_dato" and _vacio(fuentes.get(eid)):
            out.append(f'{eid}: es "{resp}" y no tiene fuente en _schema.fuentes["{eid}"]')
        if resp in ("saber_popular", "cuento") and not _ATRIBUIDO.search(texto):
            out.append(f'{eid}: es {resp} y la voz lo dice como hecho; atribúyelo ("dicen que…", '
                       '"según la tradición…", "cuenta la leyenda…")')
        out += problemas_de_escena(e)
    portada = (guion.get("plus") or {}).get("portada") or {}
    if not 3 <= len(str(portada.get("texto", "")).split()) <= 5:
        out.append('falta "plus.portada": {"texto": "3 A 5 PALABRAS", "resalta": "1 o 2 de ellas"}')
    if len(str(guion.get("descripcion", "")).split()) < 12:
        out.append('falta "descripcion": 2 o 3 frases con lo que la gente buscaría y una pregunta')
    etiquetas = [str(h).strip().lower() for h in guion.get("hashtags", []) if str(h).strip()]
    if len([h for h in etiquetas if h not in fabrica.GENERICOS]) < 4:
        out.append("van de 4 a 5 hashtags útiles (la fiesta, el objeto, el nicho y #DatoMataGato)")
    planos = [{"id": e.get("id"), "narracion": str(e.get("texto", ""))} for e in escenas]
    return out + fabrica.problemas_de_registro({"planos": planos})


def es_tradicion(guion: dict) -> bool:
    return isinstance(guion, dict) and guion.get("formato") == "tradiciones"


def resumen_visual(guion: dict) -> str:
    """Los objetos que usa el guion, para el aviso de Telegram."""
    usados = sorted({v.get("objeto") for e in guion.get("escenas", []) for v in e.get("visual", [])
                     if isinstance(v, dict)})
    faltan = (guion.get("_schema") or {}).get("objetos_que_faltan") or []
    return ("3D: " + ", ".join(map(str, usados))
            + (f" · faltan objetos: {json.dumps(faltan, ensure_ascii=False)}" if faltan else ""))
