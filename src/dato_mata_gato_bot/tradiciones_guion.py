"""Un guion de tradiciones en UN turno de Claude (22/11/2026).

Auditoría del 22/11: un guion de Dato Mata Gato costaba de 0.7 a 1.8 millones
de tokens (lotes `todos-*` del 07 al 18/11) y uno de papasia ~25 mil, porque
papasia ya no le da a Claude una sesión con herramientas: el código arma el
expediente y Claude contesta el guion en JSON, en un turno. Tradiciones tenía
casi todo para hacer lo mismo (su expediente ya se armaba con IA gratis:
Wikipedia, INAH, UNAM, con cita comprobada), pero Claude seguía escogiendo el
tema, buscando más, escribiendo el archivo y corriendo la revisión, paso por
paso, releyendo todo en cada uno.

1. `armar`: `expediente_tradiciones.armar` propone los temas (solo con un
   protagonista que el render sabe dibujar) y lee sus fuentes.
2. `escribir`: Claude recibe la fórmula + el expediente de UN tema y contesta el
   guion en JSON, sin herramientas ni el system prompt de Claude Code.
3. El código lo guarda y lo revisa (`instruccion_tradiciones.problemas` + que
   cada liga de `_schema.fuentes` sea de una página que de verdad se leyó). Si no
   pasa, solo se le manda la lista de problemas, hasta CORRECCIONES veces.
4. `anotar`: el gasto queda en `<slug>\\tokens.json` y en la bitácora
   `C:\\Android_in\\fabrica\\tradiciones_tokens.csv`.

Se apaga con TRADICIONES_UN_TURNO=0 (vuelve la sesión con herramientas).
"""

import csv
import json
import logging
import os
import re
import uuid
from datetime import datetime

from dato_mata_gato_bot import claude_runner, expediente, expediente_tradiciones, ia_gratis, pipeline
from dato_mata_gato_bot import instruccion_tradiciones as formula
from dato_mata_gato_bot.papasia_guion import Guion, _json_de, _misma, _slug, aplicar, limpiar, renglon

logger = logging.getLogger(__name__)

PREFIJO = "guion-tradicion-"
COLUMNAS = ("fecha", "slug", "modelo", "effort", "turnos", "entrada", "lectura_cache", "escritura_cache",
            "salida", "total", "paso", "problemas", "ia_gratis")
MODELO = (os.getenv("TRADICIONES_MODELO") or "").strip()
EFFORT = (os.getenv("TRADICIONES_EFFORT") or "low").strip()
CORRECCIONES = 2
MIN_DATOS = 3         # datos con cita comprobada (hecho o saber popular) para tener de dónde escribir
TOPE_EXTRACTO = 1200  # letras de cada fuente que ve Claude, además de los datos

SISTEMA = ("Eres el guionista de Dato Mata Gato, un canal de videos cortos en español de México. "
           "Contestas SOLO con el objeto JSON que se te pide, completo, sin texto antes ni después y sin ```.")


def un_turno() -> bool:
    return (os.getenv("TRADICIONES_UN_TURNO") or "1").strip() != "0"


def _bitacora():
    return pipeline.ANDROID_IN / "fabrica" / "tradiciones_tokens.csv"


# --- 1. El expediente, sin Claude ------------------------------------------------

def _con_respaldo(t: dict) -> list[dict]:
    return [d for d in t.get("datos") or [] if d.get("comprobada") and d.get("tipo") in ("hecho", "saber_popular")]


def armar(tema: str | None, cuantos: int, ya_hechos: str) -> tuple[list[dict], dict]:
    """Los temas con de dónde escribirse (y su slug), y el expediente entero."""
    exp = expediente_tradiciones.armar(tema, cuantos, ya_hechos)
    temas = []
    for t in exp["temas"]:
        t["slug"] = PREFIJO + _slug(t.get("objeto") or t["titulo"])
        if (pipeline.ANDROID_IN / t["slug"] / "guion.json").exists():
            continue
        if len(_con_respaldo(t)) < MIN_DATOS:
            logger.info("tradiciones: fuera %s (%d datos comprobados)", t["titulo"], len(_con_respaldo(t)))
            continue
        temas.append(t)
    return temas[:cuantos], exp


