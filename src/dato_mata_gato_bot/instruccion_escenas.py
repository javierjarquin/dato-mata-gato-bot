"""Escenas 3D por plano, en vez del formato "noticia" (11/11/2026).

Hasta hoy el render plus vivía de lo que publicó la prensa: la captura de la
nota que baja hasta el párrafo, la foto del medio, tomas de archivo y fichas de
texto. Se veía como un noticiero y no dibujaba LO QUE PASÓ. Esto lo cambia:
después de escribir el guion, la fábrica le pide a Claude, plano por plano, qué
se ve —escenario, personajes y qué hacen, cámara, etiquetas y qué evidencia
real va como sello y cuándo—, igual que el nicho de tradiciones.

Lo escrito va a C:\\Android_in\\<slug>\\escenas.json y lo dibuja
illustrated-narrator/tradiciones_3d (scripts/escenas.py + src/Escenas.tsx), con
modelos de Kenney (CC0), sin IA.

Reglas que no se negocian y por qué:
- Las víctimas nunca son figuras: van como velas, objetos o ausencia. Poner a
  una persona real muerta en muñequitos es de mal gusto y nos tira el canal.
  Por eso `die`, los ataques y las armas no están entre las animaciones.
- Nada de caras realistas: el catálogo es estilo juguete y nada más.
- La evidencia real NO se reconstruye: va como sello con su fuente.
- "RECREACIÓN" siempre visible: lo pone el render en cada plano.
"""

import difflib
import json
import re
from pathlib import Path

# La biblioteca de modelos del piloto de escenas (Kenney, CC0): ciudad, colonia,
# calles, autos, muebles y personajes. La arma tradiciones_3d/scripts/biblioteca.py.
MODELOS_INDICE = Path(r"C:\illustrated-narrator\tradiciones_3d\public\modelos\indice_escenas.json")
# Cuánto mide cada modelo de fábrica (x, y, z), medido de sus .glb. El render
# escala por el ALTO, así que una pieza ancha y baja se vuelve enorme de ancho:
# colonia/fence (0.48 x 0.27) con alto 1.4 salió de 2.5 de ancho y tapó el
# cuadro entero en la primera corrida (guion-estacion-migratoria-juarez,
# 11/11/2026). Lo escribe tradiciones_3d/scripts/biblioteca.py.
TAMANOS_INDICE = MODELOS_INDICE.with_name("tamanos_escenas.json")
# A unas 5 unidades de la cámara y con FOV 40, en el cuadro vertical caben ~2
# unidades de ancho y ~3.6 de alto. Una pieza más ancha que esto, puesta
# delante, es una pared: no se ve nada más.
ANCHO_DE_PANTALLA = 2.4
# Hasta aquí es "fondo": lo de atrás puede ser todo lo ancho que quiera.
FONDO_Z = -2.5
# Alto desde el que una pieza deja de ser un detalle del piso y tapa.
ALTO_QUE_TAPA = 0.6
# Sellos de evidencia por video: con uno en cada plano, la escena no se ve.
MAX_SELLOS = 4

