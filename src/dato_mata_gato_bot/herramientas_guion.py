"""Herramientas que Claude corre con Bash mientras escribe un guion (13/10/2026).

Nacen de medir una sesión de la fábrica (guion-cdmx-socavones-hundimiento,
2.4 M tokens en 27 pasos): 6 pasos se fueron en buscar fotos en Wikimedia de
dos en dos con WebFetch, y otros 6 en revisar el guion a mano con PowerShell y
corregirlo con Edit tras Edit. Cada paso relee TODO el contexto (~90-130k a esa
altura), así que esos 12 pasos eran más de la mitad del gasto. Aquí se hace lo
mismo en UNA llamada cada uno, sin gastar tokens de Claude en el trabajo:

    python -m dato_mata_gato_bot.herramientas_guion fotos "consulta 1" "consulta 2" ...
    python -m dato_mata_gato_bot.herramientas_guion revisar <slug>

`revisar` junta las reglas que antes se descubrían tarde (al generar el video
o en la ronda de corrección): la fórmula, el largo, la foto que no existe, la
nota cuyo titular no nombra el caso.
"""

import html
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor

import requests

from dato_mata_gato_bot import evidencia, revision_guion

API = "https://commons.wikimedia.org/w/api.php"
NAVEGADOR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
POR_CONSULTA = 6


def _limpio(t: str, n: int) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t or ""))).strip()[:n]


def _info(titulos: list[str]) -> dict:
    """Tamaño, fecha y descripción de cada archivo (None si no existe)."""
    out = {}
    for i in range(0, len(titulos), 40):
        r = requests.get(API, headers=evidencia.UA, timeout=30, params={
            "action": "query", "titles": "|".join(titulos[i:i + 40]), "prop": "imageinfo",
            "iiprop": "size|extmetadata", "format": "json", "formatversion": 2}).json()
        normal = {n["to"]: n["from"] for n in r.get("query", {}).get("normalized", [])}
        for p in r.get("query", {}).get("pages", []):
            pedido = normal.get(p["title"], p["title"])
            if p.get("missing") or not p.get("imageinfo"):
                out[pedido] = None
                continue
            ii = p["imageinfo"][0]
            meta = ii.get("extmetadata", {})
            out[pedido] = {
                "titulo": p["title"], "tam": f"{ii.get('width')}x{ii.get('height')}",
                "fecha": (re.findall(r"(?:19|20)\d\d", _limpio(meta.get("DateTimeOriginal", {}).get("value", ""), 80)) or [""])[0],
                "desc": _limpio(meta.get("ImageDescription", {}).get("value", ""), 140)}
    return out


def fotos(consultas: list[str]) -> str:
    lineas = []
    for q in consultas:
        r = requests.get(API, headers=evidencia.UA, timeout=30, params={
            "action": "query", "list": "search", "srnamespace": 6, "srlimit": 12,
            "format": "json", "srsearch": q}).json()
        titulos = [h["title"] for h in r.get("query", {}).get("search", [])
                   if re.search(r"\.(jpe?g|png)$", h["title"], re.IGNORECASE)][:POR_CONSULTA]
        lineas.append(f'## "{q}"')
        if not titulos:
            lineas.append("  (nada: prueba con menos palabras o usa otra nota de prensa)")
            continue
        info = _info(titulos)
        for t in titulos:
            i = info.get(t)
            if i:
                lineas.append(f"  {i['titulo']} | {i['tam']} | {i['fecha'] or 's/f'} | {i['desc'] or '(sin descripción)'}")
    lineas.append("\nUsa el nombre EXACTO (con 'File:'). Si la descripción no muestra lo que dices, no la uses.")
    return "\n".join(lineas)


# --- revisar -----------------------------------------------------------------

def _palabras(t: str) -> int:
    return len(re.findall(r"[\wáéíóúñü]+", t or "", re.IGNORECASE))