def bloque(t: dict) -> str:
    """El expediente de UN tema, como lo lee Claude."""
    partes = [
        "EXPEDIENTE (ya investigado; no tienes herramientas ni hace falta buscar nada)",
        "- Usa SOLO lo que está aquí. Lo que no esté, no lo afirmes: un dato de memoria no entra. Si el mito "
        "o un rasgo no viene, cuenta lo que sí viene.",
        "- Lo marcado tiene la cita literal comprobada en la página. En _schema.fuentes pon, para cada escena "
        "con respaldo, qué dice, quién lo dice y LA LIGA COMPLETA de esa página, tal cual viene aquí: una "
        "liga que no esté en este expediente se rechaza.",
        f"\nLA PREGUNTA: {t['titulo']}",
        f"EL OBJETO: {t['objeto']} (protagonista: {t['protagonista']})",
        f"POR QUÉ SORPRENDE: {t.get('motivo', '')}",
    ]
    for i, n in enumerate(t.get("notas") or []):
        partes.append(f"\n[{i}] {n['medio']} — {n['liga']}")
        for d in t.get("datos") or []:
            if d.get("nota") == i and d.get("comprobada"):
                partes.append(f"   {expediente_tradiciones.MARCAS[d['tipo']]}: {expediente.renglon(d)}")
        partes.append("   Extracto: " + re.sub(r"\s+", " ", expediente.lo_que_toca(
            n["texto"], t["titulo"], TOPE_EXTRACTO)))
    return "\n".join(partes)


# --- 2. La instrucción de un turno -----------------------------------------------

def _protagonista(clave: str) -> str:
    """'Modelo:food/corn' -> {"objeto": "Modelo", "modelo": "food/corn"}; 'Flor' -> {"objeto": "Flor"}."""
    objeto, _, modelo = clave.partition(":")
    return json.dumps({"objeto": objeto, **({"modelo": modelo} if modelo else {})}, ensure_ascii=False)


def instruccion(t: dict) -> str:
    """La fórmula de siempre (`instruccion_tradiciones.INSTRUCCION`) para UN guion
    que se contesta en JSON, más el expediente del tema."""
    base, _, resto = formula.INSTRUCCION.partition("FORMATO DE CADA GUION")
    molde = resto.partition("{")[2].partition("\nAL TERMINAR")[0]
    if not base or not molde or "<<TEMA>>" not in base:
        raise RuntimeError("instruccion_tradiciones.INSTRUCCION cambió de forma: revisa tradiciones_guion")
    tema = (f"{t['titulo']} El objeto es {t['objeto']} y el protagonista ya está escogido: "
            f"{_protagonista(t['protagonista'])}.")
    texto = (base.replace("<<N>> guiones", "UN guion").replace("<<N>>", "1")
             .replace("<<TEMA>>", tema)
             .replace("tiene fuente que abriste y leíste", "tiene fuente en el EXPEDIENTE de abajo")
             .replace("<<CATALOGO>>", formula._catalogo())
             .replace("<<PROTAGONISTAS>>", "; ".join(f"{k} ({v})" for k, v in formula.PROTAGONISTAS.items()))
             .replace("<<CAMARAS>>", "; ".join(f"{k} ({v})" for k, v in formula.CAMARAS.items())))
    return (texto
            + f"TU RESPUESTA\nSOLO este objeto JSON (el slug ya es \"{t['slug']}\"), sin texto antes ni "
            + "después y sin ```:\n{" + molde.rstrip()
            + "\n\n" + bloque(t))


# --- 3. Escribir, revisar y corregir ---------------------------------------------

def problemas(guion: dict, t: dict) -> list[str]:
    """La revisión del nicho, más que las ligas de las fuentes sean páginas leídas."""
    out = formula.problemas(guion)
    leidas = {_misma(n["liga"]) for n in t.get("notas") or []}
    for eid, fuente in ((guion.get("_schema") or {}).get("fuentes") or {}).items():
        for liga in re.findall(r"https?://[^\s,;)\"']+", str(fuente)):
            if _misma(liga.rstrip(".")) not in leidas:
                out.append(f"{eid}: la liga {liga} no es del expediente; usa solo las páginas que te di")
    return out


