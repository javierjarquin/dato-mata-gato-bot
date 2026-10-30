"""Revisión de un guion de true crime ANTES de generarlo, sin Claude.

Las reglas de nombres, lugares y evidencia (29/09/2026) están en la
instrucción que usa Claude, pero una instrucción se puede ignorar: el lote
del 26/09 salió con guiones sin UN SOLO nombre propio. Esto comprueba que se
cumplan; el bot le devuelve a Claude lo que falle para una sola ronda de
corrección, y lo que siga fallando no entra al lote.
"""

import re

_MAYUS = "A-ZÁÉÍÓÚÑ"
_PALABRA = rf"[{_MAYUS}][\wáéíóúñü]+"
# Sin "y": "Bernardo Benítez y José Alfredo González" son DOS personas.
_CONECTOR = r"(?:de |del |de la |de los |la )"
# Nombre de varias palabras: "José Benítez de la O", "Marcos Conde Hernández".
_NOMBRE_COMPUESTO = re.compile(rf"{_PALABRA}(?: {_CONECTOR}?(?:{_PALABRA}|O\b))+")
# "en Tierra Blanca", "en la colonia Guerrero", "en Iguala".
# "en Iguala", "En la colonia Doctores", "en la Cuauhtémoc", "en avenida Niños Héroes",
# "en el Eje Dos Norte". El 12/10/2026 la forma vieja (solo "en" minúscula y sin artículo)
# tiró 2 guiones buenos del piloto de cercanía que sí decían la colonia.
_LUGAR = re.compile(
    rf"\b[Ee]n (?:(?:la |el )?(?:colonia|alcaldía|municipio de|barrio de|avenida|calle|bulevar|"
    rf"calzada|supermanzana|fraccionamiento)\s+|la |el )?({_PALABRA}(?: {_CONECTOR}?{_PALABRA})*)")

ESTADOS = {
    "aguascalientes", "baja california", "baja california sur", "campeche", "chiapas",
    "chihuahua", "ciudad de mexico", "coahuila", "colima", "durango", "guanajuato",
    "guerrero", "hidalgo", "jalisco", "estado de mexico", "mexico", "michoacan", "morelos",
    "nayarit", "nuevo leon", "oaxaca", "puebla", "queretaro", "quintana roo",
    "san luis potosi", "sinaloa", "sonora", "tabasco", "tamaulipas", "tlaxcala",
    "veracruz", "yucatan", "zacatecas",
}
# Primeras palabras de nombres compuestos que no son personas (sin acentos:
# se comparan contra _sin_acentos).
_NO_NOMBRE = {"aqui", "te", "el", "la", "los", "las", "un", "una", "dato", "gato", "cndh",
              "policia", "fiscalia", "gobierno", "ejercito", "marina", "guardia",
              "seguridad", "secretaria", "procuraduria", "comision", "suprema", "corte",
              "juzgado", "tribunal", "centro", "estado", "cartel", "congreso", "senado",
              "universidad", "hospital", "instituto", "presidencia", "sala"}
_LUGAR_PREFIJO = re.compile(
    r"(playa|paso|ciudad|san|santa|puerto|rancho|tierra|valle|villa|colonia|cerro|rio|"
    r"lago|isla|nuevo|nueva|el|la|los|las)\b")
_MIN_NOMBRES = 3
_MIN_REALES = 3
_REALES = {"lugar", "persona", "documento", "prensa"}
# Los de VisualTipo en illustrated-narrator (domain/entities/plano.py). Si allá
# se agrega uno, aquí también: esta lista solo adelanta el mismo rechazo.
_VISUAL_TIPOS = {"imagen_ia", "video_stock", "animacion_3d", "mapa_animado",
                 "grafico_movimiento", "cartel_texto", "archivo_historico"}


