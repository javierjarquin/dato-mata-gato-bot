"""Expediente: la investigación del lote, hecha antes y sin Claude (27/10/2026).

Medido el 22/10: cada guion gastaba de 0.7 a 5.3 M tokens; lo que escribe
Claude son 40-70k, el resto es releer 30 a 60 búsquedas. Aquí se hace eso
fuera de su cuota:

1. Candidatos: RSS de Google News (gratis, sin llave; 100 notas por consulta,
   con medio y fecha, pero la liga viene codificada).
2. Gemini escoge los que cumplen la fórmula (ia_gratis).
3. Para cada uno, Bing News RSS da ligas directas de varios medios (vienen en
   el parámetro url=) y trafilatura baja el texto limpio.
4. Gemini saca los datos con su cita textual, y aquí se comprueba que la cita
   esté palabra por palabra en la nota: lo que no aparece se tira.

Claude recibe el bloque al final de su instrucción y parte de ahí. Si algo
falla, la instrucción va como antes: el expediente ayuda, no estorba.
"""

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, urlparse
from xml.etree import ElementTree

import httpx

from dato_mata_gato_bot import ia_gratis

logger = logging.getLogger(__name__)

CARPETA = Path(r"C:\Android_in\fabrica\_expedientes")
NAVEGADOR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"}
# Auditoría del 29/10/2026: el bloque pesaba ~7k tokens releídos en cada paso; los
# datos ✔ ya vienen aparte, el extracto solo da contexto.
TOPE_EXTRACTO = 600
TOPE_NOTA = 8000

# Fórmula -> (consultas sin tema, qué buscar). Solo las de noticia del día:
# terror, historia, marfil y comparativa investigan archivo, no titulares.
FORMULAS = {
    "cancun": (["Cancún", "Quintana Roo", "Playa del Carmen OR Tulum OR Chetumal"],
               "algo de Cancún o Quintana Roo que le afecte a casi cualquiera que vive ahí "
               "(bolsillo, servicios, entorno), con un responsable claro y algo que no cuadra"),
    "cdmx": (["CDMX", "Ciudad de México Metro OR agua OR colonia OR alcaldía"],
             "algo de la Ciudad de México que le toque a quien vive ahí, con algo que no cuadra"),
    # 27/10/2026: con "desata polémica" Gemini escogía el Show Run de Checo o la
    # muerte de un cantante, y Claude tiró el expediente y buscó 17 veces. Estas
    # consultas son las que a Claude sí le dieron tema ("funan a influencer
    # tras burlarse de…").
    "viral": (["se hizo viral México", "rumor redes sociales México", "es falso que circula en redes",
               "desmienten video viral", "aseguran en redes que"],
              "algo que ya se está diciendo en redes y que tiene un documento oficial debajo que "
              "lo confirmaría o lo tumbaría (lo que se dice / lo que está en papel / lo que nadie ha "
              "contestado). Una muerte SÍ sirve si circula una versión que un papel oficial cerraría ('dicen que se suicidó' contra el dictamen de la fiscalía). NO sirven: deportes, espectáculos sin rumor, nombramientos"),
    "polemica": (["funan a influencer México", "se disculpa tras comentario México", "indignación por comentario México",
                  "comentario clasista OR racista OR machista México", "madres buscadoras OR trabajadores ofende México"],
                 "una FRASE dicha por alguien con nombre (influencer, político, empresario, famoso) que "
                 "ofendió a un grupo de gente (madres buscadoras, trabajadores, una región, mujeres…), que "
                 "se pueda citar textual, con reacción medible y un dato oficial del grupo ofendido. "
                 "Una muerte o un pleito SÍ sirven si alrededor hay una frase que ofendió a un grupo (burlas a la salud mental de alguien ofenden a quienes viven con depresión). NO sirven: deportes, eventos, nombramientos, pleitos sin frase hacia un grupo"),
    # 29/10/2026: la comparativa es perenne, pero el tema sale de lo que se está
    # discutiendo (un informe, un cambio de reglas); el expediente busca 30 días.
    "comparativa": (["informe de gobierno resultados estado México", "comparado con el sexenio anterior estado",
                     "respecto a la administración anterior INEGI", "gobernador presume reducción OR aumento"],
                    "una situación concreta que le toca a la gente (agua, seguridad, transporte, salud, basura, "
                    "trámites) donde un gobierno de México, estatal sobre todo, hace algo distinto que el "
                    "anterior o que otro estado, y existe UN indicador medido igual en los dos lados (INEGI, "
                    "CONEVAL, SESNSP, IMCO, CONAGUA). NO sirven: chismes de políticos, encuestas de "
                    "popularidad, comparaciones sin dato"),
}

# El dato oficial que cada fórmula pide y Claude salía a buscar (auditoría del
# 29/10/2026): la pregunta para `datos` y lo que se agrega a la búsqueda.
OFICIAL = {
    "comparativa": ("el indicador oficial que mide esto igual en los dos lados (antes y ahora, o aquí y en "
                    "otro estado): cifra, unidad y periodo de cada lado", "INEGI CONEVAL datos oficiales"),
    "polemica": ("la cifra oficial del grupo del que se habla: cuántos son o cuántos viven esto, con año",
                 "INEGI cifra oficial"),
    "viral": ("qué dice el documento oficial (decreto, dictamen, comunicado, padrón) sobre esto",
              "documento oficial gob.mx"),
    "cancun": ("el dato oficial sobre esto: cifra, fecha y dependencia", "datos oficiales gob.mx"),
    "cdmx": ("el dato oficial sobre esto: cifra, fecha y dependencia", "datos oficiales gob.mx"),
}
OFICIALES = ("inegi.org.mx", "coneval.org.mx", "imco.org.mx", "mexicoevalua.org", "banxico.org.mx",
             "ine.mx", "cndh.org.mx", "inai.org.mx")


def es_oficial(liga: str) -> bool:
    casa = urlparse(liga).netloc.lower().removeprefix("www.")
    return casa.endswith(".gob.mx") or casa == "gob.mx" or any(casa == o or casa.endswith("." + o) for o in OFICIALES)


class SinTemasFrescos(RuntimeError):
    """Polémica o viral sin tema: el expediente no dejó ningún tema de los
    últimos DIAS_REDES días. Claude no sale a buscar uno por su cuenta (Javier,
    29/10/2026): la fábrica se salta esa fórmula en la tanda."""


