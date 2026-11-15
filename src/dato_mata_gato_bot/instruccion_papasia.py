"""Canal "papasia" (12/11/2026): información útil para papás y mamás primerizos.

Una preocupación real de las primeras semanas ("¿por qué llora a la misma hora
cada tarde?", "¿por qué hipa tanto?"), contestada con lo que dicen las
instituciones de salud, en 60-85 segundos y con el mismo video 3D hecho con
código del nicho de tradiciones (illustrated-narrator/tradiciones_3d).

Canal aparte del de Dato Mata Gato: su propio bot de Telegram
(@PapaPRIMEIABOT), su propia voz (Viral C de principal) y sus propios slugs
(`guion-papasia-`). Sale del POC del cólico vespertino, que Javier aprobó el
12/11/2026 (clip_assistance/analisis/nicho_bebes).

ESTO NO ES TRUE CRIME NI TRADICIONES: es salud infantil. Un dato mal puesto le
hace daño a un bebé de verdad y tumba la cuenta. Por eso la revisión de aquí es
la más dura del sistema y rechaza SIN pasar por Claude:

- Dosis de cualquier medicamento, y los medicamentos por su nombre.
- Diagnosticar ("si hace esto, tiene X") o prometer una cura ("esto quita el…").
- Tranquilizar de más ("no te preocupes si…"): este canal dice cuándo SÍ
  preocuparse, que es justo lo que un primerizo no sabe.
- El tema de las vacunas, en cualquier dirección.
- Un "hecho" sin liga a una institución de salud de FUENTES_BUENAS.
- Un video sin el tiempo `cuando_pediatra`: las señales de alarma van SIEMPRE,
  aunque el tema sea inofensivo.

El saber popular no se quita, se atribuye ("te van a decir que son gases") y
enseguida va lo que dicen las guías, igual que en tradiciones.
"""

import json
import re
from pathlib import Path

from dato_mata_gato_bot import canal
from dato_mata_gato_bot import instruccion_tradiciones as _trad

# Los objetos nuevos del canal (illustrated-narrator/tradiciones_3d/src/Objetos.tsx,
# commit fd01699) más los de tradiciones que sirven para este nicho. Si algo no
# está aquí, el render no sabría dibujarlo.
CATALOGO = {
    "Bebe": ("un bebé envuelto en su cobija, de plastilina, con gorrito de osito (alto ~2.1, de "
             "y = -1.05 a 1.05: con escala 1 queda sentado en la nube); es el protagonista del canal",
             {"duerme": "0-1: ojos cerrados y respiración lenta", "llora": "0-1: boca abierta, cara roja, "
              "puños arriba y temblorina", "brazos": "0-1: los saca del envoltorio",
              "brillo": "0-1: se ilumina cuando se habla de él", "cobija": "#hex (azul por defecto)"}),
    "Cuna": ("una cuna de madera con barrotes; el bebé va dentro con posicion [0, -0.2, 0]",
             {"colchon": "0-1 (1 = con colchón; 0 = vacía)", "barrotes": "9",
              "brillo": "0-1", "madera": "#hex"}),
    "Biberon": ("un biberón gordito (alto ~1.75, sentado en la nube); el nivel de leche se anima "
                "para hablar de tomas y cantidades",
                {"nivel": "0-1: cuánta leche tiene (0.6)", "brillo": "0-1",
                 "leche": "#hex", "tapa": "#hex"}),
    "Calendario": _trad.CATALOGO["Calendario"],
    "Particulas": _trad.CATALOGO["Particulas"],
    "Sol": _trad.CATALOGO["Sol"],
    "Piso": _trad.CATALOGO["Piso"],
    "Modelo": _trad.CATALOGO["Modelo"],
    "Forma": _trad.CATALOGO["Forma"],
}
COMUNES = _trad.COMUNES
CAMARAS = _trad.CAMARAS
MAX_FORMAS = _trad.MAX_FORMAS
MODELOS_INDICE = _trad.MODELOS_INDICE
# Quien puede protagonizar: el bebé casi siempre, el biberón en los temas de
# alimentación. La cuna no: es el escenario, y un video entero dentro de la cuna
# es lo que dejó al POC sin cambio visual los últimos 35 s (12/11/2026).
PROTAGONISTAS = {"Bebe": "el bebé envuelto", "Biberon": "el biberón (temas de alimentación)"}