def _titulares(url: str) -> tuple[str, list[str]]:
    """('' u error, [h1, og:title, title]) de la página, sin navegador."""
    try:
        r = requests.get(url, headers=NAVEGADOR, timeout=25)
    except requests.RequestException as exc:
        return f"no abre ({type(exc).__name__})", []
    if r.status_code >= 400:
        return f"HTTP {r.status_code}", []
    t = r.text
    cands = re.findall(r"<h1[^>]*>(.*?)</h1>", t, re.S | re.I)[:3]
    cands += re.findall(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', t, re.I)
    cands += re.findall(r"<title[^>]*>(.*?)</title>", t, re.S | re.I)[:1]
    return "", [_limpio(c, 200) for c in cands if _limpio(c, 200)]


def problemas_de_forma(guion: dict) -> list[str]:
    out = []
    planos = guion.get("planos", [])
    ids = [p.get("id") for p in planos]
    if ids != [f"p0{i}" for i in range(9)]:
        out.append(f"los planos tienen que ser p00 a p08, en orden (hay: {', '.join(map(str, ids))})")
    total = sum(_palabras(p.get("narracion", "")) for p in planos)
    if not 120 <= total <= 190:
        out.append(f"la narración tiene {total} palabras; tienen que ser 120 a 190")
    for p in planos:
        texto = p.get("narracion", "")
        if p.get("id") == "p00" and _palabras(texto) > 12:
            out.append(f"p00 tiene {_palabras(texto)} palabras; máximo 12")
        if re.search(r"\d", texto):
            out.append(f"{p.get('id')}: hay cifras con número ({', '.join(re.findall(r'[0-9][0-9.,]*', texto))}); "
                       "van en palabras")
        for frase in re.split(r"(?<=[.!?¿¡])\s+", texto):
            if _palabras(frase) > 20:
                out.append(f"{p.get('id')}: frase de {_palabras(frase)} palabras (máximo 20): \"{frase[:70]}…\"")
    return out


def problemas_de_evidencia(guion: dict) -> list[str]:
    out = []
    piezas = guion.get("evidencia", [])
    fotos_ = [e["wikimedia"] if e["wikimedia"].startswith("File:") else f"File:{e['wikimedia']}"
              for e in piezas if e.get("wikimedia")]
    if any(e.get("buscar_wikimedia") for e in piezas):
        out.append("no uses buscar_wikimedia: pon el nombre exacto en \"wikimedia\"")
    if fotos_:
        info = _info(fotos_)
        out += [f"la foto {f} no existe en Wikimedia Commons" for f in fotos_ if not info.get(f)]
    claves = evidencia.claves_del_caso(guion)
    patron = [re.compile(rf"\b{re.escape(k)}\b") for k in claves]
    for e in piezas:
        if e.get("tipo") != "prensa" or not e.get("url"):
            continue
        error, titulares = _titulares(e["url"])
        if error.startswith(("HTTP 401", "HTTP 403", "HTTP 429", "HTTP 503")):
            continue  # bloqueo anti-bot: la captura real usa un navegador y suele pasar
        if error:
            out.append(f"{e.get('id')}: la nota {e['url']} {error}; cambia el enlace o la pieza")
            continue
        planos = [revision_guion._sin_acentos(t) for t in titulares]
        if titulares and not any(p.search(t) for p in patron for t in planos):
            out.append(f"{e.get('id')}: el titular (\"{titulares[0][:90]}\") no nombra nada del guion "
                       f"(claves: {', '.join(claves[:8])}); la captura va a fallar. Agrega en \"claves\" "
                       "una palabra que sí esté en el titular, o usa otra nota")
    return out


def problemas_de_plus(guion: dict) -> list[str]:
    """El bloque "plus" (animaciones de CapituloPlus, 13/10/2026): que cuadre con
    el guion. Si algo falla igual, el render se salta esa animación; esto es
    para que Claude lo arregle en el mismo paso."""
    plus = guion.get("plus")
    if not isinstance(plus, dict) or not plus:
        return ['falta "plus" en la raíz (al menos "mapa" con el lugar exacto)']
    out = []
    planos = {p.get("id"): p for p in guion.get("planos", [])}
    c = plus.get("contador")
    if c is not None:
        if not isinstance(c.get("numero"), int) or c["numero"] <= 0:
            out.append('plus.contador.numero tiene que ser un número entero (sin comillas)')
        if not str(c.get("despues", "")).strip() or _palabras(c.get("despues", "")) > 4:
            out.append('plus.contador.despues: de 1 a 4 palabras')
    m = plus.get("mapa")
    if m is None:
        out.append('plus.mapa falta: el lugar exacto del guion')
    else:
        if m.get("plano") not in planos:
            out.append(f'plus.mapa.plano "{m.get("plano")}" no es un plano del guion')
        if not str(m.get("consulta", "")).strip():
            out.append("plus.mapa.consulta está vacía")
        if len(str(m.get("etiqueta", ""))) > 32:
            out.append("plus.mapa.etiqueta: máximo 32 letras")
    k = plus.get("contradiccion")
    if k is not None:
        plano = planos.get(k.get("plano"))
        if plano is None or k.get("plano") in ("p00", "p08"):
            out.append(f'plus.contradiccion.plano "{k.get("plano")}": tiene que ser uno de p01 a p07')
        for lado in ("arriba", "abajo"):
            renglones = (k.get(lado) or {}).get("renglones") or []
            if not 1 <= len(renglones) <= 3:
                out.append(f"plus.contradiccion.{lado}: de 1 a 3 renglones")
            out += [f'plus.contradiccion.{lado}: "{r}" pasa de 36 letras' for r in renglones if len(r) > 36]
        if k.get("resaltar") not in ((k.get("abajo") or {}).get("renglones") or []):
            out.append("plus.contradiccion.resaltar tiene que ser un renglón de \"abajo\", copiado igual")
        if plano is not None:
            dichas = revision_guion._sin_acentos(plano.get("narracion", "")).lower().split()
            dichas = [re.sub(r"[^\w]", "", w) for w in dichas]
            if revision_guion._sin_acentos(str(k.get("abajo_en", ""))).lower() not in dichas:
                out.append(f'plus.contradiccion.abajo_en "{k.get("abajo_en")}" no es una palabra de la '
                           f'narración de {k.get("plano")}')
    # La portada "gancho" (29/10/2026): 3 a 5 palabras gigantes en el perfil.
    po = plus.get("portada")
    if not isinstance(po, dict) or not str(po.get("texto", "")).strip():
        out.append('plus.portada falta: {"texto": "3 a 5 PALABRAS", "resalta": "1 o 2 de ellas"}')
    else:
        texto = revision_guion._sin_acentos(po["texto"]).upper().split()
        if not 3 <= len(texto) <= 5:
            out.append(f'plus.portada.texto: de 3 a 5 palabras (trae {len(texto)})')
        resalta = revision_guion._sin_acentos(str(po.get("resalta", ""))).upper().split()
        if not 1 <= len(resalta) <= 2 or any(w not in texto for w in resalta):
            out.append('plus.portada.resalta: 1 o 2 palabras de "texto", copiadas igual')
    return out


def _ruta(slug: str):
    from dato_mata_gato_bot import pipeline

    return pipeline.ANDROID_IN / slug / "guion.json"


def problemas(slug: str) -> list[str]:
    from dato_mata_gato_bot import fabrica, instruccion_comparativa, instruccion_polemica, instruccion_viral

    out = fabrica.problemas_cercania(slug)
    if out == ["no se pudo leer el guion.json"]:
        return out
    guion = json.loads(_ruta(slug).read_text(encoding="utf-8"))
    # Un guion de tema viral se reconoce por los tres niveles, y uno de polémica
    # por la frase que la detonó. Sus reglas (el candado, la pieza 8, los nombres
    # dichos, el check final) solo se revisaban DESPUÉS de entregar el lote, así
    # que Claude las descubría en la ronda de corrección, con el guion ya
    # escrito (16/10/2026).
    schema = guion.get("_schema") or {}
    if slug.startswith("guion-comparativa-") or schema.get("comparacion"):
        # Antes de la polémica: las dos llevan "veredicto", y el 29/10/2026 a una
        # comparativa le pidió estigma y prueba del ofensor; Claude gastó 8 pasos
        # leyendo este código para entenderlo.
        out += instruccion_comparativa.problemas(guion)
    elif schema.get("tres_niveles"):
        out += instruccion_viral.problemas(guion)
    elif schema.get("frase") or schema.get("premisas") or schema.get("veredicto"):
        out += instruccion_polemica.problemas(guion)
    return out + problemas_de_forma(guion) + problemas_de_evidencia(guion) + problemas_de_plus(guion)


# --- lo mecánico, con IA gratis (auditoría del 29/10/2026) --------------------
# En 33 corridas de revisar, lo que más se repitió fue el largo (12; siempre de
# más: 191 a 323 palabras), las frases de más de 20 palabras (6) y plus.mapa (9).
# Varias rondas de Claude fueron solo por 1 o 2 palabras de más. Cuando TODO lo
# que falla es de esto, lo arregla una IA gratis; si con eso el guion pasa,
# Claude recibe OK. Si no, el archivo vuelve como estaba (Claude lo tiene en su
# contexto y un archivo cambiado le obliga a releerlo).
MECANICOS = (re.compile(r"^la narración tiene \d+ palabras"), re.compile(r"^p\d\d: frase de \d+ palabras"),
             re.compile(r"^plus\.mapa"))
TOPE_PALABRAS = 185  # abajo de 190 para no rebotar
# Solo sobrepasos chicos. Probado el 29/10/2026 con 220 palabras: la IA dejó el
# guion "pasando" pero quitó el contraste (el promedio de seiscientos setenta y un
# pesos) y el "nadie lo prueba" del nivel 3. Recortar más es editar: va a Claude.
MAX_SOBRA = 205
RECORTE_MAX = 0.15
_NUMERO = re.compile(r"^(cero|uno?|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|trece|"
                     r"catorce|quince|dieci\w+|veinte|veinti\w+|treinta|cuarenta|cincuenta|sesenta|setenta|"
                     r"ochenta|noventa|cien|ciento|\w+cient[oa]s|quinient[oa]s|mil|millon|millones|"
                     r"porciento|medio|media)$")
# Lo único que la IA puede agregar al partir o recortar frases.
CONECTORES = {"pero", "ademas", "entonces", "tambien", "aunque", "porque", "pues", "asi", "esto", "esta",
              "este", "eso", "esos", "esas", "ella", "ellos", "ellas", "luego", "despues", "ahora"}


def _vocablos(texto: str) -> set[str]:
    return {w for w in re.findall(r"[a-zñ]+", revision_guion._sin_acentos(texto or "").lower()) if len(w) >= 4}


# Probado el 29/10/2026: "Él dijo que entró antes" quedó "Él entró antes". Lo
# atribuido sigue atribuido: estos verbos no se quitan.
_ATRIBUCION = re.compile(r"^(dijo|dice|dicen|dijeron|segun|aseguro|asegura|afirmo|afirma|declaro|acuso|acusa|"
                         r"reporto|reporta|informo|publico|publica|senalo|denuncio|explico|admitio|nego|niega|"
                         r"respondio|contesto|sostiene|presume|presumio)$")


_ARTICULOS = re.compile(r"\b(el|la|los|las|un|una|unos|unas)\b", re.IGNORECASE)


def _intocables(texto: str) -> set[str]:
    """Las cifras dichas en palabras, los nombres propios (con mayúscula a mitad
    de frase) y los verbos de atribución."""
    palabras = re.findall(r"[\wáéíóúñü]+", texto)
    out = {w.lower() for w in palabras if _NUMERO.match(revision_guion._sin_acentos(w).lower())
           or _ATRIBUCION.match(revision_guion._sin_acentos(w).lower())}
    for frase in re.split(r"(?<=[.!?¿¡:;])\s+", texto):
        out |= {w.lower() for w in re.findall(r"[\wáéíóúñü]+", frase)[1:] if w[:1].isupper()}
    return out


def _plano_nuevo(texto: str, meta: int, cita: str) -> str | None:
    """La narración de un plano más corta y sin frases de más de 20 palabras, o
    None si la IA agregó algo (palabras, cifras), quitó una pregunta, la cita,
    una cifra o un nombre, o recortó de más."""
    from dato_mata_gato_bot import ia_gratis

    try:
        r = ia_gratis.pedir(
            "Eres editor de guiones de video corto en español de México. Reescribe esta narración "
            f"para que tenga como máximo {meta} palabras y ninguna frase de más de 20 palabras (parte "
            "las largas en dos). Quita SOLO palabras de relleno: ninguna frase entera, ningún dato, "
            "ninguna cifra, ningún nombre, ningún artículo (el, la, los, un…); tiene que sonar natural "
            "dicho en voz alta. Usa SOLO las palabras que ya están: no agregues cifras, "
            "nombres, lugares ni ideas, y no cambies el sentido. Conserva cada pregunta (¿…?)"
            + (f" y esta cita completa, igual: «{cita}»" if cita else "") + ". Las cifras siguen en palabras.\n\n"
            f"Narración:\n{texto}\n\n" + 'Responde JSON: {"narracion": "<la narración nueva>"}',
            local=False, reintentos=1)
    except ia_gratis.SinIA:
        return None
    nuevo = re.sub(r"\s+", " ", str(r.get("narracion", "") if isinstance(r, dict) else "")).strip()
    if not nuevo or re.search(r"\d", nuevo) or nuevo.count("¿") != texto.count("¿"):
        return None
    if _vocablos(nuevo) - _vocablos(texto) - CONECTORES:
        return None
    if not (1 - RECORTE_MAX) * _palabras(texto) - 1 <= _palabras(nuevo) <= _palabras(texto):
        return None
    if _intocables(texto) - {w.lower() for w in re.findall(r"[\wáéíóúñü]+", nuevo)}:
        return None
    # "Periodista José Díaz publicó lista de…": sin artículos la voz suena telegráfica (29/10/2026).
    if len(_ARTICULOS.findall(nuevo)) < len(_ARTICULOS.findall(texto)):
        return None
    if cita and revision_guion._sin_acentos(cita).lower() in revision_guion._sin_acentos(texto).lower() \
            and revision_guion._sin_acentos(cita).lower() not in revision_guion._sin_acentos(nuevo).lower():
        return None
    return nuevo


def _mapa_nuevo(guion: dict) -> dict | None:
    from dato_mata_gato_bot import ia_gratis

    planos = [p for p in guion.get("planos", []) if p.get("id") in ("p00", "p01", "p02", "p03")]
    try:
        r = ia_gratis.pedir(
            "De esta narración saca el lugar exacto del hecho para buscarlo en un mapa.\n"
            + "\n".join(f"{p['id']}: {p.get('narracion', '')}" for p in planos)
            + '\n\nResponde JSON: {"plano": "<id del plano donde la voz nombra el lugar>", "consulta": '
            '"<edificio, calle o colonia, y la ciudad y el estado>", "etiqueta": "<máximo 32 letras, '
            'MAYÚSCULAS, como SAN LÁZARO · CDMX>"}', local=False, reintentos=1)
    except ia_gratis.SinIA:
        return None
    if not isinstance(r, dict) or r.get("plano") not in {p["id"] for p in planos} or not str(r.get("consulta", "")).strip():
        return None
    return {"plano": r["plano"], "consulta": str(r["consulta"]).strip(), "etiqueta": str(r.get("etiqueta", ""))[:32]}


def arreglar_mecanico(guion: dict, fallas: list[str]) -> list[str]:
    """Arregla en `guion` (en memoria) lo mecánico de `fallas`. Devuelve qué hizo."""
    hecho = []
    planos = [p for p in guion.get("planos", []) if isinstance(p, dict)]
    schema = guion.get("_schema") or {}
    cita = str((schema.get("frase") or {}).get("texto", "") if isinstance(schema.get("frase"), dict) else "")
    total = sum(_palabras(p.get("narracion", "")) for p in planos)
    if any(f.startswith("la narración tiene") for f in fallas) and not TOPE_PALABRAS < total <= MAX_SOBRA:
        return []  # corta, o larga de más: eso es editar y va a Claude
    metas: dict[str, int] = {}
    obligados = set()  # los de frase larga se aplican siempre
    for f in fallas:
        if m := re.match(r"^(p\d\d): frase de", f):
            obligados.add(m.group(1))
            metas[m.group(1)] = _palabras(next((p.get("narracion", "") for p in planos if p.get("id") == m.group(1)), ""))
    largo = TOPE_PALABRAS < total <= MAX_SOBRA and any(f.startswith("la narración tiene") for f in fallas)
    if largo:
        # Se le pide recorte a todos (nunca a p00, el gancho, ni a p08, el cierre con la
        # pregunta y la frase del canal), hasta RECORTE_MAX cada uno: la IA a veces quita
        # un nombre y ese plano se tira, así que hacen falta de dónde escoger.
        for p in planos:
            if p.get("id") not in ("p00", "p08") and (n := _palabras(p.get("narracion", ""))) >= 8:
                metas[p["id"]] = min(metas.get(p["id"], n), n - max(1, int(n * RECORTE_MAX)))
    por_id = {p.get("id"): p for p in planos}
    with ThreadPoolExecutor(8) as pool:
        nuevos = dict(zip(metas, pool.map(lambda i: _plano_nuevo(por_id[i].get("narracion", ""), metas[i], cita), metas)))
    # Primero los obligados; luego los que más recortan, solo hasta bajar de 190.
    ahorro = {i: _palabras(por_id[i].get("narracion", "")) - _palabras(x) for i, x in nuevos.items() if x}
    usar = [i for i in nuevos if nuevos[i] and i in obligados]
    total -= sum(ahorro[i] for i in usar)
    for i in sorted((i for i in ahorro if i not in obligados), key=lambda i: -ahorro[i]):
        if not largo or total <= 190:
            break
        usar.append(i)
        total -= ahorro[i]
    for i, nuevo in ((i, nuevos[i]) for i in usar):
        if nuevo and nuevo != por_id[i].get("narracion", "").strip():
            antes = _palabras(por_id[i].get("narracion", ""))
            por_id[i]["narracion"] = nuevo
            hecho.append(f"{i}: de {antes} a {_palabras(nuevo)} palabras, frases partidas")
    if any(f.startswith("plus.mapa") for f in fallas) and (mapa := _mapa_nuevo(guion)):
        guion.setdefault("plus", {})["mapa"] = mapa
        hecho.append(f"plus.mapa: {mapa['consulta']} ({mapa['plano']})")
    return hecho


def revisar(slug: str) -> str:
    out = problemas(slug)
    if out == ["no se pudo leer el guion.json"]:
        return "\n".join(out)
    if out and all(any(m.match(f) for m in MECANICOS) for f in out):
        original = _ruta(slug).read_text(encoding="utf-8")
        guion = json.loads(original)
        hecho = arreglar_mecanico(guion, out)
        if hecho:
            _ruta(slug).write_text(json.dumps(guion, ensure_ascii=False, indent=2), encoding="utf-8")
            if not problemas(slug):
                return ("OK: el guion pasa todas las revisiones automáticas. Lo mecánico lo arreglé yo "
                        "con IA gratis, sin cambiar datos (el guion.json cambió: si lo vas a tocar, léelo "
                        "antes):\n" + "\n".join(f"- {h}" for h in hecho))
            _ruta(slug).write_text(original, encoding="utf-8")
    if not out:
        return "OK: el guion pasa todas las revisiones automáticas."
    # Con Edit, todos en la MISMA respuesta (29/10/2026): reescribir el guion
    # completo costaba 7-15k de salida por ronda; un Edit, unos cientos. La
    # corrección era el 36 % del gasto de la fábrica.
    return ("Corrige TODO esto de una vez: con Edit, todos los Edit en la MISMA respuesta (solo "
            "reescribe el guion.json completo con Write si cambias más de la mitad), y vuelve a "
            "correr revisar:\n" + "\n".join(f"- {p}" for p in out))


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(argv) >= 2 and argv[0] == "fotos":
        print(fotos(argv[1:]))
        return 0
    if len(argv) == 2 and argv[0] == "revisar":
        print(revisar(argv[1]))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
