"""Expediente del nicho de tradiciones, hecho con IA gratis antes que Claude (30/10/2026).

Para tradiciones no hay noticias que leer: el tema sale de la temporada (lo que
se celebra en las próximas semanas) o de Javier, y las fuentes son Wikipedia en
español y las páginas de quienes lo estudian (INAH, UNAM, gob.mx, Cultura,
México Desconocido). Igual que en expediente.py, cada dato trae su cita
comprobada palabra por palabra en la página; aquí además viene marcado como
hecho, saber popular (se dice atribuido) o falso (no entra).
"""

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from urllib.parse import urlparse

import httpx

from dato_mata_gato_bot import expediente, ia_gratis

logger = logging.getLogger(__name__)

WIKIPEDIA = "https://es.wikipedia.org/w/api.php"
# Wikimedia pide un User-Agent con contacto (sin él responde 403). Solo ASCII: con un acento,
# httpx lanza UnicodeEncodeError (un ValueError) y Wikipedia salía vacía sin aviso.
AGENTE = {"User-Agent": "DatoMataGato/1.0 (https://www.tiktok.com/@datomatagato)"}
CONFIABLES = ("inah.gob.mx", "gob.mx", "unam.mx", "mexicodesconocido.com.mx", "arqueologiamexicana.mx",
              "colmex.mx", "inali.gob.mx", "cultura.gob.mx", "fao.org", "wikipedia.org")
TOPE_TEXTO = 6000
QUE_SACAR = ("Saca de 4 a 8 datos que sirvan para contestar la pregunta y contar su historia: de dónde "
             "viene, qué significa el nombre, el mito o la historia de fondo, qué significa cada rasgo "
             "del objeto, y lo que la gente cree aunque no esté probado.")


def confiable(liga: str) -> bool:
    casa = urlparse(liga).netloc.lower().removeprefix("www.")
    return any(casa == c or casa.endswith("." + c) for c in CONFIABLES)


def wikipedia(consulta: str, pregunta: str, tope: int = 2) -> list[dict]:
    """Los `tope` artículos de Wikipedia en español que mejor contestan, con su
    texto plano recortado a lo que más toca la pregunta."""
    try:
        r = httpx.get(WIKIPEDIA, headers=AGENTE, timeout=20, params={
            "action": "query", "list": "search", "srsearch": consulta, "srlimit": tope + 1, "format": "json"})
        r.raise_for_status()
        titulos = [x["title"] for x in r.json()["query"]["search"] if "desambiguación" not in x["title"]][:tope]
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        logger.warning("tradiciones: Wikipedia %s: %s", consulta, exc)
        return []
    out = []
    for titulo in titulos:
        try:
            r = httpx.get(WIKIPEDIA, headers=AGENTE, timeout=20, params={
                "action": "query", "prop": "extracts", "explaintext": 1, "titles": titulo, "format": "json"})
            texto = next(iter(r.json()["query"]["pages"].values())).get("extract") or ""
        except (httpx.HTTPError, ValueError, KeyError, StopIteration):
            continue
        if len(texto) > 400:
            out.append({"titulo": titulo, "medio": "es.wikipedia.org",
                        "liga": "https://es.wikipedia.org/wiki/" + titulo.replace(" ", "_"),
                        "texto": expediente.lo_que_toca(texto, pregunta, TOPE_TEXTO)})
    return out