# Los 9 tiempos de la fórmula, en orden. `nunca` es el único que puede faltar:
# no todo tema tiene una regla de seguridad dura que valga la pena decir.
TIEMPOS = ("pregunta", "respuesta", "normal", "numeros", "mito", "cuando_pediatra",
           "nunca", "pasa", "cierre")
OPCIONALES = ("nunca", "mito")
RESPALDOS = ("hecho", "saber_popular", "sin_dato")

# De dónde puede salir un "hecho". Sociedades médicas, salud pública y
# universidades: nada de blogs, marcas de fórmula ni "mamás influencers".
FUENTES_BUENAS = (
    "healthychildren.org", "aap.org", "who.int", "paho.org", "cdc.gov", "nhs.uk",
    "nih.gov", "nichd.nih.gov", "medlineplus.gov", "unicef.org", "mayoclinic.org",
    "imss.gob.mx", "gob.mx", "salud.gob.mx", "unam.mx", "insp.mx",
)

# Medido del POC del cólico (12/11/2026): 301 palabras en 80 s, o sea ~235 por
# minuto. La voz de este canal (Viral C) corre bastante más que la de
# tradiciones, así que el rango de allá (180 por minuto) dejaba fuera un video
# que ya funcionaba. 60 a 85 segundos.
MIN_PALABRAS, MAX_PALABRAS = 200, 320
MAX_FRASE = 32
# Una escena de más de esto dura más de ~8 s: necesita que algo se mueva, o se
# vuelve una diapositiva (el defecto del POC del 12/11/2026).
PALABRAS_SIN_MOVIMIENTO = 20
# Cuántas escenas seguidas pueden tener EXACTAMENTE los mismos objetos.
MAX_ESCENAS_IGUALES = 3
# Tradiciones permite 2 etiquetas y 50 letras de subtítulo, pero allá el
# subtítulo es un apunte ("cempōhualli: veinte") y aquí es la institución que
# respalda el dato ("AAP: puede causar ceguera, daño cerebral o la muerte"), que
# no cabe en 50. Medido de las etiquetas del POC, que se leen bien (12/11/2026).
MAX_ETIQUETAS = 3
MAX_SUBTITULO = 70


# --- Lo que no puede decir un video de este canal -------------------------------

_MEDICAMENTOS = re.compile(
    r"\b(paracetamol|acetaminof[eé]n|tempra|ibuprofeno|advil|motrin|aspirina|amoxicilina|"
    r"antibi[oó]tic\w*|simeticona|dimeticona|ranitidina|omeprazol|jarabe|supositorio|"
    r"gotas\s+de|antihistam[ií]nic\w*|melatonina)\b", re.IGNORECASE)
_DOSIS = re.compile(r"\b\d[\d.,]*\s*(mg|ml|mililitros?|miligramos?|gotas?|cucharadit\w+|cucharad\w+)\b",
                    re.IGNORECASE)
_CURA = re.compile(r"\b(cura|curan|curar\w*|quita\s+(el|la|los|las)|elimina\s+(el|la|los|las)|"
                   r"se\s+quita\s+con|acaba\s+con\s+(el|la)|remedio\s+para)\b", re.IGNORECASE)
_DIAGNOSTICO = re.compile(r"(si\s+(tu\s+beb[eé]|lo\s+ves|hace|llora|tiene)[^.?!]{0,60}\b"
                          r"(es|tiene|significa\s+que\s+tiene)\s+(c[oó]lico|reflujo|alergia|infecci[oó]n|"
                          r"intolerancia)\b)", re.IGNORECASE)
_TRANQUILIZAR = re.compile(r"\bno\s+te\s+preocupes\s+si\b", re.IGNORECASE)
_VACUNAS = re.compile(r"\bvacun\w+\b", re.IGNORECASE)
# Lo que tiene que estar.
_ATRIBUIDO = _trad._ATRIBUIDO
_TE_VAN_A_DECIR = re.compile(r"\b(te\s+van\s+a\s+decir|te\s+dir[aá]n|vas\s+a\s+o[ií]r|te\s+van\s+a\s+contar)\b",
                             re.IGNORECASE)