class SinCuotaGratis(ia_gratis.SinIA):
    """Todas las IA gratis se quedaron sin cuota. La fábrica pregunta por
    Telegram si sigue Claude investigando (/iaclaude) o espera (/iaesperar)."""


# Qué hacer si se acaba la cuota gratis: "preguntar" (lanza SinCuotaGratis) o
# "claude" (la instrucción va sin expediente y Claude investiga, como antes).
# La fábrica lo pone por lote antes de cada tanda (estado["sin_ia_gratis"]).
SI_SE_ACABA = "preguntar"


def activo() -> bool:
    """FABRICA_EXPEDIENTE (default 1). 0 = Claude investiga solo, como antes."""
    return (os.getenv("FABRICA_EXPEDIENTE") or "1").strip() != "0"


def _limpio(texto: str) -> str:
    """Para comparar citas: sin acentos raros, comillas parejas, espacios simples."""
    texto = unicodedata.normalize("NFC", texto or "").lower()
    for a, b in (("“", '"'), ("”", '"'), ("«", '"'), ("»", '"'), ("‘", "'"), ("’", "'"), ("—", "-"), ("–", "-")):
        texto = texto.replace(a, b)
    return re.sub(r"\s+", " ", texto).strip()


def _rss(url: str) -> list[dict]:
    try:
        r = httpx.get(url, headers=NAVEGADOR, timeout=20, follow_redirects=True)
        r.raise_for_status()
        items = ElementTree.fromstring(r.content).findall(".//item")
    except (httpx.HTTPError, ElementTree.ParseError) as exc:
        logger.warning("expediente: RSS %s: %s", url[:80], exc)
        return []
    out = []
    for it in items:
        try:
            fecha = parsedate_to_datetime(it.findtext("pubDate") or "")
        except (TypeError, ValueError):
            fecha = None
        titulo = (it.findtext("title") or "").strip()
        medio = (it.findtext("source") or "").strip()
        if medio and titulo.endswith(f" - {medio}"):
            titulo = titulo[: -len(medio) - 3]
        liga = it.findtext("link") or ""
        if "bing.com" in liga:  # la liga real va en url=
            liga = parse_qs(urlparse(liga).query).get("url", [liga])[0]
            medio = medio or urlparse(liga).netloc.removeprefix("www.")
        out.append({"titulo": titulo, "medio": medio, "fecha": fecha, "liga": liga})
    return out


def google_news(consulta: str, dias: int) -> list[dict]:
    return _rss(f"https://news.google.com/rss/search?q={quote_plus(consulta)}+when:{dias}d"
                "&hl=es-419&gl=MX&ceid=MX:es-419")


def bing_news(consulta: str) -> list[dict]:
    return _rss(f"https://www.bing.com/news/search?q={quote_plus(consulta)}&format=rss&setmkt=es-MX")


def tendencias_x(tope: int = 20) -> list[str]:
    """Lo que es tendencia en X en México ahorita (trends24.in, sin llave).
    Ninguna IA gratis ve TikTok, y el WebSearch de Claude tampoco: lo que pega
    en redes se ve aquí o cuando ya lo levantaron los medios."""
    try:
        r = httpx.get("https://trends24.in/mexico/", headers=NAVEGADOR, timeout=20, follow_redirects=True)
    except httpx.HTTPError:
        return []
    vistas = []
    for t in re.findall(r"class=trend-link[^>]*>([^<]+)<", r.text):
        t = t.strip()
        if t not in vistas:
            vistas.append(t)
    return vistas[:tope]


def google_trends() -> list[dict]:
    """Búsquedas que se dispararon en México, con sus notas (ligas directas)."""
    try:
        r = httpx.get("https://trends.google.com/trending/rss?geo=MX", headers=NAVEGADOR, timeout=20,
                      follow_redirects=True)
        items = ElementTree.fromstring(r.content).findall(".//item")
    except (httpx.HTTPError, ElementTree.ParseError):
        return []
    ns = {"ht": "https://trends.google.com/trending/rss"}
    out = []
    for it in items:
        for n in it.findall("ht:news_item", ns)[:1]:
            out.append({"titulo": n.findtext("ht:news_item_title", namespaces=ns) or "",
                        "medio": n.findtext("ht:news_item_source", namespaces=ns) or "",
                        "liga": n.findtext("ht:news_item_url", namespaces=ns) or "",
                        "fecha": datetime.now(timezone.utc),
                        "tendencia": f"Google Trends: {it.findtext('title')} "
                                     f"({it.findtext('ht:approx_traffic', namespaces=ns)} búsquedas)"})
    return out


def de_redes() -> list[dict]:
    """Candidatos de lo que se habla en redes: cada tendencia de X con su nota
    más nueva del último día, más Google Trends."""
    out = google_trends()
    with ThreadPoolExecutor(8) as pool:
        for t, notas in zip(tendencias := tendencias_x(), pool.map(lambda t: google_news(t, 1)[:2], tendencias)):
            out += [{**n, "tendencia": f"tendencia en X: {t}"} for n in notas]
    return out


def candidatos(consultas: list[str], dias: int, tope: int = 80, redes: bool = False) -> list[dict]:
    """Titulares de los últimos `dias`, sin repetidos, los más nuevos primero.
    Con `redes`, primero lo que es tendencia (no se recorta por fecha)."""
    limite = datetime.now(timezone.utc) - timedelta(days=dias)
    vistos, out = set(), []
    if redes:
        for n in de_redes():
            clave = _limpio(n["titulo"])[:60]
            if n["titulo"] and clave not in vistos:
                vistos.add(clave)
                out.append(n)
    for c in consultas:
        for n in google_news(c, dias):
            clave = _limpio(n["titulo"])[:60]
            if clave in vistos or (n["fecha"] and n["fecha"] < limite):
                continue
            vistos.add(clave)
            out.append(n)
    de_tendencia = [n for n in out if n.get("tendencia")]
    resto = sorted((n for n in out if not n.get("tendencia")), key=lambda n: n["fecha"] or limite, reverse=True)
    return (de_tendencia + resto)[:tope]


def _lista(r, clave: str) -> list:
    """Gemini a veces responde la lista sola en vez de {clave: [...]}."""
    if isinstance(r, list):
        return r
    return (r.get(clave) if isinstance(r, dict) else None) or []


PDFTOTEXT = shutil.which("pdftotext") or r"C:\Program Files\Git\mingw64\bin\pdftotext.exe"