def proponer(tema: str | None, cuantos: int, ya_hechos: str) -> list[dict]:
    """Preguntas "¿por qué…?" con su objeto protagonista. Sin tema, de la temporada.
    Solo con un protagonista que el render sabe dibujar (30/10/2026: la calaverita
    armada con esferas se veía como figuras geométricas)."""
    from dato_mata_gato_bot import instruccion_tradiciones

    hay = instruccion_tradiciones.protagonistas()
    sobre = (f"todas sobre esta tradición: {tema} (cada una una pregunta distinta, con su propio objeto)"
             if tema else "de las fiestas de las próximas semanas en México, o de todo el año si no hay")
    r = ia_gratis.pedir(
        f"Hoy es {datetime.now():%d/%m/%Y}. Busco {cuantos} temas para videos cortos de TikTok en español de "
        "México del nicho \"el porqué de las tradiciones\": una pregunta sobre UN objeto de una tradición "
        "mexicana que casi nadie sabe contestar y cuya respuesta sorprende (\"¿Por qué ponemos cempasúchil a "
        f"los muertos?\": su nombre, la fiesta mexica de las flores, el camino de pétalos). Temas {sobre}.\n"
        "El objeto protagonista TIENE que ser uno de esta lista (es lo único que se puede animar en 3D); "
        "si una tradición no tiene su objeto aquí, no la propongas:\n"
        + "\n".join(f"- {k}: {v}" for k, v in hay.items()) + "\n\n"
        f"No repitas nada de lo ya hecho:\n{ya_hechos[:4000]}\n\n"
        'Responde JSON: {"temas": [{"pregunta": "¿Por qué…?", "objeto": "<el objeto, en palabras>", '
        '"protagonista": "<la clave exacta de la lista, p. ej. Modelo:food/corn>", "busqueda": "<2 a 5 '
        'palabras para buscarlo en Wikipedia>", "por_que": "<una línea: qué sorprende>"}]} con exactamente '
        f"{cuantos} temas, el mejor primero.",
        local=False)
    temas = []
    for t in (r.get("temas") if isinstance(r, dict) else r) or []:
        if not (isinstance(t, dict) and str(t.get("pregunta", "")).strip() and str(t.get("objeto", "")).strip()):
            continue
        if t.get("protagonista") not in hay:
            logger.info("tradiciones: fuera %s (protagonista %s no existe)", t.get("pregunta"), t.get("protagonista"))
            continue
        temas.append({"titulo": t["pregunta"].strip(), "objeto": t["objeto"].strip(),
                      "protagonista": t["protagonista"],
                      "busqueda": str(t.get("busqueda") or t["objeto"]).strip(), "motivo": t.get("por_que", "")})
    return temas


def _web(t: dict) -> list[dict]:
    """Hasta 2 páginas de quienes lo estudian (no Wikipedia: esa ya va aparte)."""
    resultados = expediente.web(f"{t['busqueda']} origen tradición INAH UNAM México Desconocido")
    ligas = [r for r in resultados if confiable(r["liga"]) and "wikipedia.org" not in r["liga"]][:2]
    out = []
    for r in ligas:
        texto = expediente.leer(r["liga"], tope=None)
        if texto:
            out.append({**r, "texto": expediente.lo_que_toca(texto, t["titulo"], TOPE_TEXTO)})
    return out


def investigar(t: dict, con_web: bool = True) -> None:
    t["notas"] = wikipedia(t["busqueda"], t["titulo"]) + (_web(t) if con_web else [])
    try:
        t["datos"] = (expediente.datos(t["titulo"], t["notas"], que=QUE_SACAR, tipos=True)
                      if t["notas"] else [])
    except ia_gratis.SinIA as exc:
        logger.warning("tradiciones: sin datos de %s: %s", t["titulo"][:60], exc)
        t["datos"] = []