def escribir(t: dict, contar_tokens=None, modelo: str | None = None, effort: str | None = None) -> Guion:
    """Un guion: un turno para escribir y hasta CORRECCIONES para corregir, en la
    misma sesión. Lo que pase la revisión (o lo último que haya) queda en disco."""
    g = Guion(t["slug"], sesion=str(uuid.uuid4()))
    mensaje, guion = instruccion(t), None
    ruta = pipeline.ANDROID_IN / t["slug"] / "guion.json"
    for intento in range(CORRECCIONES + 1):
        r = claude_runner.run_turn(g.sesion, mensaje, is_new_session=(intento == 0), ligera=True,
                                   herramientas="", sistema=SISTEMA,
                                   modelo=modelo or MODELO or None, effort=effort or EFFORT or None)
        g.turnos += 1
        if contar_tokens:
            g.tokens = contar_tokens([g.sesion])
        if not r.ok:
            g.error = r.text[:400]
            break
        respuesta = _json_de(r.text)
        if respuesta is None:
            g.problemas = ["tu respuesta no fue UN objeto JSON con el guion"]
        else:
            guion = aplicar(guion, respuesta)
            guion["formato"] = "tradiciones"
            guion["slug"] = t["slug"]
            limpiar(guion)
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_text(json.dumps(guion, ensure_ascii=False, indent=1), encoding="utf-8")
            g.problemas = problemas(guion, t)
        if not g.problemas:
            break
        mensaje = ("La revisión marcó esto:\n" + "\n".join(f"- {p}" for p in g.problemas) + "\n\n"
                   'Corrígelo TODO. Responde SOLO un objeto JSON con lo que cambia: {"escenas": [las escenas '
                   "corregidas, COMPLETAS y con su mismo id], y las llaves de arriba que cambien (titulo, "
                   "objeto, protagonista, descripcion, hashtags, plus, _schema)}. No repitas las escenas que "
                   "no cambian. Si hay que agregar, quitar o reordenar escenas, responde el guion ENTERO "
                   "(con \"formato\").")
    return g


# --- 4. La bitácora --------------------------------------------------------------

def anotar(g: Guion, modelo: str = "", effort: str = "", gratis: str = "") -> None:
    fila = {"fecha": datetime.now().isoformat(timespec="seconds"), "slug": g.slug,
            "modelo": modelo or MODELO or "(el de la cuenta)", "effort": effort or EFFORT, "turnos": g.turnos,
            **{k: g.tokens.get(k, 0) for k in ("entrada", "lectura_cache", "escritura_cache", "salida", "total")},
            "paso": "si" if g.paso else "no", "problemas": "; ".join(g.problemas)[:300] or g.error[:300],
            "ia_gratis": gratis}
    try:
        carpeta = pipeline.ANDROID_IN / g.slug
        if carpeta.is_dir():
            (carpeta / "tokens.json").write_text(json.dumps({**fila, "sesion": g.sesion}, ensure_ascii=False,
                                                            indent=1), encoding="utf-8")
        bitacora = _bitacora()
        bitacora.parent.mkdir(parents=True, exist_ok=True)
        nueva = not bitacora.exists()
        with bitacora.open("a", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, COLUMNAS)
            if nueva:
                w.writeheader()
            w.writerow(fila)
    except OSError as exc:
        logger.warning("tradiciones: no pude anotar los tokens de %s: %s", g.slug, exc)


def lote(tema: str | None, cantidad: int, ya_hechos: str, contar_tokens=None, avisar=None,
         es_limite=claude_runner.hay_que_parar) -> tuple[list[Guion], str | None]:
    """El lote entero. Devuelve (los guiones, el mensaje de Claude si se cortó por
    cuota o CLI viejo). Lanza `ia_gratis.SinIA` si no hay ni un tema con fuentes
    (quien llama decide si escribe como antes) y `expediente.SinCuotaGratis` tal
    cual sale del expediente."""
    temas, exp = armar(tema, cantidad, ya_hechos)
    if not temas:
        raise ia_gratis.SinIA("no encontré temas de tradiciones con fuentes comprobadas")
    gratis = ", ".join(exp.get("modelos") or [])
    if avisar:
        avisar(f"🆓 Expediente de tradiciones armado sin Claude ({gratis or 'IA gratis'}): {len(temas)} temas, "
               f"{sum(len(t.get('notas') or []) for t in temas)} fuentes leídas, "
               f"{sum(len(_con_respaldo(t)) for t in temas)} datos con cita comprobada. "
               "Claude escribe cada guion en un turno.")
    hechos: list[Guion] = []
    for t in temas:
        g = escribir(t, contar_tokens)
        anotar(g, gratis=gratis)
        hechos.append(g)
        if g.error and es_limite(g.error):
            return hechos, g.error
    return hechos, None