_PEDIATRA = re.compile(r"\b(pediatra|m[eé]dic\w+|doctor\w*|urgencias)\b", re.IGNORECASE)
_NO_SUSTITUYE = re.compile(r"\bno\s+sustituye\b", re.IGNORECASE)
_MANDAR = _trad._MANDAR

PROHIBIDO = (
    (_MEDICAMENTOS, "nombra un medicamento: este canal no habla de medicinas, ni para decir que son "
                    "buenas ni malas. Eso lo receta el pediatra"),
    (_DOSIS, "trae una dosis (mg, ml, gotas, cucharadas): nunca va una cantidad de nada que se le dé "
             "a un bebé"),
    (_CURA, "promete que algo cura o quita: ninguna información de un video cura nada"),
    (_DIAGNOSTICO, "diagnostica ('si hace esto, tiene X'): describe lo que pasa, nunca le pongas "
                   "nombre de enfermedad al bebé de quien te ve"),
    (_TRANQUILIZAR, "dice 'no te preocupes si…': este canal dice cuándo SÍ hay que ir al pediatra, "
                    "que es lo que un primerizo no sabe"),
    (_VACUNAS, "habla de vacunas: el tema no entra en este canal, en ninguna dirección"),
)


def modelos() -> dict[str, str]:
    return _trad.modelos()


def protagonistas() -> dict[str, str]:
    return dict(PROTAGONISTAS)


def _catalogo() -> str:
    lineas = []
    for nombre, (que, props) in CATALOGO.items():
        lineas.append(f"  - {nombre}: {que}. " + ", ".join(f"{k} ({v})" for k, v in props.items()))
    lineas.append("  Todos aceptan además: " + ", ".join(f"{k} ({v})" for k, v in COMUNES.items()))
    por_paquete: dict[str, list[str]] = {}
    for nombre, que in modelos().items():
        por_paquete.setdefault(nombre.split("/")[0], []).append(f"{nombre} ({que})")
    lineas.append("BIBLIOTECA (para Modelo, solo para cosas de fondo):")
    lineas += [f"  {', '.join(v)}" for v in por_paquete.values()]
    return "\n".join(lineas)