def _sin_acentos(t: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _contenido(guion: dict) -> list[dict]:
    return [p for p in guion.get("planos", []) if p.get("seccion") != "identidad_cierre"]


def _personas_en(texto: str) -> list[str]:
    """Nombres compuestos del texto que no son lugares ni instituciones."""
    personas = []
    for m in _NOMBRE_COMPUESTO.finditer(texto):
        palabras = m.group(0).split()
        # Palabra que abre la frase y no es parte del nombre ("Gobernaba Javier
        # Duarte"): si la que sigue también va con mayúscula, se descarta.
        inicio = m.start() == 0 or texto[:m.start()].rstrip()[-1:] in ".!?¿¡"
        if inicio and len(palabras) > 2 and palabras[0].lower().endswith(("aba", "ó", "ía", "ron")):
            palabras = palabras[1:]
        nombre = " ".join(palabras)
        limpio = _sin_acentos(nombre)
        if limpio.split()[0] in _NO_NOMBRE or limpio in ESTADOS or _LUGAR_PREFIJO.match(limpio):
            continue
        personas.append(nombre)
    return personas


def nombres_de_persona(guion: dict) -> set[str]:
    return {n for p in _contenido(guion) for n in _personas_en(p.get("narracion", ""))}


def lugares_exactos(guion: dict) -> list[str]:
    """Lugares más chicos que un estado, dichos en los primeros planos."""
    lugares = []
    for p in _contenido(guion)[:3]:
        for m in _LUGAR.finditer(p.get("narracion", "")):
            lugar = m.group(1)
            if _sin_acentos(lugar) not in ESTADOS and _sin_acentos(lugar).split()[0] not in _NO_NOMBRE:
                lugares.append(lugar)
    return lugares


def problemas(guion: dict, min_nombres: int = _MIN_NOMBRES) -> list[str]:
    """Lo que el guion no cumple, en frases que se le pueden pasar a Claude.

    `min_nombres=0` para la fórmula de cercanía (Cancún, 12/10/2026): un video
    del precio de la gasolina no tiene tres personas con nombre y apellido, y
    no hay que inventárselas. Lugar exacto y evidencia real sí se exigen.
    """
    out = []
    nombres = nombres_de_persona(guion)
    if len(nombres) < min_nombres:
        out.append(f"solo {len(nombres)} nombre(s) de persona con nombre y apellido "
                   f"({', '.join(sorted(nombres)) or 'ninguno'}); hacen falta al menos "
                   f"{_MIN_NOMBRES}: víctimas, funcionarios, acusados")
    if not lugares_exactos(guion):
        out.append("no dice el lugar exacto en los primeros planos: municipio o colonia "
                   "y estado (\"en Tierra Blanca, Veracruz\"), no solo el estado")
    evid = {p.get("id"): p.get("tipo") for p in guion.get("evidencia", [])}
    reales = sum(1 for t in evid.values() if t in _REALES)
    if reales < _MIN_REALES:
        out.append(f"evidencia con {reales} pieza(s) reales (lugar, persona, documento o "
                   f"prensa); hacen falta al menos {_MIN_REALES}. Si el caso no las tiene, "
                   "cámbialo por otro")
    sin_pieza = [p.get("id") for p in _contenido(guion)
                 if not [e for e in p.get("visual", {}).get("evidencia", []) if e in evid]]
    if evid and sin_pieza:
        out.append(f"planos sin evidencia asignada: {', '.join(sin_pieza)}")
    # visual.tipo lo valida illustrated-narrator al cargar el guion, pero hasta
    # el 15/10/2026 el error salía recién al generar: un guion con "archivo" en
    # vez de "archivo_historico" quemaba los dos intentos del video y volvía
    # como traceback en el estado del lote. Aquí se atrapa antes, y en una frase
    # que Claude puede corregir.
    malos = {p.get("id"): t for p in guion.get("planos", [])
             if (t := (p.get("visual") or {}).get("tipo")) and t not in _VISUAL_TIPOS}
    if malos:
        out.append("visual.tipo inválido en " + ", ".join(f"{k} (\"{v}\")" for k, v in malos.items())
                   + ". Los únicos válidos son: " + ", ".join(sorted(_VISUAL_TIPOS))
                   + ". Para evidencia real es \"archivo_historico\"; el cierre es "
                   "\"grafico_movimiento\"")
    for p in _contenido(guion):
        texto = p.get("narracion", "")
        for frase in re.split(r"(?<=[.!?])\s+", texto):
            if len(_personas_en(frase)) > 2:
                out.append(f"{p.get('id')}: más de dos nombres en una frase (la voz se "
                           f"come uno): \"{frase[:80]}\"")
        tl = re.findall(r"\bTl[\wáéíóúñ]+", texto)
        if tl:
            out.append(f"{p.get('id')}: la voz no puede decir {', '.join(tl)}; va en "
                       "texto_en_pantalla y en la narración el estado o un lugar cercano")
    return out