# Objeto -> (qué es, {prop: qué hace}). Lo mismo que dibujan tradiciones_3d/src/
# Escenas.tsx y Objetos.tsx. Si algo no está aquí, el render no sabría dibujarlo.
CATALOGO = {
    "Personaje": ("una persona estilo juguete, de pie en y = 0 (mide `alto`, 0.9 por defecto)",
                  {"modelo": "uno de personajes/… de la biblioteca", "animacion": "de la lista de ANIMACIONES",
                   "alto": "0.9 (un niño 0.7)", "giro": "radianes: 0 mira a la cámara, 1.5708 a su derecha",
                   "velocidad": "1 = la animación a su ritmo", "desfase": "segundos: para que dos no vayan igual",
                   "una_vez": "true: la animación no se repite", "brillo": "0-1: se ilumina cuando se habla de él"}),
    "Multitud": ("varias personas repartidas en un rectángulo (una marcha, una fila, gente mirando)",
                 {"n": "cuántas (12)", "ancho": "6", "fondo": "2.5", "alto": "0.9",
                  "animacion": "de ANIMACIONES, la misma para todas", "giro": "radianes",
                  "semilla": "texto: cambia quiénes son", "aparece": "0-1: qué fracción ya llegó (anímalo y llega gente)"}),
    "Modelo": ("un modelo de la BIBLIOTECA (lista abajo), apoyado en y = 0",
               {"modelo": "nombre de la biblioteca, p. ej. autos/police",
                "alto": "altura en unidades (una persona mide 0.9; un auto 0.7; un edificio 3 a 4)",
                "ancho": "en vez de alto, para piezas planas (una calle: ancho 2)",
                "brillo": "0-1", "giro": "radianes"}),
    "Suelo": ("el piso, plano y grande, a y = 0. Va en TODAS las escenas de calle o cuarto",
              {"color": "#hex (noche #1C1F26, cuarto #2A2420)", "tamano": "80"}),
    "Luz": ("una luz de color, para lo que la escena necesita (torreta de patrulla, foco)",
            {"color": "#hex", "fuerza": "3", "distancia": "6", "parpadeo": "vueltas por segundo (2 = torreta)"}),
    "Velas": ("fila de velas encendidas. ASÍ van las víctimas: una vela por persona, nunca un muñeco",
              {"cantidad": "5", "fuerza": "0-1 (0 = apagadas; anímalo para encenderlas una por una)",
               "separacion": "0.5"}),
    "Particulas": ("chispas o humo que suben ondulando (humo, polvo, vapor)",
                   {"fuerza": "0-1", "color": "#hex", "cantidad": "70", "alto": "3.2", "ancho": "0.9"}),
    "Lluvia": ("lluvia", {"fuerza": "0-1"}),
    "Vagon": ("un vagón de metro, a lo largo de x", {"largo": "4", "color": "#hex", "franja": "#hex",
                                                     "apagado": "0-1: gris y sin luces, un tren parado", "luces": "0-1"}),
    "Vias": ("vías de tren, a lo largo de x", {"largo": "30"}),
    "Anden": ("andén de estación, con su franja amarilla al frente", {"largo": "14", "fondo": "3", "alto": "0.45"}),
    "Forma": ("una primitiva SOLO para detalles chicos (una caja de luz, una línea, una base): máximo 2 por "
              "escena y nunca el centro de la escena",
              {"forma": "esfera|caja|cilindro|cono|capsula|dona|plano", "color": "#hex",
               "tamano": "número o [x, y, z]: la medida TOTAL", "brillo": "0-1", "opacidad": "0-1",
               "giro": "radianes"}),
}
# Todos aceptan además estos.
COMUNES = {"posicion": "[x, y, z] (x derecha, y arriba, z hacia la cámara)", "escala": "número",
           "rotacion": "[x, y, z] en radianes", "gira": "vueltas por segundo en radianes"}
MAX_FORMAS = 2
MAX_OBJETOS = 10

# Las 32 animaciones de los personajes de Kenney, menos las que no van en este
# canal: `die`, los `attack-*` y los `*-shoot`. No reconstruimos la muerte de
# nadie ni ponemos armas en manos de un muñeco: eso es lo que distingue una
# recreación de una recreación de mal gusto.
ANIMACIONES = {
    "static": "quieto, sin moverse", "idle": "de pie, respirando", "walk": "caminando",
    "sprint": "corriendo", "jump": "saltando", "fall": "cayendo de un salto", "crouch": "agachado",
    "sit": "sentado (ponlo sobre una silla)", "drive": "manejando (ponlo dentro del auto)",
    "pick-up": "levantando algo del piso", "emote-yes": "asintiendo, diciendo que sí",
    "emote-no": "negando con la cabeza", "holding-right": "sosteniendo algo con la derecha",
    "holding-left": "sosteniendo algo con la izquierda", "holding-both": "sosteniendo algo con las dos manos",
    "interact-right": "señalando o tocando algo a su derecha", "interact-left": "señalando a su izquierda",
    "wheelchair-sit": "en silla de ruedas",
}
# Luz de la escena. La escoge el guion entero y cada escena puede cambiarla.
AMBIENTES = {"noche": "calle de noche, azul", "calido": "interior cálido, velas", "anden": "luz blanca de estación",
             "oficina": "interior de oficina u oficina pública"}
# Las cámaras con nombre miran al centro (0,0,0) y sirven para un objeto solo;
# en una escena con gente casi siempre conviene la cámara libre.
CAMARAS = {"frente": "de frente, quieta", "acerca": "se acerca despacio", "aleja": "se aleja",
           "cerca": "close-up", "plano": "de frente, recta", "arriba": "desde arriba", "orbita": "rodea el centro"}