INSTRUCCION = r"""
Vas a escribir <<N>> guiones de video corto (60 a 85 segundos) para el canal PAPASIA, de
información útil para papás y mamás PRIMERIZOS.

EL TEMA
<<TEMA>>

DE QUÉ VA
Una preocupación REAL de quien acaba de tener su primer bebé ("¿por qué llora a la misma hora
cada tarde?", "¿por qué se sobresalta dormido?", "¿cuántas veces debería comer?"), contestada
con lo que dicen las instituciones de salud. Quien te ve está cansado, asustado y buscando en
el celular a las tres de la mañana. El video hace dos cosas: le dice qué es normal, y le dice
cuándo SÍ tiene que llamar al pediatra.

ESTO ES SALUD INFANTIL, NO ES UN CANAL DE DATOS CURIOSOS
- NUNCA menciones un medicamento, ni para bien ni para mal. Ninguna dosis, ninguna cantidad de
  nada que se le dé a un bebé. Eso lo receta el pediatra y punto.
- NUNCA diagnostiques ("si hace esto, tiene cólico"): describe lo que pasa, sin ponerle nombre
  de enfermedad al bebé de quien te ve.
- NUNCA prometas que algo cura o quita algo.
- NUNCA digas "no te preocupes si…". Este canal dice cuándo SÍ preocuparse.
- El tema de las vacunas NO entra, en ninguna dirección.
- Si el tema que te tocó no se puede contar sin romper algo de esto, CAMBIA DE TEMA y anótalo.

LOS 9 TIEMPOS (cada escena lleva "tiempo"; en este orden)
- pregunta (0-2 s): la preocupación, en las palabras en que la diría un papá primerizo, con el
  bebé en pantalla desde el cuadro 0. Con signos de pregunta.
- respuesta (3-12 s): la respuesta directa, nombrando a quien lo dice ("la Academia Americana de
  Pediatría le pone horario"). Sin rodeos y sin suspenso.
- normal: lo que casi nadie le dice: que esto le pasa a muchos y no es su culpa. Es la razón por
  la que el video se comparte.
- numeros: el dato que lo vuelve concreto (uno de cada cinco, a las seis semanas, tres horas al
  día). Números en palabras.
- mito (puede faltar): lo que le van a decir los demás, ATRIBUIDO ("te van a decir que son
  gases"), y enseguida lo que dicen las guías. No te burles de quien lo dice.
- cuando_pediatra: OBLIGATORIO EN TODOS LOS VIDEOS, aunque el tema sea inofensivo. Las señales
  concretas con las que hay que llamar al pediatra, tal como las lista la fuente.
- nunca (puede faltar): la regla de seguridad dura del tema, si la hay ("a un bebé nunca se le
  sacude"), con lo que puede pasar y qué hacer en su lugar.
- pasa: cuándo se acaba o qué esperar ("a los tres o cuatro meses se va solo").
- cierre: "esto no sustituye a tu pediatra" (con esas palabras) + "mándaselo a quien…" con una
  persona concreta y reconocible ("a quien hoy anda caminando el pasillo a las ocho de la noche").
De 9 a 12 escenas; de 200 a 320 palabras en total.

LOS DATOS (si no tiene liga de una institución, NO va)
Cada escena lleva "respaldo":
- "hecho": lo dice una de estas instituciones y abriste la página: <<FUENTES>>.
  Va en _schema.fuentes con el id de la escena, con QUÉ dice, QUIÉN lo dice y LA LIGA COMPLETA.
  Sin liga de esos dominios, la revisión lo rechaza.
- "saber_popular": lo que se cree sin evidencia. No se quita: se dice atribuido ("te van a decir
  que…", "dicen que…") y enseguida lo que dicen las guías. También lleva fuente.
- "sin_dato": la pregunta, el cierre, o una frase que solo repite lo ya dicho.
Si una cifra aparece distinta en dos instituciones, usa la más conservadora y anótalo.

LO QUE SE VE (3D hecho con código: objetos simples, luz cálida, fondo casi negro)
1. Lo que se dice es lo que se ve, LITERAL: si la voz dice "uno de cada cinco", se ven cinco
   bebés y uno se ilumina; si dice "a las seis semanas", el calendario marca la casilla.
2. Brillo en la parte de la que se habla, en el momento en que se dice (anima "brillo").
3. NO SE REPITA LA MISMA ESTAMPA: no pongas más de tres escenas seguidas con exactamente los
   mismos objetos. En el primer video del canal los últimos treinta y cinco segundos eran la
   misma cuna quieta y se cae la retención. Cambia de objeto, de cámara o de encuadre.
4. Toda escena de más de veinte palabras lleva ALGO ANIMADO (un prop con {"de"…"a"…} o dos
   etiquetas que entran en momentos distintos).
5. Caras: el bebé es estilo juguete y nada más. No salen papás ni personas.
6. Etiquetas: máximo tres por escena, de 34 letras o menos; el subtítulo (70 o menos) es donde va
   la institución que lo dice ("Academia Americana de Pediatría").
Cada escena:
  "visual": de 1 a 6 objetos del CATÁLOGO, cada uno {"objeto": "<nombre>", <props>}.
  "camara": una de estas: <<CAMARAS>>
     o libre: {"pos": [x, y, z], "mira": [x, y, z]}, o {"desde": {...}, "hasta": {...}}.
  "etiquetas": [{"titulo": "...", "subtitulo": "...", "desde": 0.2, "hasta": 0.55}]
  "claves": de 2 a 4 palabras SUELTAS de ESA escena, tal cual las dice la voz.
Cualquier prop numérico se puede ANIMAR: {"de": 0, "a": 1, "desde": 0.55, "hasta": 0.85}.

CATÁLOGO (usa SOLO esto)
<<CATALOGO>>
CÓMO SE VE (15/11/2026): plastilina pastel sobre una nube rosa, con fondo claro. El render pone
solo la nube, el fondo y la luz, y vuelve pastel cualquier color que mandes: no uses Piso ni
colores oscuros. El cuadro es vertical: con la cámara normal solo se ve de x = -1 a x = 1; lo
que pongas más afuera NO sale (un Bebe chico junto al Calendario va en x = 0.6, no en 1.4).
EL PROTAGONISTA: <<PROTAGONISTAS>>. Va en "protagonista" ({"objeto": "Bebe"}), sale en la
primera escena y en alguna de las tres últimas.

CÓMO SUENA (español de México; de tú; como se lo explicas a tu hermana que acaba de ser mamá)
- Cálido y directo, nunca alarmista y nunca condescendiente. Ninguna frase pasa de 25 palabras.
- Números en palabras. Nada de España ni giros de traducción.
- No le digas a quien te ve lo que "debería" estar haciendo: dile lo que dicen las guías.
- Las preguntas a quien ve son de sí o no.

FORMATO DE CADA GUION
Escríbelo en C:\Android_in\<slug>\guion.json, con slug "guion-papasia-" + palabras cortas del
tema (minúsculas y guiones):
{"formato": "papasia",
 "titulo": "la pregunta, como título",
 "objeto": "de qué trata, en palabras",
 "protagonista": {"objeto": "Bebe"},
 "voz_narrador": "viral_c",
 "descripcion": "2 o 3 frases con lo que un primerizo buscaría, qué instituciones se citan, y al final: Esto no sustituye a tu pediatra.",
 "hashtags": ["4 o 5: #PapasPrimerizos, el tema, #Bebes, #Maternidad o #Paternidad; sin #fyp ni #viral"],
 "plus": {"portada": {"texto": "3 A 5 PALABRAS EN MAYÚSCULAS", "resalta": "1 o 2 de ellas"}},
 "escenas": [ ... ],
 "_schema": {"fuentes": {"<id de escena>": "qué dice, quién lo dice y la liga completa"},
             "descartado": ["lo que no pusiste por las reglas de arriba, y por qué"]}}

AL TERMINAR responde SOLO este bloque JSON:
{"guiones": [{"slug": "...", "titulo": "...", "resumen_hechos": "2 líneas: el dato principal y su institución"}]}
""".strip()