def _de_pdf(contenido: bytes) -> str | None:
    """El texto de un PDF: pdftotext (el de Git) y, si no está, pypdf."""
    with tempfile.TemporaryDirectory() as tmp:
        ruta = Path(tmp) / "doc.pdf"
        ruta.write_bytes(contenido)
        try:
            r = subprocess.run([PDFTOTEXT, "-enc", "UTF-8", str(ruta), "-"], capture_output=True, timeout=60)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.decode("utf-8", errors="replace")
        except (OSError, subprocess.TimeoutExpired):
            pass
        try:
            from pypdf import PdfReader

            return "\n".join(p.extract_text() or "" for p in PdfReader(str(ruta)).pages)
        except Exception:  # noqa: BLE001 — un PDF roto no tumba la búsqueda
            return None


def leer(liga: str, tope: int | None = TOPE_NOTA) -> str | None:
    """El texto limpio de una nota o un PDF, o None si no se deja (paywall, JS, 403)."""
    import trafilatura

    try:
        r = httpx.get(liga, headers=NAVEGADOR, timeout=20, follow_redirects=True)
        r.raise_for_status()
    except httpx.HTTPError:
        return None
    if r.content[:5] == b"%PDF-" or "pdf" in r.headers.get("content-type", ""):
        texto = _de_pdf(r.content)
    else:
        texto = trafilatura.extract(r.text, include_comments=False, include_tables=False, favor_precision=True)
    return texto[:tope] if texto and len(texto) > 400 else None


# Las dos fórmulas hermanas: un tema que no cuadra en una se prueba en la otra.
HERMANAS = {"polemica": "viral", "viral": "polemica"}


def escoger(lista: list[dict], que_buscar: str, cuantos: int, ya_hechos: str,
            formula: str | None = None, desde: datetime | None = None) -> list[dict]:
    """Los mejores `cuantos`. Con una fórmula hermana, cada elegido trae
    "formula": la suya o la otra, por la prueba del papel. Con `desde`, el
    HECHO (no la nota) tiene que ser de esa fecha o más nuevo."""
    clasificar = fresco = pide_desde = ""
    if desde:
        fresco = (f" El HECHO tiene que haber empezado el {desde:%d/%m/%Y} o después (cuándo se dijo, se "
                  "publicó o se viralizó): una nota reciente que da seguimiento a algo más viejo NO sirve.")
        pide_desde = ', "desde": "<DD/MM/AAAA: cuándo empezó el hecho, o null si no se sabe>"'
    if formula in HERMANAS:
        otra = HERMANAS[formula]
        que_buscar = (f"temas para dos fórmulas hermanas. POLÉMICA: {FORMULAS['polemica'][1]}. "
                      f"VIRAL: {FORMULAS['viral'][1]}. Prefiero de {formula}")
        clasificar = (f', "formula": "{formula}" o "{otra}" (la prueba del papel: si existe un documento '
                      'que, si apareciera, cerraría la discusión, es "viral"; si lo que detonó todo es '
                      'una opinión sin papel que la cierre, es "polemica")')
    renglones = "\n".join(f"{i}. {n['titulo']} — {n['medio']}"
                          + (f" ({n['fecha']:%d/%m})" if desde and hasattr(n.get("fecha"), "strftime") else "")
                          + (f" [{n['tendencia']}]" if n.get("tendencia") else "") for i, n in enumerate(lista))
    r = ia_gratis.pedir(
        f"Eres editor de un canal de TikTok en español de México. Hoy es {datetime.now():%d/%m/%Y}. Busco {cuantos} temas para "
        f"videos cortos para gente de México. Qué busco: {que_buscar}. Tiene que pasar en México "
        "o tocar a México directamente (nada de otro país que aquí no importe), estar pasando ahorita, hacer hablar "
        f"(que la gente quiera comentar) y poderse mostrar con notas o documentos.{fresco}\n"
        "No repitas nada de lo que ya está hecho, ni el mismo caso con otras palabras:\n"
        f"{ya_hechos[:6000]}\n\nTitulares:\n{renglones}\n\n"
        f'Responde JSON: {{"elegidos": [{{"i": <número>, "motivo": "<una línea: por qué hace '
        'hablar y qué no cuadra>", "busqueda": "<4 a 7 palabras para encontrar más notas del '
        f'mismo hecho>"{pide_desde}{clasificar}}}]}} con exactamente {cuantos} elegidos, el mejor primero. Si menos '
        "cumplen, pon menos.",
        local=False)  # escoger pide criterio: Ollama no; sin cuota gratis la fábrica pregunta
    out = []
    for e in _lista(r, "elegidos")[:cuantos]:
        if desde and isinstance(e, dict) and (cuando := _fecha(e.get("desde"))) and cuando < desde:
            continue
        if isinstance(e, dict) and isinstance(e.get("i"), int) and 0 <= e["i"] < len(lista):
            out.append({**lista[e["i"]], "motivo": e.get("motivo", ""), "busqueda": e.get("busqueda", ""),
                        **({"formula": e["formula"]} if e.get("formula") in HERMANAS else {})})
    return out


def _bolsa(formula: str) -> Path:
    return CARPETA / f"bolsa_{formula}.json"


def a_la_bolsa(formula: str, temas: list[dict]) -> None:
    """Temas que no cuadraron en la hermana: el próximo expediente de
    `formula` los prueba primero. Duran DIAS_BOLSA."""
    if not temas:
        return
    viejos = de_la_bolsa(formula, sacar=False)
    nuevos = [{k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in t.items()
               if k in ("titulo", "medio", "liga", "fecha", "motivo", "busqueda")}
              | {"guardado": datetime.now().isoformat(timespec="minutes"), "de": HERMANAS[formula]}
              for t in temas]
    try:
        CARPETA.mkdir(parents=True, exist_ok=True)
        _bolsa(formula).write_text(json.dumps((nuevos + viejos)[:20], ensure_ascii=False, indent=1, default=str),
                                   encoding="utf-8")
    except OSError:
        pass


DIAS_BOLSA = 3
# Polémica y viral (Javier, 29/10/2026): solo hechos de los últimos 3 días; más
# viejos repetían videos (un podcast del 05/10 se escribió el 29/10). El filtro
# es aquí, con las IA gratis: Claude recibe los temas ya filtrados y no revisa fechas.
DIAS_REDES = 3