def modelos() -> dict[str, str]:
    try:
        return json.loads(MODELOS_INDICE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def tamanos() -> dict[str, list[float]]:
    try:
        return json.loads(TAMANOS_INDICE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _forma(nombre: str, tam: dict) -> str:
    """"ancho 1.8× su alto" para los modelos que no son más o menos cúbicos."""
    medida = tam.get(nombre)
    if not medida or medida[1] <= 0:
        return ""
    razon = max(medida[0], medida[2]) / medida[1]
    if razon >= 1.3:
        return f", ancho {razon:.1f}× su alto"
    if razon <= 0.45:
        return f", angosto: {razon:.1f}× su alto"
    return ""


def _catalogo() -> str:
    lineas = []
    for nombre, (que, props) in CATALOGO.items():
        lineas.append(f"  - {nombre}: {que}. " + ", ".join(f"{k} ({v})" for k, v in props.items()))
    lineas.append("  Todos aceptan además: " + ", ".join(f"{k} ({v})" for k, v in COMUNES.items()))
    tam = tamanos()
    por_paquete: dict[str, list[str]] = {}
    for nombre, que in modelos().items():
        por_paquete.setdefault(nombre.split("/")[0], []).append(f"{nombre} ({que}{_forma(nombre, tam)})")
    lineas.append("BIBLIOTECA (para Modelo y para el modelo de Personaje). Donde dice \"ancho N× su alto\", "
                  f"ese modelo con alto 1 mide N de ancho, y en pantalla solo caben {ANCHO_DE_PANTALLA}:")
    lineas += [f"  {', '.join(v)}" for v in por_paquete.values()]
    return "\n".join(lineas)


INSTRUCCION = r"""
Tienes un guion YA ESCRITO y aprobado. No lo toques: no cambies una palabra de la narración.
Lo único que vas a escribir es QUÉ SE VE en cada plano, en 3D, para que el video deje de verse
como un noticiero y dibuje lo que pasó.

EL GUION
<<GUION>>

QUÉ ESCRIBIR
Un archivo C:\Android_in\<<SLUG>>\escenas.json, así:
{"ambiente": "<uno de los ambientes>",
 "escenas": {
   "<id del plano>": {"visual": [...], "camara": ..., "etiquetas": [...], "claves": [...],
                      "ambiente": "<opcional, si ESTE plano cambia de luz>",
                      "evidencia": {"e": "<id de una pieza de evidencia>", "desde": 0.05, "hasta": 0.4}},
   ...}}
UNA escena por cada plano del guion, con su mismo id. El plano de identidad_cierre NO lleva
escena: ahí va el cierre de marca del canal.

CÓMO SE ARMA UNA ESCENA
- "visual": de 2 a <<MAXOBJ>> objetos del CATÁLOGO, cada uno {"objeto": "<nombre>", <props>}.
  Siempre un Suelo. Lo que la voz nombra tiene que estar en pantalla: si dice "la patrulla
  llegó", hay autos/police; si dice "los vecinos salieron", hay Multitud o varios Personaje.
- COMPÓN EN PROFUNDIDAD: el cuadro es vertical (1080x1920) y angosto. Pon las piezas en z
  distintas (unas cerca, otras al fondo) y no en fila a lo ancho: a lo ancho se salen. Lo que
  importa va entre x = -1.2 y 1.2. Los edificios, al fondo (z de -3 a -6).
- NADA TAPANDO AL SUJETO. En pantalla caben unas <<ANCHO>> unidades de ancho. El render escala
  un Modelo por su ALTO, así que una pieza ancha queda más ancha todavía: la barda
  (colonia/fence, ancho 1.8× su alto) con alto 1.4 mide 2.5 y se ve como una pared de color que
  tapa el video entero. Pasó el 11/11/2026. Antes de poner un modelo con alto, multiplica su
  alto por el "ancho N× su alto" del catálogo: si pasa de <<ANCHO>>, bájale el alto o mándalo
  al fondo (z ≤ <<FONDO>>). Bardas, paredes, rejas y camiones: al fondo o chiquitos, nunca
  entre la cámara y la persona de la que habla la voz.
- "camara": {"desde": {"pos": [x,y,z], "mira": [x,y,z]}, "hasta": {...}, "entre": [0.2, 0.8]}
  para que se mueva, o {"pos": …, "mira": …} quieta, o una con nombre: <<CAMARAS>>.
  Una persona mide 0.9: la cámara va a y entre 1.0 y 1.8, a z entre 4 y 9, mirando a y ≈ 0.7.
  Más cerca de z = 4 no se ve de cuerpo entero.
- NO TAPES EL TEXTO: los subtítulos van arriba (alto 300 a 530 px), el letrero abajo (1330) y
  el sello de evidencia a media pantalla (640). Deja el centro del cuadro para la escena y no
  levantes objetos por encima de y = 3.
- "etiquetas": máximo DOS por escena, {"titulo": "…", "subtitulo": "…", "desde": 0.1, "hasta": 0.5}
  (desde/hasta: 0 = empieza la escena, 1 = termina). El titulo, 34 letras o menos; el subtitulo,
  50 o menos. Aquí van los datos duros del guion (el nombre con cargo, la cifra, la fecha).
- "claves": de 2 a 4 palabras SUELTAS de ESE plano, tal cual las dice la voz, que se resaltan
  en el subtítulo.
- Cualquier prop numérico (y posicion o escala) se puede ANIMAR dentro de la escena:
    {"de": 0, "a": 1, "desde": 0.55, "hasta": 0.85}      -> cambia entre el 55 % y el 85 %
    {"de": [-2,0,0], "a": [2,0,0], "desde": 0, "hasta": 0.6}  -> se mueve
  Pon el cambio en el momento de la frase que lo dice.

LA EVIDENCIA REAL (esto es lo que hace que el canal sea creíble)
Las piezas del guion (<<EVIDENCIA>>) NO se reconstruyen: se enseñan como sello, con su fuente.
Pon "evidencia" en 2 a <<SELLOS>> planos, los que dicen el dato que esa pieza respalda, con
"desde"/"hasta" cortos (0.3 de la escena basta). NO pongas evidencia en todos los planos: el
sello ocupa media pantalla y, puesto en todos, no se ve la escena que acabas de armar.

LO QUE NO SE HACE, NUNCA
1. Las VÍCTIMAS no salen como personajes. Van como Velas (una por persona), como un objeto
   suyo (una maleta, una silla vacía) o como ausencia. Un muñequito haciendo de una persona
   que murió es de mal gusto y no va.
2. No reconstruyas el momento de la violencia: ni golpes, ni armas, ni cuerpos. Esas
   animaciones no están en la lista a propósito. El plano del hecho se cuenta con lo que queda
   (la puerta, el cuarto vacío, la calle cerrada) o con quien mira.
3. Nada de caras de personas reales: los personajes son genéricos, estilo juguete. A un
   funcionario se le pone con etiqueta (su nombre y cargo), no con su cara.
4. Nada que no esté en el CATÁLOGO: lo que no existe, el render no lo dibuja y se descarta.

ANIMACIONES (para Personaje y Multitud)
<<ANIMACIONES>>

AMBIENTES
<<AMBIENTES>>

CATÁLOGO (usa SOLO esto)
<<CATALOGO>>

EJEMPLO DE DOS ESCENAS
 "p01": {"visual": [
     {"objeto": "Suelo", "color": "#1C1F26"},
     {"objeto": "Personaje", "modelo": "personajes/character-male-b", "animacion": "walk", "giro": 1.5708,
      "posicion": {"de": [-1.8, 0, 0], "a": [1.9, 0, 0], "desde": 0, "hasta": 0.62}},
     {"objeto": "Modelo", "modelo": "personajes/item-luggage", "alto": 0.28, "posicion": [-2.05, 0, 0.12]},
     {"objeto": "Modelo", "modelo": "ciudad/building-g", "alto": 3.4, "posicion": [2.4, 0, -3.5]},
     {"objeto": "Modelo", "modelo": "calles/light-square", "alto": 1.9, "posicion": [-2.0, 0, -1.5]}],
   "camara": {"desde": {"pos": [-1.0, 1.15, 5.0], "mira": [-1.0, 0.7, 0]},
              "hasta": {"pos": [1.4, 1.35, 5.6], "mira": [1.6, 0.9, -0.5]}},
   "etiquetas": [{"titulo": "Rubén Espinosa", "subtitulo": "fotoperiodista · se fue de Veracruz",
                  "desde": 0.04, "hasta": 0.48}],
   "claves": ["vigilaban", "Narvarte"]},
 "p02": {"ambiente": "calido", "visual": [
     {"objeto": "Suelo", "color": "#1A120C"},
     {"objeto": "Modelo", "modelo": "muebles/table", "alto": 0.5},
     {"objeto": "Velas", "cantidad": 1, "posicion": [-0.56, 0.7, 0], "fuerza": 1},
     {"objeto": "Velas", "cantidad": 1, "posicion": [-0.28, 0.7, 0],
      "fuerza": {"de": 0, "a": 1, "desde": 0.04, "hasta": 0.08}}],
   "camara": {"desde": {"pos": [0, 1.5, 4.8], "mira": [0, 0.75, 0]},
              "hasta": {"pos": [0, 1.3, 3.9], "mira": [0, 0.8, 0]}},
   "etiquetas": [{"titulo": "Nadia Vera", "subtitulo": "también había dejado Veracruz", "desde": 0.04, "hasta": 0.38}],
   "claves": ["dieciocho"]}
(las cuatro víctimas son cuatro velas que se encienden mientras la voz las nombra, no cuatro muñecos)

CÓMO TRABAJAR (cada respuesta tuya relee todo lo anterior: menos respuestas = menos costo)
- Escribe el archivo COMPLETO una sola vez (Write) y córrele la revisión:
      <<REVISAR>>
  Revisa que cada objeto, prop, modelo, animación y cámara exista, y que no falte ningún plano.
  Si marca algo, corrígelo TODO con Edit en la MISMA respuesta y vuelve a correrla.
- No busques en internet ni abras otros archivos: todo lo que necesitas está aquí.

AL TERMINAR responde SOLO este bloque JSON:
{"escenas": {"planos": <cuántos>, "nota": "una línea: qué se ve en el video"}}
""".strip()


def instruccion(slug: str, guion: dict) -> str:
    """El prompt del paso de escenas de UN video."""
    planos = []
    for p in guion.get("planos") or []:
        if p.get("seccion") == "identidad_cierre":
            planos.append(f'  {p.get("id")} [identidad_cierre: NO lleva escena, va el cierre de marca]')
            continue
        planos.append(f'  {p.get("id")} ({p.get("seccion", "")}): {p.get("narracion", "")}')
    evidencia = [f'{e.get("id")} ({e.get("tipo")}: {e.get("fuente") or e.get("titulo") or e.get("buscar_wikimedia") or ""})'
                 for e in guion.get("evidencia") or [] if str(e.get("id", "")).startswith("e")]
    texto = f'titulo: {guion.get("titulo", "")}\nplanos:\n' + "\n".join(planos)
    return (INSTRUCCION.replace("<<GUION>>", texto).replace("<<SLUG>>", slug)
            .replace("<<EVIDENCIA>>", ", ".join(evidencia) or "no hay piezas de evidencia en este guion")
            .replace("<<MAXOBJ>>", str(MAX_OBJETOS)).replace("<<SELLOS>>", str(MAX_SELLOS))
            .replace("<<ANCHO>>", str(ANCHO_DE_PANTALLA)).replace("<<FONDO>>", str(FONDO_Z))
            .replace("<<CATALOGO>>", _catalogo())
            .replace("<<ANIMACIONES>>", "; ".join(f"{k} ({v})" for k, v in ANIMACIONES.items()))
            .replace("<<AMBIENTES>>", "; ".join(f"{k} ({v})" for k, v in AMBIENTES.items()))
            .replace("<<CAMARAS>>", "; ".join(f"{k} ({v})" for k, v in CAMARAS.items()))
            .replace("<<REVISAR>>", REVISAR.format(slug=slug)))


REVISAR = "C:/dato-mata-gato-bot/.venv/Scripts/python.exe -m dato_mata_gato_bot.herramientas_guion escenas {slug}"


# --- Revisión sin Claude --------------------------------------------------------

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


def _norma(w: str) -> str:
    return re.sub(r"[^\wáéíóúüñ]", "", str(w).lower())


TOPE_Y = 3.0


def _eje(pos, i: int) -> float:
    """La coordenada i de una posicion, fija o animada (la más cercana a la cámara)."""
    if isinstance(pos, dict):
        valores = [pos.get("de"), pos.get("a")]
        return max((x[i] for x in valores if isinstance(x, list) and len(x) == 3 and _es_num(x[i])), default=0.0)
    return float(pos[i]) if isinstance(pos, list) and len(pos) == 3 and _es_num(pos[i]) else 0.0


def _fijo(x, por_defecto: float = 0.0) -> float:
    """Un prop numérico; si está animado, su valor más grande."""
    if isinstance(x, dict):
        return max((float(v) for v in (x.get("de"), x.get("a")) if _es_num(v)), default=por_defecto)
    return float(x) if _es_num(x) else por_defecto


def tapa_el_cuadro(v: dict, tam: dict) -> str:
    """"" si el objeto cabe; si no, cuánto mide y por qué estorba.

    El render escala por el ALTO: una barda de 0.48 x 0.27 con alto 1.4 queda
    de 2.5 de ancho, más que el cuadro entero, y delante del sujeto es una
    pared de color (11/11/2026, el plano de la reja de Juárez).
    """
    medida = tam.get(v.get("modelo"))
    if not medida or medida[1] <= 0 or _eje(v.get("posicion"), 2) <= FONDO_Z:
        return ""
    escala = _fijo(v.get("escala"), 1.0) or 1.0
    if v.get("ancho") is not None:
        ancho = _fijo(v["ancho"]) * escala
        alto = ancho * medida[1] / max(medida[0], medida[2], 1e-3)
    else:
        alto = _fijo(v.get("alto"), 1.0) * escala
        ancho = alto * max(medida[0], medida[2]) / medida[1]
    if alto < ALTO_QUE_TAPA or ancho <= ANCHO_DE_PANTALLA:
        return ""
    cabe = ANCHO_DE_PANTALLA * medida[1] / max(medida[0], medida[2])
    return (f'{v["modelo"]} queda de {ancho:.1f} de ancho (mide {medida[0]}x{medida[1]}x{medida[2]} y el render '
            f"escala por el alto): tapa el cuadro. Bájale el alto a {cabe:.1f} o mándalo al fondo (z ≤ {FONDO_Z})")


def problemas_de_escena(eid: str, e: dict, narracion: str, evidencias: set[str]) -> list[str]:
    out = []
    if not isinstance(e, dict):
        return [f"{eid}: la escena tiene que ser un objeto JSON"]
    visual = e.get("visual")
    if not isinstance(visual, list) or not 1 <= len(visual) <= MAX_OBJETOS:
        out.append(f'{eid}: "visual" lleva de 1 a {MAX_OBJETOS} objetos del catálogo')
        visual = visual if isinstance(visual, list) else []
    biblioteca, tam = modelos(), tamanos()
    for v in visual:
        nombre = v.get("objeto") if isinstance(v, dict) else None
        if nombre not in CATALOGO:
            out.append(f'{eid}: el objeto "{nombre}" no existe; usa uno del catálogo')
            continue
        validos = set(CATALOGO[nombre][1]) | set(COMUNES) | {"objeto"}
        if malos := sorted(set(v) - validos):
            out.append(f'{eid}: {nombre} no tiene {", ".join(malos)} (tiene: '
                       f'{", ".join(sorted(validos - {"objeto"}))})')
        if nombre in ("Modelo", "Personaje") and v.get("modelo") not in biblioteca:
            parecidos = difflib.get_close_matches(str(v.get("modelo")), list(biblioteca), n=3, cutoff=0.5)
            out.append(f'{eid}: el modelo "{v.get("modelo")}" no está en la biblioteca'
                       + (f' (¿{", ".join(parecidos)}?)' if parecidos else ""))
        elif nombre == "Personaje" and not str(v.get("modelo", "")).startswith("personajes/"):
            out.append(f'{eid}: Personaje necesita un modelo de personajes/… (tiene "{v.get("modelo")}")')
        if (anim := v.get("animacion")) is not None and anim not in ANIMACIONES:
            dura = anim in ("die", "attack-melee-right", "attack-melee-left", "attack-kick-right",
                            "attack-kick-left", "holding-right-shoot", "holding-left-shoot", "holding-both-shoot")
            out.append(f'{eid}: la animación "{anim}" ' + ("no se usa en este canal: no reconstruimos "
                       "la violencia ni la muerte de nadie" if dura else f"no existe (van: {', '.join(ANIMACIONES)})"))
        for k, x in v.items():
            if not _valor_ok(x):
                out.append(f'{eid}: {nombre}.{k} está mal animado: {{"de": 0, "a": 1, "desde": 0.2, '
                           '"hasta": 0.6}, con desde/hasta entre 0 y 1')
        if (y := _eje(v.get("posicion"), 1)) > TOPE_Y:
            out.append(f"{eid}: {nombre} está a y = {y:.1f}; nada por encima de y = {TOPE_Y:.0f} "
                       "(se va a la franja de los subtítulos)")
        if nombre == "Modelo" and (aviso := tapa_el_cuadro(v, tam)):
            out.append(f"{eid}: {aviso}")
    if sum(isinstance(v, dict) and v.get("objeto") == "Forma" for v in visual) > MAX_FORMAS:
        out.append(f"{eid}: más de {MAX_FORMAS} Forma: con primitivas sueltas la escena se ve como figuras "
                   "geométricas; usa modelos de la biblioteca")
    if not _camara_ok(e.get("camara")):
        out.append(f'{eid}: "camara" tiene que ser una de {", ".join(CAMARAS)}, {{"pos": [x,y,z], "mira": [x,y,z]}} '
                   'o {"desde": {...}, "hasta": {...}}')
    if (amb := e.get("ambiente")) is not None and amb not in AMBIENTES:
        out.append(f'{eid}: el ambiente "{amb}" no existe (van: {", ".join(AMBIENTES)})')
    etiquetas = e.get("etiquetas") or []
    if len(etiquetas) > 2:
        out.append(f"{eid}: máximo dos etiquetas por escena")
    for et in etiquetas:
        if not isinstance(et, dict) or not str(et.get("titulo") or "").strip() or len(str(et.get("titulo"))) > 34:
            out.append(f'{eid}: la etiqueta "{(et or {}).get("titulo")}" va de 1 a 34 letras')
            continue
        if len(str(et.get("subtitulo") or "")) > 50:
            out.append(f'{eid}: el subtítulo de "{et.get("titulo")}" pasa de 50 letras')
        if not (_es_num(et.get("desde")) and _es_num(et.get("hasta")) and 0 <= et["desde"] < et["hasta"] <= 1):
            out.append(f'{eid}: la etiqueta "{et.get("titulo")}" necesita desde < hasta, entre 0 y 1')
    dichas = {_norma(w) for w in narracion.split()}
    claves = e.get("claves") or []
    if not 1 <= len(claves) <= 4:
        out.append(f'{eid}: "claves" lleva de 2 a 4 palabras sueltas de ESE plano')
    if fuera := [c for c in claves if _norma(c) not in dichas]:
        out.append(f'{eid}: las claves {", ".join(map(str, fuera))} no son palabras que diga la voz en este '
                   "plano: cada clave es UNA palabra, tal cual se dice")
    ev = e.get("evidencia")
    if ev is not None:
        if not isinstance(ev, dict) or ev.get("e") not in evidencias:
            out.append(f'{eid}: "evidencia" apunta a {json.dumps(ev, ensure_ascii=False)}, que no es una pieza '
                       f'de este guion ({", ".join(sorted(evidencias)) or "no hay"})')
        else:
            for k in ("desde", "hasta"):
                if k in ev and not (_es_num(ev[k]) and 0 <= ev[k] <= 1):
                    out.append(f'{eid}: evidencia.{k} va entre 0 y 1')
    return out


def problemas(plan: dict, guion: dict) -> list[str]:
    """Todo lo que le falta al plan de escenas para que el video salga."""
    out = []
    if not isinstance(plan, dict):
        return ["el archivo tiene que ser un objeto JSON con \"ambiente\" y \"escenas\""]
    if (amb := plan.get("ambiente")) and amb not in AMBIENTES:
        out.append(f'"ambiente" no existe: {amb} (van: {", ".join(AMBIENTES)})')
    escenas = plan.get("escenas")
    if not isinstance(escenas, dict) or not escenas:
        return out + ['faltan las "escenas": {"<id del plano>": {...}}']
    planos = {p.get("id"): p for p in guion.get("planos") or []}
    piden = {i for i, p in planos.items() if p.get("seccion") != "identidad_cierre"}
    if faltan := sorted(piden - set(escenas)):
        out.append(f"faltan escenas para estos planos: {', '.join(faltan)}")
    if sobran := sorted(set(escenas) - set(planos)):
        out.append(f"estas escenas no son de ningún plano del guion: {', '.join(sobran)}")
    evidencias = {str(e.get("id")) for e in guion.get("evidencia") or [] if str(e.get("id", "")).startswith("e")}
    con_evidencia = 0
    for eid, e in escenas.items():
        if eid not in planos:
            continue
        out += problemas_de_escena(eid, e, str(planos[eid].get("narracion", "")), evidencias)
        con_evidencia += bool(isinstance(e, dict) and e.get("evidencia"))
    if evidencias and not con_evidencia:
        out.append("ninguna escena enseña evidencia real: pon 2 a 4 sellos donde la voz dice el dato")
    if con_evidencia > MAX_SELLOS:
        out.append(f"{con_evidencia} escenas llevan sello de evidencia y el tope son {MAX_SELLOS}: el sello "
                   "ocupa media pantalla, y en todos los planos no deja ver la escena. Déjalo donde la voz "
                   "dice el dato que esa pieza respalda")
    return out


# --- Descarte (lo que no existe, no llega al render) ----------------------------

def limpiar(plan: dict, guion: dict) -> tuple[dict, list[str]]:
    """El plan con SOLO lo que el render sabe dibujar, y qué se tiró.

    Es la red de abajo: la revisión le pide a Claude que lo arregle, pero un
    prop inventado que se cuele no puede tumbar un video entero.
    """
    tirado: list[str] = []
    if not isinstance(plan, dict):
        return {"escenas": {}}, ["el plan no era un objeto JSON"]
    biblioteca = modelos()
    planos = {p.get("id") for p in guion.get("planos") or []}
    evidencias = {str(e.get("id")) for e in guion.get("evidencia") or [] if str(e.get("id", "")).startswith("e")}
    limpio = {"ambiente": plan.get("ambiente") if plan.get("ambiente") in AMBIENTES else "noche", "escenas": {}}
    escenas = plan.get("escenas")
    if not isinstance(escenas, dict):
        return limpio, [f'"escenas" tiene que ser {{"<id del plano>": {{...}}}}, no {type(escenas).__name__}']
    for eid, e in escenas.items():
        if eid not in planos or not isinstance(e, dict):
            tirado.append(f"{eid}: no es un plano del guion")
            continue
        visual = []
        for v in e.get("visual") or []:
            nombre = v.get("objeto") if isinstance(v, dict) else None
            if nombre not in CATALOGO:
                tirado.append(f"{eid}: objeto {nombre}")
                continue
            if nombre in ("Modelo", "Personaje") and v.get("modelo") not in biblioteca:
                tirado.append(f'{eid}: modelo {v.get("modelo")}')
                continue
            validos = set(CATALOGO[nombre][1]) | set(COMUNES) | {"objeto"}
            pieza = {}
            for k, x in v.items():
                if k not in validos:
                    tirado.append(f"{eid}: {nombre}.{k}")
                elif not _valor_ok(x):
                    tirado.append(f"{eid}: {nombre}.{k} mal animado")
                elif k == "animacion" and x not in ANIMACIONES:
                    tirado.append(f"{eid}: animación {x}")
                else:
                    pieza[k] = x
            visual.append(pieza)
        if len(visual) > MAX_OBJETOS:
            tirado.append(f"{eid}: {len(visual) - MAX_OBJETOS} objetos de más")
            visual = visual[:MAX_OBJETOS]
        nueva: dict = {"visual": visual or [{"objeto": "Suelo"}]}
        if _camara_ok(e.get("camara")) and e.get("camara") is not None:
            nueva["camara"] = e["camara"]
        elif e.get("camara") is not None:
            tirado.append(f"{eid}: cámara")
        if e.get("ambiente") in AMBIENTES:
            nueva["ambiente"] = e["ambiente"]
        etiquetas = [et for et in (e.get("etiquetas") or [])
                     if isinstance(et, dict) and str(et.get("titulo") or "").strip()
                     and _es_num(et.get("desde")) and _es_num(et.get("hasta")) and et["desde"] < et["hasta"]]
        if etiquetas:
            nueva["etiquetas"] = [{**et, "titulo": str(et["titulo"])[:34],
                                   **({"subtitulo": str(et["subtitulo"])[:50]} if et.get("subtitulo") else {})}
                                  for et in etiquetas[:2]]
        if claves := [str(c) for c in (e.get("claves") or [])][:4]:
            nueva["claves"] = claves
        ev = e.get("evidencia")
        if isinstance(ev, dict) and ev.get("e") in evidencias:
            nueva["evidencia"] = {k: ev[k] for k in ("e", "desde", "hasta", "alto") if k in ev}
        elif ev is not None:
            tirado.append(f'{eid}: evidencia {(ev or {}).get("e")}')
        limpio["escenas"][eid] = nueva
    return limpio, tirado


def resumen_visual(plan: dict) -> str:
    """Lo que se ve en el video, para el aviso de Telegram."""
    escenas = (plan or {}).get("escenas") or {}
    usados: dict[str, int] = {}
    for e in escenas.values():
        for v in (e or {}).get("visual") or []:
            if isinstance(v, dict) and v.get("objeto"):
                usados[v["objeto"]] = usados.get(v["objeto"], 0) + 1
    sellos = sum(1 for e in escenas.values() if (e or {}).get("evidencia"))
    etiquetas = sum(len((e or {}).get("etiquetas") or []) for e in escenas.values())
    return (f"escenas 3D: {len(escenas)} escenas, " + ", ".join(f"{k}×{v}" for k, v in sorted(usados.items()))
            + f" · {etiquetas} etiquetas · {sellos} sellos de evidencia")