BUSCAR_TEMA = r"""
No te dieron tema: escoge <<CUANTOS>> preocupaciones de las primeras doce semanas que un papá
primerizo busque de madrugada y que una institución de salud conteste claro (el llanto, el
sueño, las tomas, el hipo, los sobresaltos, la popó, el peso, la costra láctea, el ombligo).
Que se pueda mostrar con un bebé, una cuna, un biberón y un calendario.
""".strip()


def instruccion(n: int, tema: str | None, ya_hechos: str, ligera: bool = False) -> str:
    """El prompt del lote. Sin `tema`, Claude escoge."""
    from dato_mata_gato_bot import instruccion_cercania

    if tema:
        descripcion = (f"{tema}. Si te piden más de un guion, cada uno es una preocupación distinta "
                       "sobre este tema, con su propia pregunta.")
    else:
        descripcion = BUSCAR_TEMA.replace("<<CUANTOS>>", str(n))
    texto = (INSTRUCCION.replace("<<N>>", str(n)).replace("<<TEMA>>", descripcion)
             .replace("<<CATALOGO>>", _catalogo())
             .replace("<<FUENTES>>", ", ".join(FUENTES_BUENAS))
             .replace("<<PROTAGONISTAS>>", "; ".join(f"{k} ({v})" for k, v in PROTAGONISTAS.items()))
             .replace("<<CAMARAS>>", "; ".join(f"{k} ({v})" for k, v in CAMARAS.items())))
    if ligera:
        trabajar = (_trad.COMO_TRABAJAR.replace("<<H>>", instruccion_cercania.HERRAMIENTAS)
                    .replace("<<B>>", instruccion_cercania.BUSCAR)
                    .replace("revisar <slug>", "revisar <slug>"))
        texto = texto.replace("\nAL TERMINAR responde", "\n" + trabajar + "\n\nAL TERMINAR responde")
    # Los guiones del canal van en su carpeta, no en la raíz de Dato Mata Gato.
    texto = texto.replace("C:\\Android_in\\<slug>", str(canal.entrada("papasia")) + "\\<slug>")
    return texto + "\n\nYA ESTÁN HECHOS -- no repitas ninguno: " + ya_hechos