def de_la_bolsa(formula: str, sacar: bool = True) -> list[dict]:
    """Lo que la hermana le pasó a `formula` en los últimos DIAS_BOLSA. Con
    `sacar`, la bolsa queda vacía: lo que no se escoja ahora ya tuvo su vuelta."""
    try:
        temas = json.loads(_bolsa(formula).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    limite = datetime.now() - timedelta(days=DIAS_BOLSA)
    temas = [t for t in temas if datetime.fromisoformat(t.get("guardado", "2000-01-01")) >= limite]
    if sacar:
        try:
            _bolsa(formula).unlink()
        except OSError:
            pass
    for t in temas:
        t["tendencia"] = f"no cuadró en {t.get('de')}: {t.get('motivo', '')}"[:160]
        try:
            t["fecha"] = datetime.fromisoformat(t["fecha"]) if t.get("fecha") else None
        except (TypeError, ValueError):
            t["fecha"] = None
    # Guardado hace 3 días con una nota de hace 3 = tema de 6 días (29/10/2026).
    viejo = (datetime.now(timezone.utc) - timedelta(days=DIAS_REDES)).timestamp()
    return [t for t in temas if not t["fecha"] or t["fecha"].timestamp() >= viejo]


TIPOS_DE_DATO = ("hecho", "saber_popular", "falso")


def datos(titulo: str, notas: list[dict], pregunta: str | None = None, reintentos: int | None = None,
          que: str | None = None, tipos: bool = False) -> list[dict]:
    """Datos con cita textual; solo quedan los que la cita está literal en su nota.
    Con `pregunta`, solo los que la contestan (el comando buscar). Con `tipos`
    (tradiciones, 30/10/2026), cada uno dice si es hecho, saber popular o falso."""
    cuerpo = "\n\n".join(f"[{i}] {n['medio']}\n{n['texto']}" for i, n in enumerate(notas))
    que = que or (f"Saca de 3 a 5 datos que contesten esta pregunta: {pregunta}. Si ninguna nota la "
                  "contesta, responde la lista vacía." if pregunta else
                  "Saca los datos que sirven para contar este hecho en un video: cifras, fechas, nombres "
                  "con cargo, lugares exactos y frases dichas por alguien.")
    tipo = ""
    if tipos:
        que += (' Marca cada dato con "tipo": "hecho" (la fuente lo da como documentado), "saber_popular" '
                '(la fuente dice que es creencia, tradición o algo que "se dice") o "falso" (la fuente dice '
                "que es un mito falso o un error común).")
        tipo = ', "tipo": "hecho|saber_popular|falso"'
    r = ia_gratis.pedir(
        f"Tema: {titulo}\n\nNotas:\n{cuerpo}\n\n{que} Para cada uno copia la CITA "
        "tal cual viene en la nota (de 6 a 30 palabras, sin cambiar ni una letra). No inventes: "
        "si no está escrito en la nota, no va.\n"
        f'Responde JSON: {{"datos": [{{"dato": "<en tus palabras>", "cita": "<copia literal>", "nota": <número>{tipo}}}]}}',
        rapido=True,  # una llamada por tema: la cuota gratis de 3.8 se acabó a la mitad (27/10)
        local=False,  # Ollama inventa citas; mejor sin datos que con datos falsos
        reintentos=reintentos)
    out, vistas = [], set()
    for d in _lista(r, "datos"):
        if not isinstance(d, dict):
            continue
        n = d.get("nota")
        if not isinstance(n, int) or not 0 <= n < len(notas) or not d.get("cita"):
            continue
        if (n, _limpio(d["cita"])) in vistas:  # la misma cita dos veces con otra paráfrasis
            continue
        vistas.add((n, _limpio(d["cita"])))
        d["comprobada"] = _limpio(d["cita"]).strip('"') in _limpio(notas[n]["texto"])
        # La cita se comprueba, la paráfrasis no: el 29/10/2026 Gemini puso "21.8
        # millones" en un dato cuya cita solo decía "23,7 por ciento".
        d["cifras_fuera"] = sorted(_cifras(str(d.get("dato", ""))) - _cifras(d["cita"]))
        if tipos and d.get("tipo") not in TIPOS_DE_DATO:
            d["tipo"] = "saber_popular"  # sin marca clara, se dice atribuido: es lo seguro
        out.append(d)
    return out


def _cifras(texto: str) -> set[str]:
    return {c.replace(",", ".") for c in re.findall(r"\d+(?:[.,]\d+)?", texto)}


def renglon(d: dict) -> str:
    """Un dato para Claude. Si la paráfrasis trae cifras que la cita no tiene,
    solo va la cita."""
    if d.get("cifras_fuera"):
        return f"«{d['cita']}»"
    return f"{d['dato']} — «{d['cita']}»"


def _palabras(texto: str) -> set[str]:
    return {w for w in re.findall(r"\w+", _limpio(texto)) if len(w) >= 4}


ANDROID_IN = Path(r"C:\Android_in")


def _hechos() -> list[set[str]]:
    """Las palabras de cada guion ya escrito: slug, título, gancho y la frase."""
    out = []
    for ruta in ANDROID_IN.glob("guion-*/guion.json"):
        try:
            g = json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(g, dict):
            continue
        schema = g.get("_schema") if isinstance(g.get("_schema"), dict) else {}
        frase = schema.get("frase") if isinstance(schema.get("frase"), dict) else {}
        inicio = " ".join(str(p.get("narracion", "")) for p in (g.get("planos") or [])[:3] if isinstance(p, dict))
        texto = " ".join([ruta.parent.name.replace("-", " "), str(g.get("titulo", "")), str(g.get("gancho", "")),
                          str(frase.get("texto", "")), str(schema.get("que_paso", "")), inicio])
        out.append(_palabras(texto))
    return out


def ya_hecho(titulo: str, hechos: list[set[str]] | None = None) -> bool:
    """El titular cuenta un caso que ya tiene guion. Sin IA: el 27/10/2026 Gemini
    volvió a escoger "Funan a influencer… madres buscadoras" con el video de "su
    gato vale más que sus desaparecidos" ya hecho. 3+ palabras en común = el mismo,
    sin contar las que salen en muchos guiones ("cancún", "agua", "méxico")."""
    hechos = _hechos() if hechos is None else hechos
    tope = max(5, len(hechos) // 30)
    cuenta: dict[str, int] = {}
    palabras = _palabras(titulo)
    for h in hechos:
        for w in palabras & h:
            cuenta[w] = cuenta.get(w, 0) + 1
    raras = {w for w in palabras if cuenta.get(w, 0) <= tope}
    return any(len(raras & h) >= 3 for h in hechos)


def sin_repetir(temas: list[dict]) -> list[dict]:
    """Un caso, un tema: el 27/10/2026 Groq escogió a Mbappé tres veces con
    titulares de tres medios. Dos titulares con 3+ palabras en común son el mismo."""
    out: list[dict] = []
    for t in temas:
        if all(len(_palabras(t["titulo"]) & _palabras(o["titulo"])) < 3 for o in out):
            out.append(t)
    return out


def consulta_de(t: dict) -> str:
    """Con qué se buscan más notas del tema. La búsqueda que propone la IA solo
    si comparte palabras con el titular: el 27/10/2026 Groq propuso "Moreno
    Cárdenas maestros SNTE" para el titular de Mbappé y no salió ni una nota."""
    busqueda, titulo = t.get("busqueda") or "", t["titulo"]
    if len(_palabras(busqueda) & _palabras(titulo)) >= 2:
        return busqueda
    return " ".join(re.findall(r"\w+", titulo)[:10])


def impacto(t: dict, cobertura: list[dict]) -> str:
    """Las señales del umbral que se pueden medir sin Claude: cuántos medios lo
    cubrieron, en cuántos días y si es tendencia. En la viral del 29/10/2026
    Claude hizo 6 WebSearch para juntar justo esto."""
    hoy = datetime.now(timezone.utc)
    recientes = [n for n in cobertura if n.get("fecha") and (hoy - n["fecha"]).days <= 7]
    medios = sorted({n["medio"] for n in recientes if n.get("medio")})
    dias = sorted({n["fecha"].astimezone().date() for n in recientes})
    partes = []
    if medios:
        partes.append(f"{len(medios)} medios distintos en Bing Noticias ({', '.join(medios[:10])})"
                      + (f", con notas en {len(dias)} días distintos (del {dias[0]:%d/%m} al {dias[-1]:%d/%m})"
                         if len(dias) > 1 else f", todas del {dias[0]:%d/%m}"))
    if t.get("tendencia"):
        partes.append(t["tendencia"])
    return "; ".join(partes)


def _investigar(t: dict) -> None:
    """Hasta 3 notas de medios distintos (la liga directa de Google Trends, si
    la hay, y luego Bing), leídas en paralelo, y sus datos con cita."""
    ligas, medios = [], set()
    propias = [t] if t["liga"] and "news.google.com" not in t["liga"] else []
    cobertura = bing_news(consulta_de(t))
    for n in propias + cobertura:
        if n["medio"] not in medios and "bing.com" not in n["liga"] and len(ligas) < 6:
            ligas.append(n)
            medios.add(n["medio"])
    t["impacto"] = impacto(t, cobertura)
    with ThreadPoolExecutor(6) as pool:
        textos = list(pool.map(lambda n: leer(n["liga"]), ligas))
    t["notas"] = [{**n, "texto": x} for n, x in zip(ligas, textos) if x][:3]
    try:
        t["datos"] = datos(t["titulo"], t["notas"]) if t["notas"] else []
    except ia_gratis.SinIA as exc:
        logger.warning("expediente: sin datos de %s: %s", t["titulo"][:60], exc)
        t["datos"] = []


def _fecha(texto) -> datetime | None:
    """"05/10/2026" -> datetime, o None."""
    m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", str(texto or ""))
    try:
        return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None
    except ValueError:
        return None


def desde_cuando(t: dict) -> datetime | None:
    """Cuándo empezó el hecho, según las notas ya leídas: el titular puede ser
    de hoy y el hecho de hace semanas ("sigue la polémica por…"). None si la IA
    no lo sabe."""
    if not t.get("notas"):
        return None
    cuerpo = "\n\n".join(f"[{n['medio']}" + (f", {n['fecha']:%d/%m/%Y}" if hasattr(n.get("fecha"), "strftime") else "")
                         + f"]\n{n['texto'][:2000]}" for n in t["notas"])
    try:
        r = ia_gratis.pedir(
            f"Hoy es {datetime.now():%d/%m/%Y}. Tema: {t['titulo']}\n\nNotas:\n{cuerpo}\n\n"
            "¿Qué día empezó este hecho (cuándo se dijo, se publicó o se viralizó lo que lo detonó)? "
            'Si una nota dice "el pasado 5 de octubre" o "hace dos semanas", calcula la fecha. '
            'Responde JSON: {"desde": "DD/MM/AAAA"}, o {"desde": null} si las notas no lo dicen.',
            rapido=True, local=False)
    except ia_gratis.SinIA as exc:
        logger.warning("expediente: sin fecha de %s: %s", t["titulo"][:60], exc)
        return None
    return _fecha(r.get("desde") if isinstance(r, dict) else None)


def _oficial(t: dict, formula: str) -> None:
    """Hasta 2 páginas oficiales (INEGI, CONEVAL, gob.mx…) con el dato que pide
    la fórmula, y sus datos con cita. Sin página oficial, no agrega nada."""
    pregunta, extra = OFICIAL[formula]
    ligas = [r for r in web(f"{consulta_de(t)} {extra}") if es_oficial(r["liga"])][:2]
    textos = [leer(r["liga"], tope=None) for r in ligas]
    notas = [{**r, "texto": lo_que_toca(x, f"{t['titulo']} {pregunta}")} for r, x in zip(ligas, textos) if x]
    if not notas:
        return
    try:
        encontrados = datos(t["titulo"], notas, pregunta=f"{pregunta} (tema: {t['titulo']})")
    except ia_gratis.SinIA as exc:
        logger.warning("expediente: sin dato oficial de %s: %s", t["titulo"][:60], exc)
        return
    t["oficial"] = [{"medio": n["medio"], "liga": n["liga"],
                     "datos": [d for d in encontrados if d["nota"] == i and d["comprobada"]]}
                    for i, n in enumerate(notas)]


def armar(formula: str, tema: str | None, cuantos: int, ya_hechos: str, dias: int = 2) -> dict:
    """Busca, escoge, lee y saca datos. Guarda el expediente en CARPETA."""
    consultas, que_buscar = FORMULAS[formula]
    if tema:
        consultas, que_buscar = [tema], f"{tema}. {que_buscar}"
    ia_gratis.reiniciar_usados()
    frescos = formula in HERMANAS and not tema  # con tema, lo escogió Javier
    if frescos:
        dias = DIAS_REDES if formula == "polemica" else min(dias, DIAS_REDES)
    desde = (datetime.now() - timedelta(days=DIAS_REDES)).replace(hour=0, minute=0, second=0, microsecond=0) \
        if frescos else None
    # Polémica sin tendencias de X: llenaban la lista de nombres sin frase (27/10).
    lista = candidatos(consultas, dias, redes=formula == "viral")
    if formula in HERMANAS and not tema:
        lista = de_la_bolsa(formula) + lista
    hechos = _hechos()
    lista = [n for n in lista if not ya_hecho(n["titulo"], hechos)]
    if not lista:
        raise ia_gratis.SinIA("ningún titular en el RSS")
    try:
        temas = escoger(lista, que_buscar, cuantos * 3, ya_hechos, None if tema else formula, desde)
    except ia_gratis.SinIA as exc:
        if ia_gratis.es_cuota(str(exc)):
            raise SinCuotaGratis(str(exc)) from exc
        raise
    if formula in HERMANAS:
        a_la_bolsa(HERMANAS[formula], [t for t in temas if t.get("formula") == HERMANAS[formula]])
        temas = [t for t in temas if t.get("formula", formula) == formula]
    temas = sin_repetir(temas)
    with ThreadPoolExecutor(6) as pool:
        list(pool.map(_investigar, temas))
    viejos = []
    if desde:
        with ThreadPoolExecutor(6) as pool:
            for t, cuando in zip(temas, list(pool.map(desde_cuando, temas))):
                t["desde"] = f"{cuando:%d/%m/%Y}" if cuando else None
        viejos = [t for t in temas if (c := _fecha(t["desde"])) and c < desde]
        temas = [t for t in temas if t not in viejos]
    # Uno por uno y solo los primeros: el buscador de Groq da ~3 búsquedas por minuto.
    for t in temas[:cuantos + 1]:
        _oficial(t, formula)
    exp = {"formula": formula, "tema": tema, "modelos": sorted(ia_gratis.usados()), "armado": datetime.now().isoformat(timespec="seconds"),
           "titulares_vistos": len(lista), "temas": temas,
           "viejos": [f"{t['titulo']} (desde {t['desde']})" for t in viejos]}
    try:
        CARPETA.mkdir(parents=True, exist_ok=True)
        ruta = CARPETA / f"{datetime.now():%Y%m%d-%H%M%S}-{formula}.json"
        ruta.write_text(json.dumps(exp, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        exp["ruta"] = str(ruta)
    except OSError:
        pass
    return exp


def bloque(exp: dict) -> str:
    """El expediente como texto para la instrucción de Claude."""
    if exp.get("formula") in HERMANAS and not exp.get("tema"):
        escoge = ("- ESCOGE TU TEMA SOLO DE ESTA LISTA. Ya están filtrados: son de los últimos "
                  f"{DIAS_REDES} días y no repiten ningún video hecho; no revises fechas ni busques "
                  "temas por tu cuenta. Si ninguno cumple la fórmula, entrega menos guiones y di en "
                  "una línea por qué.")
    else:
        escoge = ("- ESCOGE TU TEMA DE ESTA LISTA. No busques temas por tu cuenta. Solo si NINGUNO cumple la "
                  "fórmula, busca otro, y di en tu respuesta en una línea por qué ninguno servía.")
    partes = [
        "EXPEDIENTE YA INVESTIGADO (lo armé antes, fuera de tu cuota: cada búsqueda tuya se "
        "relee en todos los pasos que siguen y es lo que más gasta)",
        escoge,
        "- Las notas de abajo YA las bajé y leí de su liga: cuentan como notas abiertas. Los datos "
        "con ✔ tienen la cita comprobada palabra por palabra en esa nota.",
        "- Busca por tu cuenta SOLO lo que falte (el documento oficial, la cifra del grupo, la foto, "
        "una segunda fuente), con el comando buscar: en todo el lote, máximo 4 búsquedas "
        "y 3 notas abiertas más.",
        "- El IMPACTO de cada tema (medios, días, tendencia) ya está medido abajo. En polémica y "
        "viral solo falta la publicación de redes para _schema.hallado_en (plataforma, cuenta y "
        "números): para eso, máximo 2 búsquedas.",
        "- La evidencia, las fotos y la revisión automática van igual que siempre.",
    ]
    for k, t in enumerate(exp["temas"], 1):
        fecha = t["fecha"].strftime("%d/%m/%Y") if hasattr(t.get("fecha"), "strftime") else ""
        partes.append(f"\nTEMA {k}: {t['titulo']} — {t['medio']} {fecha}\nPor qué: {t.get('motivo', '')}")
        if t.get("impacto"):
            partes.append(f"IMPACTO ya medido (va a _schema.impacto; no lo busques): {t['impacto']}")
        if not t.get("notas"):
            partes.append("  (no pude bajar ninguna nota: si lo usas, búscalo tú)")
        for i, n in enumerate(t.get("notas", [])):
            partes.append(f"  [{i}] {n['medio']} — {n['liga']}")
            for d in t.get("datos", []):
                if d.get("nota") == i:
                    marca = "✔" if d["comprobada"] else "✘ NO está literal: no lo uses sin verificar"
                    partes.append(f"      {marca} {renglon(d)}")
            partes.append("      Extracto: " + re.sub(r"\s+", " ", n["texto"][:TOPE_EXTRACTO]))
        for o in t.get("oficial", []):
            partes.append(f"  DATO OFICIAL — {o['medio']} — {o['liga']}")
            partes += [f"      ✔ {renglon(d)}" for d in o["datos"]] or ["      (la abrí y no trae la cifra: búscala con buscar)"]
    return "\n".join(partes)


def agregar(texto: str, formula: str, tema: str | None, cuantos: int, ya_hechos: str,
            dias: int = 2, avisar=None) -> str:
    """La instrucción con el expediente (aviso arriba, bloque al final), o tal
    cual si no se pudo. Sin cuota gratis y SI_SE_ACABA == "preguntar", lanza
    SinCuotaGratis. `avisar(texto)` dice por Telegram qué se usó."""
    if not activo() or formula not in FORMULAS:
        return texto
    frescos = formula in HERMANAS and not tema
    try:
        exp = armar(formula, tema, cuantos, ya_hechos, dias)
    except SinCuotaGratis as exc:
        if SI_SE_ACABA == "preguntar":
            raise
        logger.warning("expediente: sin cuota gratis, Claude investiga (%s)", exc)
        if avisar:
            avisar(f"🔎 {formula}: sin cuota gratis; Claude investiga solo, como antes.")
        return texto
    except (ia_gratis.SinIA, httpx.HTTPError, ValueError, KeyError) as exc:
        logger.warning("expediente: sin expediente para %s: %s", formula, exc)
        if frescos:
            raise SinTemasFrescos(f"no se pudo armar el expediente ({str(exc)[:100]})") from exc
        return texto
    if not exp["temas"]:
        if frescos:
            raise SinTemasFrescos(f"ningún tema de los últimos {DIAS_REDES} días pasó el filtro"
                                  + (f" (fuera por viejos: {'; '.join(exp['viejos'])[:300]})" if exp["viejos"] else ""))
        return texto
    logger.info("expediente %s: %d temas, %d notas -> %s", formula, len(exp["temas"]),
                sum(len(t.get("notas", [])) for t in exp["temas"]), exp.get("ruta"))
    if avisar:
        datos = [d for t in exp["temas"] for d in t.get("datos", [])]
        avisar(f"🆓 Expediente de {formula} armado sin Claude ({', '.join(exp['modelos']) or 'IA gratis'}): "
               f"{exp['titulares_vistos']} titulares, {len(exp['temas'])} temas, "
               f"{sum(len(t.get('notas', [])) for t in exp['temas'])} notas leídas, "
               f"{sum(d['comprobada'] for d in datos)} datos con cita comprobada, "
               f"{sum(bool(o['datos']) for t in exp['temas'] for o in t.get('oficial', []))} página(s) "
               "oficial(es) con dato. Claude solo escribe."
               + (f"\n🗓️ Fuera por viejos (más de {DIAS_REDES} días): {'; '.join(exp['viejos'])[:400]}"
                  if exp.get("viejos") else ""))
    aviso = ("IMPORTANTE: al final de esta instrucción hay un EXPEDIENTE con los temas ya buscados y sus "
             "notas ya leídas. Escoge de ahí; no busques temas por tu cuenta.\n\n")
    return aviso + texto + "\n\n" + bloque(exp)


# --- buscar (29/10/2026) -------------------------------------------------------
# Auditoría del 28/10: "investigar" era el 36 % del gasto de la fábrica aun con
# expediente. Lo que faltaba (el dato oficial, la segunda fuente) Claude lo
# buscaba con WebSearch y lo leía con curl, pdftotext y sed: 5-10k letras por
# página que se releen en todos los pasos que siguen. Aquí la página se baja y
# se lee fuera de su cuota, y Claude recibe ~1k letras: el dato, su cita
# comprobada palabra por palabra y la liga.
#
#     python -m dato_mata_gato_bot.expediente buscar "<pregunta>" [liga…]

TOPE_BUSCAR = 6000  # letras de cada página que ve la IA: lo que más toca la pregunta
TOPE_LIGAS = 5


# Cada modelo tiene su propio tope diario de tokens; una búsqueda "sin abrir"
# gasta ~2k (29/10/2026). Si abre las páginas, decenas de miles: por eso el aviso.
GROQ_BUSCADORES = [m.strip() for m in (os.getenv("GROQ_BUSCADOR_MODELOS")
                                       or "openai/gpt-oss-120b,openai/gpt-oss-20b").split(",") if m.strip()]


def _resultado(liga: str, titulo: str = "") -> dict:
    return {"titulo": titulo, "liga": liga, "medio": urlparse(liga).netloc.removeprefix("www.")}


def _web_groq(consulta: str) -> list[dict]:
    """La búsqueda integrada de gpt-oss en Groq (browser_search, capa gratis).
    Probadas el 29/10/2026: DuckDuckGo bloquea (202 + captcha) a la tercera
    consulta y sigue así minutos; Bing en HTML devuelve basura a un robot
    (Reddit para una pregunta del ENADIS); el grounding de Gemini no viene en la
    capa gratis (429), y el 120b revienta el tope de tokens con las páginas."""
    llave = (os.getenv("GROQ_API_KEY") or "").strip().strip("\"'")
    if not llave:
        return []
    herramientas = []
    for modelo in GROQ_BUSCADORES:
        if herramientas := _groq_busca(llave, modelo, consulta):
            break
    out = []
    for h in herramientas:
        if h.get("type") == "browser_search":
            out += [_resultado(x["url"], x.get("title", "")) for x in (h.get("search_results") or {}).get("results") or []
                    if str(x.get("url", "")).startswith("http")]
    return out


def _groq_busca(llave: str, modelo: str, consulta: str) -> list[dict]:
    """Las herramientas que corrió `modelo`, o [] si no contestó. Espera solo un
    429 corto (por minuto); el diario pide 1-2 min y se pasa al otro modelo."""
    for intento in range(2):
        try:
            r = httpx.post("https://api.groq.com/openai/v1/chat/completions", timeout=90,
                           headers={"Authorization": f"Bearer {llave}"},
                           json={"model": modelo, "max_completion_tokens": 300,
                                 "tools": [{"type": "browser_search"}],
                                 "messages": [{"role": "user", "content": "Haz UNA sola búsqueda en la web, sin "
                                               f"abrir las páginas, y dame las ligas: {consulta}"}]})
            r.raise_for_status()
            return r.json()["choices"][0]["message"].get("executed_tools") or []
        except httpx.HTTPStatusError as exc:
            logger.warning("buscar: Groq %s: HTTP %s", modelo, exc.response.status_code)
            try:
                espera = float(exc.response.headers.get("retry-after") or 5)
            except ValueError:
                espera = 5
            if exc.response.status_code not in (429, 500, 502, 503) or espera > 30 or intento:
                return []
            time.sleep(espera + 1)
        except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
            logger.warning("buscar: Groq %s: %s", modelo, exc)
            return []
    return []


def _web_duckduckgo(consulta: str) -> list[dict]:
    try:
        r = httpx.post("https://html.duckduckgo.com/html/", data={"q": consulta, "kl": "mx-es"},
                       headers=NAVEGADOR, timeout=20, follow_redirects=True)
    except httpx.HTTPError as exc:
        logger.warning("buscar: DuckDuckGo: %s", exc)
        return []
    out = []
    for liga, titulo in re.findall(r'class="result__a" href="([^"]+)"[^>]*>(.*?)</a>', r.text):
        liga = parse_qs(urlparse(liga).query).get("uddg", [liga])[0]
        if liga.startswith("http") and "duckduckgo.com" not in liga:
            out.append(_resultado(liga, re.sub(r"<[^>]+>", "", titulo).strip()))
    return out


def web(consulta: str, tope: int = 8) -> list[dict]:
    """Resultados de la web, sin repetir: Groq y, si no da nada, DuckDuckGo.
    (Bing por RSS solo sirve para noticias: en la web devolvió el portal del
    SAT para una pregunta de la ENADIS.)"""
    vistas, out = set(), []
    for n in _web_groq(consulta) or _web_duckduckgo(consulta):
        if n["liga"] not in vistas:
            vistas.add(n["liga"])
            out.append(n)
    return out[:tope]


def _pedazos(texto: str, largo: int = 800) -> list[str]:
    """Párrafos; los gigantes (PDF sin renglones en blanco) en trozos de `largo`."""
    pedazos = [p for p in re.split(r"\n\s*\n", texto) if p.strip()]
    return [p[i:i + largo] for p in pedazos for i in range(0, len(p), largo)]


def _puntuador(pregunta: str):
    buscadas = _palabras(pregunta) | set(re.findall(r"\d{2,}", pregunta))
    return lambda p: len(_palabras(p) & buscadas) * 3 + len(re.findall(r"\d", p)) // 4


def lo_mas_cercano(texto: str, pregunta: str, tope: int = 400) -> str | None:
    """El pedazo que más palabras comparte con la pregunta, tal cual viene en la
    página (sin la IA), o None si no comparte ninguna."""
    puntos = _puntuador(pregunta)
    mejor = max(_pedazos(texto, tope), key=puntos, default="")
    return re.sub(r"\s+", " ", mejor).strip() if mejor and len(_palabras(mejor) & _palabras(pregunta)) >= 2 else None


def lo_que_toca(texto: str, pregunta: str, tope: int = TOPE_BUSCAR) -> str:
    """Los pedazos del texto con más palabras de la pregunta, en su orden, hasta
    `tope`. Un PDF del INEGI tiene 100k letras; la cifra está en un párrafo."""
    if len(texto) <= tope:
        return texto
    pedazos = _pedazos(texto)
    puntos = _puntuador(pregunta)
    elegidos, largo = set(), 0
    for i in sorted(range(len(pedazos)), key=lambda i: puntos(pedazos[i]), reverse=True):
        if largo + len(pedazos[i]) > tope:
            continue
        elegidos.add(i)
        largo += len(pedazos[i])
    return "\n…\n".join(pedazos[i] for i in sorted(elegidos))


def buscar(pregunta: str, ligas: list[str] | None = None) -> str:
    """Lee las ligas (o lo que dé la web para la pregunta) y regresa solo los
    datos que la contestan, cada uno con su cita comprobada y su liga."""
    ia_gratis.reiniciar_usados()
    dadas = [{"liga": x, "medio": urlparse(x).netloc.removeprefix("www.")} for x in (ligas or [])][:TOPE_LIGAS]
    resultados = [] if dadas else (web(pregunta) or bing_news(pregunta))
    candidatas = dadas or resultados[:6]
    with ThreadPoolExecutor(6) as pool:
        textos = list(pool.map(lambda n: leer(n["liga"], tope=None), candidatas))
    notas = [{**n, "texto": lo_que_toca(x, pregunta)} for n, x in zip(candidatas, textos) if x]
    notas = notas if dadas else notas[:3]
    cerradas = [n["liga"] for n, x in zip(candidatas, textos) if not x]
    lineas = [f'## "{pregunta}"']
    if not notas:
        lineas.append("  (no pude abrir ninguna página: " + (
            "ábrelas con WebFetch)" if dadas else "prueba otra pregunta o pásame las ligas)"))
        return "\n".join(lineas + [f"  no abrió: {x}" for x in cerradas])
    try:
        encontrados = datos(pregunta, notas, pregunta=pregunta, reintentos=1)
    except ia_gratis.SinIA as exc:
        # Sin IA gratis: lo que más toca la pregunta, recortado; sigue siendo menos que la página.
        lineas.append(f"  (sin IA gratis ahorita: {str(exc)[:80]}…; van los párrafos que más tocan la pregunta)")
        for n in notas:
            lineas += [f"[{n['medio']}] {n['liga']}", "  " + re.sub(r"\s+", " ", lo_que_toca(n["texto"], pregunta, 1200))]
        return "\n".join(lineas)
    buenos = [d for d in encontrados if d["comprobada"]]
    for i, n in enumerate(notas):
        suyos = [d for d in buenos if d["nota"] == i]
        lineas.append(f"[{n['medio']}] {n['liga']}")
        if suyos:
            lineas += [f"  ✔ {renglon(d)}" for d in suyos]
        elif cercano := lo_mas_cercano(n["texto"], pregunta):
            # 29/10/2026: 23 de 37 búsquedas salían "no trae nada" y Claude se iba a
            # WebSearch (~3.7k letras). El pedazo más cercano, literal, suele bastar.
            lineas.append(f"  (sin dato exacto; lo más cercano, literal de la página): «{cercano}»")
        else:
            lineas.append("  (no trae nada que conteste)")
    if tirados := len(encontrados) - len(buenos):
        lineas.append(f"({tirados} dato(s) tirado(s): su cita no está literal en la página)")
    lineas += [f"no abrió: {x} (si la necesitas, sólo ésa con WebFetch)" for x in cerradas if dadas]
    if not dadas and (otras := [r for r in resultados if r["liga"] not in {n["liga"] for n in notas}][:3]):
        lineas.append("Otras ligas de la búsqueda (pásalas a buscar si hace falta): "
                      + " · ".join(r["liga"] for r in otras))
    lineas.append(f"(leído sin Claude con {', '.join(sorted(ia_gratis.usados())) or 'IA gratis'})")
    return "\n".join(lineas)


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.ERROR)  # los 429 de cada proveedor no le sirven a Claude
    if len(argv) >= 2 and argv[0] == "buscar":
        print(buscar(argv[1], argv[2:]))
        return 0
    print('uso: python -m dato_mata_gato_bot.expediente buscar "<pregunta>" [liga…]')
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