def armar(tema: str | None, cuantos: int, ya_hechos: str) -> dict:
    ia_gratis.reiniciar_usados()
    try:
        temas = proponer(tema, cuantos + 1, ya_hechos)
    except ia_gratis.SinIA as exc:
        if ia_gratis.es_cuota(str(exc)):
            raise expediente.SinCuotaGratis(str(exc)) from exc
        raise
    hechos = expediente._hechos()
    temas = expediente.sin_repetir([t for t in temas if not expediente.ya_hecho(t["titulo"], hechos)])
    # Wikipedia en paralelo; la búsqueda web (Groq, ~3 por minuto) solo para los que se van a usar.
    with ThreadPoolExecutor(4) as pool:
        list(pool.map(lambda x: investigar(x[1], con_web=x[0] < cuantos + 1), enumerate(temas)))
    exp = {"formula": "tradiciones", "tema": tema, "modelos": sorted(ia_gratis.usados()),
           "armado": datetime.now().isoformat(timespec="seconds"), "temas": temas}
    try:
        expediente.CARPETA.mkdir(parents=True, exist_ok=True)
        ruta = expediente.CARPETA / f"{datetime.now():%Y%m%d-%H%M%S}-tradiciones.json"
        ruta.write_text(json.dumps(exp, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        exp["ruta"] = str(ruta)
    except OSError:
        pass
    return exp


MARCAS = {"hecho": "✔ HECHO", "saber_popular": "🗣 SABER POPULAR (dilo atribuido: \"dicen que…\")",
          "falso": "✘ FALSO según la fuente (no entra; va a _schema.falsos_descartados)"}


def bloque(exp: dict) -> str:
    partes = [
        "EXPEDIENTE YA INVESTIGADO (lo armé antes, fuera de tu cuota: cada búsqueda tuya se relee en "
        "todos los pasos que siguen)",
        "- ESCOGE TUS TEMAS DE ESTA LISTA. Solo si ninguno sirve, busca otro y di en una línea por qué.",
        "- Las páginas de abajo YA las bajé y leí: cuentan como fuentes abiertas. Lo marcado tiene la cita "
        "comprobada palabra por palabra en esa página.",
        "- Busca por tu cuenta SOLO lo que falte (el mito completo, el significado de un rasgo, una segunda "
        "fuente), con el comando buscar: máximo 4 búsquedas en todo el lote.",
    ]
    for k, t in enumerate(exp["temas"], 1):
        partes.append(f"\nTEMA {k}: {t['titulo']} — objeto: {t['objeto']}"
                      + (f" (protagonista: {t['protagonista']})" if t.get("protagonista") else "")
                      + f"\nPor qué: {t.get('motivo', '')}")
        if not t.get("notas"):
            partes.append("  (no encontré fuentes: si lo usas, búscalo tú)")
        for i, n in enumerate(t.get("notas", [])):
            partes.append(f"  [{i}] {n['medio']} — {n['liga']}")
            for d in t.get("datos", []):
                if d.get("nota") == i and d.get("comprobada"):
                    partes.append(f"      {MARCAS[d['tipo']]}: {expediente.renglon(d)}")
            partes.append("      Extracto: " + re.sub(r"\s+", " ", n["texto"][:expediente.TOPE_EXTRACTO]))
    return "\n".join(partes)


def agregar(texto: str, tema: str | None, cuantos: int, ya_hechos: str, avisar=None) -> str:
    """La instrucción con el expediente, o tal cual si no se pudo armar. Sin cuota
    gratis y SI_SE_ACABA == "preguntar", lanza SinCuotaGratis (como expediente.agregar)."""
    if not expediente.activo():
        return texto
    try:
        exp = armar(tema, cuantos, ya_hechos)
    except expediente.SinCuotaGratis as exc:
        if expediente.SI_SE_ACABA == "preguntar":
            raise
        if avisar:
            avisar(f"🔎 tradiciones: sin cuota gratis; Claude investiga solo ({str(exc)[:80]}).")
        return texto
    except (ia_gratis.SinIA, httpx.HTTPError, ValueError, KeyError) as exc:
        logger.warning("tradiciones: sin expediente: %s", exc)
        return texto
    if not exp["temas"]:
        return texto
    datos = [d for t in exp["temas"] for d in t.get("datos", []) if d.get("comprobada")]
    if avisar:
        avisar(f"🆓 Expediente de tradiciones armado sin Claude ({', '.join(exp['modelos']) or 'IA gratis'}): "
               f"{len(exp['temas'])} temas, {sum(len(t.get('notas', [])) for t in exp['temas'])} fuentes leídas, "
               + ", ".join(f"{sum(d['tipo'] == k for d in datos)} {n}" for k, n in
                           (("hecho", "hechos"), ("saber_popular", "de saber popular"), ("falso", "falsos")))
               + " con cita comprobada. Claude solo escribe.")
    aviso = ("IMPORTANTE: al final de esta instrucción hay un EXPEDIENTE con los temas ya buscados y sus "
             "fuentes ya leídas. Escoge de ahí.\n\n")
    return aviso + texto + "\n\n" + bloque(exp)