# --- Revisión sin Claude --------------------------------------------------------

_vacio = _trad._vacio
_es_num = _trad._es_num
_valor_ok = _trad._valor_ok
_camara_ok = _trad._camara_ok


def _tiene_liga_buena(fuente: str) -> bool:
    """Una fuente sirve si trae una liga de FUENTES_BUENAS."""
    ligas = re.findall(r"https?://[^\s,;)]+", str(fuente or ""))
    return any(any(d in liga.lower() for d in FUENTES_BUENAS) for liga in ligas)


def _animado(v) -> bool:
    """Si algún prop del objeto cambia dentro de la escena."""
    return isinstance(v, dict) and any(isinstance(x, dict) and "de" in x and "a" in x for x in v.values())


def _firma(e: dict) -> tuple:
    """Qué objetos tiene una escena, para detectar la estampa repetida."""
    return tuple(sorted(str(v.get("objeto")) for v in e.get("visual") or [] if isinstance(v, dict)))


def problemas_de_escena(e: dict) -> list[str]:
    """Lo mismo que revisa tradiciones (objetos, props, cámara, etiquetas, claves)
    pero contra el catálogo de este canal, más la regla del movimiento."""
    out = []
    eid = e.get("id", "?")
    visual = e.get("visual")
    if not isinstance(visual, list) or not 1 <= len(visual) <= 6:
        out.append(f'{eid}: "visual" lleva de 1 a 6 objetos del catálogo')
        visual = visual if isinstance(visual, list) else []
    for v in visual:
        nombre = v.get("objeto") if isinstance(v, dict) else None
        if nombre not in CATALOGO:
            out.append(f'{eid}: el objeto "{nombre}" no existe en este canal '
                       f'(hay: {", ".join(CATALOGO)})')
            continue
        validos = set(CATALOGO[nombre][1]) | set(COMUNES) | {"objeto"}
        if malos := sorted(set(v) - validos):
            out.append(f'{eid}: {nombre} no tiene {", ".join(malos)} (tiene: '
                       f'{", ".join(sorted(validos - {"objeto"}))})')
        if nombre == "Modelo" and v.get("modelo") not in modelos():
            out.append(f'{eid}: el modelo "{v.get("modelo")}" no está en la biblioteca')
        for k, x in v.items():
            if not _valor_ok(x):
                out.append(f'{eid}: {nombre}.{k} está mal animado: {{"de": 0, "a": 1, "desde": 0.2, '
                           '"hasta": 0.6}, con desde/hasta entre 0 y 1')
    if sum(isinstance(v, dict) and v.get("objeto") == "Forma" for v in visual) > MAX_FORMAS:
        out.append(f"{eid}: más de {MAX_FORMAS} Forma: con primitivas sueltas se ve como figuras geométricas")
    if not _camara_ok(e.get("camara")):
        out.append(f'{eid}: "camara" tiene que ser una de {", ".join(CAMARAS)} o {{"pos": [x, y, z], '
                   '"mira": [x, y, z]}')
    etiquetas = e.get("etiquetas") or []
    if len(etiquetas) > MAX_ETIQUETAS:
        out.append(f"{eid}: máximo {MAX_ETIQUETAS} etiquetas por escena")
    for et in etiquetas:
        if _vacio(et.get("titulo")) or len(str(et.get("titulo"))) > 34:
            out.append(f'{eid}: la etiqueta "{et.get("titulo")}" va de 1 a 34 letras')
        if len(str(et.get("subtitulo") or "")) > MAX_SUBTITULO:
            out.append(f'{eid}: el subtítulo de "{et.get("titulo")}" pasa de {MAX_SUBTITULO} letras')
        if not (_es_num(et.get("desde")) and _es_num(et.get("hasta")) and 0 <= et["desde"] < et["hasta"] <= 1):
            out.append(f'{eid}: la etiqueta "{et.get("titulo")}" necesita desde < hasta, entre 0 y 1')
    # El defecto del POC (12/11/2026): escenas largas sin que nada se mueva.
    palabras = len(str(e.get("texto", "")).split())
    if palabras > PALABRAS_SIN_MOVIMIENTO:
        tiempos_etiq = {(et.get("desde"), et.get("hasta")) for et in etiquetas}
        if not any(_animado(v) for v in visual) and len(tiempos_etiq) < 2:
            out.append(f"{eid}: son {palabras} palabras (más de {PALABRAS_SIN_MOVIMIENTO}, o sea más de "
                       "unos ocho segundos) y no se mueve nada: anima un prop "
                       '({"de": 0, "a": 1, "desde": 0.3, "hasta": 0.7}) o pon dos etiquetas en '
                       "momentos distintos")
    dichas = {_trad._norma(w) for w in str(e.get("texto", "")).split()}
    claves = e.get("claves") or []
    if not claves:
        out.append(f'{eid}: faltan "claves" (2 a 4 palabras de la escena que se resaltan)')
    if fuera := [c for c in claves if _trad._norma(str(c)) not in dichas]:
        out.append(f'{eid}: las claves {", ".join(map(str, fuera))} no son palabras que diga la voz en '
                   "esta escena")
    return out


def problemas_de_seguridad(guion: dict) -> list[str]:
    """Lo que no puede decir un video de salud infantil. Esto no escala a Claude:
    si algo de aquí salta, el guion se tira."""
    out = []
    for e in guion.get("escenas") or []:
        texto = str(e.get("texto", ""))
        eid = e.get("id", "?")
        for patron, motivo in PROHIBIDO:
            if m := patron.search(texto):
                out.append(f'{eid}: "{m.group(0)}" — {motivo}')
    return out


def problemas_de_protagonista(guion: dict) -> list[str]:
    prota = guion.get("protagonista")
    nombre = prota.get("objeto") if isinstance(prota, dict) else None
    if nombre not in PROTAGONISTAS:
        return [f'"protagonista" ({json.dumps(prota, ensure_ascii=False)}) tiene que ser '
                f'{" o ".join(PROTAGONISTAS)}']
    escenas = guion.get("escenas") or []
    en = [any(isinstance(v, dict) and v.get("objeto") == nombre for v in e.get("visual") or [])
          for e in escenas]
    out = []
    if en and not en[0]:
        out.append("el protagonista no sale en la primera escena")
    if en and not any(en[-3:]):
        out.append("el protagonista no regresa en las tres últimas escenas")
    return out


def problemas(guion: dict) -> list[str]:
    """Todo lo que el guion necesita para que el video salga y sea seguro."""
    from dato_mata_gato_bot import fabrica

    out = []
    if guion.get("formato") != "papasia":
        out.append('falta "formato": "papasia"')
    for k in ("titulo", "objeto"):
        if _vacio(guion.get(k)):
            out.append(f'falta "{k}"')
    escenas = guion.get("escenas")
    if not isinstance(escenas, list) or not escenas:
        return out + ['faltan las "escenas"']
    out += problemas_de_seguridad(guion)
    if not 9 <= len(escenas) <= 12:
        out.append(f"lleva {len(escenas)} escenas y van de 9 a 12")
    ids = [e.get("id") for e in escenas]
    if len(set(ids)) != len(ids) or any(_vacio(i) for i in ids):
        out.append('cada escena lleva un "id" propio')
    tiempos = [e.get("tiempo") for e in escenas]
    if malos := sorted({str(t) for t in tiempos if t not in TIEMPOS}):
        out.append(f'"tiempo" no reconocido: {", ".join(malos)} (van: {", ".join(TIEMPOS)})')
    if faltan := [t for t in TIEMPOS if t not in tiempos and t not in OPCIONALES]:
        out.append(f"faltan estos tiempos de la fórmula: {', '.join(faltan)}")
    orden = [TIEMPOS.index(t) for t in tiempos if t in TIEMPOS]
    if orden != sorted(orden):
        out.append("los tiempos van en el orden de la fórmula: " + " → ".join(TIEMPOS))
    if "?" not in str(escenas[0].get("texto", "")):
        out.append("la primera escena es la PREGUNTA que se hace un primerizo (con signos de pregunta)")
    # Las dos que hacen seguro al canal.
    pediatra = next((e for e in escenas if e.get("tiempo") == "cuando_pediatra"), None)
    if pediatra is None:
        out.append('falta el tiempo "cuando_pediatra": las señales para llamar al pediatra van en '
                   "TODOS los videos, aunque el tema parezca inofensivo")
    elif not _PEDIATRA.search(str(pediatra.get("texto", ""))):
        out.append(f'{pediatra.get("id")}: el tiempo cuando_pediatra no nombra al pediatra ni a urgencias')
    ultima = str(escenas[-1].get("texto", ""))
    if not _NO_SUSTITUYE.search(ultima):
        out.append('la última escena tiene que decir que esto "no sustituye" a su pediatra')
    if not _MANDAR.search(ultima):
        out.append('la última escena pide mandarlo a alguien en concreto: "Mándaselo a quien…"')
    palabras = sum(len(str(e.get("texto", "")).split()) for e in escenas)
    if not MIN_PALABRAS <= palabras <= MAX_PALABRAS:
        out.append(f"lleva {palabras} palabras y van de {MIN_PALABRAS} a {MAX_PALABRAS} (60 a 85 segundos)")
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
        elif resp != "sin_dato":
            fuente = fuentes.get(eid)
            if _vacio(fuente):
                out.append(f'{eid}: es "{resp}" y no tiene fuente en _schema.fuentes["{eid}"]')
            elif not _tiene_liga_buena(fuente):
                out.append(f'{eid}: la fuente no trae liga de una institución de salud. Tiene que salir '
                           f'de: {", ".join(FUENTES_BUENAS[:8])}…')
        if resp == "saber_popular" and not (_ATRIBUIDO.search(texto) or _TE_VAN_A_DECIR.search(texto)):
            out.append(f'{eid}: es saber_popular y la voz lo dice como hecho; atribúyelo '
                       '("te van a decir que…", "dicen que…")')
        out += problemas_de_escena(e)
    # La estampa repetida: lo que dejó al POC sin cambio visual los últimos 35 s.
    seguidas, anterior = 1, None
    for e in escenas:
        f = _firma(e)
        seguidas = seguidas + 1 if f == anterior else 1
        if seguidas > MAX_ESCENAS_IGUALES:
            out.append(f'{e.get("id")}: van {seguidas} escenas seguidas con los mismos objetos '
                       f'({", ".join(f) or "ninguno"}): cambia de objeto o de encuadre, no más de '
                       f"{MAX_ESCENAS_IGUALES} seguidas")
            break
        anterior = f
    portada = (guion.get("plus") or {}).get("portada") or {}
    en_portada = len(str(portada.get("texto", "")).split())
    if en_portada > 5:  # "falta" confundía: el 15/11/2026 traía 6 palabras y se quedó sin corregir
        out.append(f'"plus.portada.texto" lleva {en_portada} palabras y van de 3 a 5')
    elif en_portada < 3:
        out.append('falta "plus.portada": {"texto": "3 A 5 PALABRAS", "resalta": "1 o 2 de ellas"}')
    if len(str(guion.get("descripcion", "")).split()) < 12:
        out.append('falta "descripcion": 2 o 3 frases con lo que un primerizo buscaría')
    etiquetas = [str(h).strip().lower() for h in guion.get("hashtags", []) if str(h).strip()]
    if len([h for h in etiquetas if h not in fabrica.GENERICOS]) < 4:
        out.append("van de 4 a 5 hashtags útiles (#PapasPrimerizos, el tema, #Bebes)")
    planos = [{"id": e.get("id"), "narracion": str(e.get("texto", ""))} for e in escenas]
    return out + fabrica.problemas_de_registro({"planos": planos})


def es_papasia(guion: dict) -> bool:
    return isinstance(guion, dict) and guion.get("formato") == "papasia"


def resumen_visual(guion: dict) -> str:
    """Los objetos y las instituciones del guion, para el aviso de Telegram."""
    usados = sorted({v.get("objeto") for e in guion.get("escenas", []) for v in e.get("visual", [])
                     if isinstance(v, dict)})
    fuentes = (guion.get("_schema") or {}).get("fuentes") or {}
    ligas = {d for f in fuentes.values() for d in FUENTES_BUENAS if d in str(f).lower()}
    return ("3D: " + ", ".join(map(str, usados))
            + (" · fuentes: " + ", ".join(sorted(ligas)) if ligas else " · SIN FUENTES"))
