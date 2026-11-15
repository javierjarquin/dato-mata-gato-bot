"""Un guion de papasia en UN turno de Claude (15/11/2026).

Medido el 12/11/2026: los 2 primeros guiones del canal costaron 1.5 millones de
tokens (28 pasos; cada paso relee la instrucción y todo lo anterior). 12 pasos
fueron de investigar y ~10 de explorar el código del bot para entender el
formato. Aquí Claude da un paso por guion:

1. `proponer`: la IA gratis escoge las dudas (fuera de la cuota de Claude).
2. `investigar`: el código busca y lee las páginas de las instituciones de
   salud, y la IA gratis saca los datos, cada uno con su cita comprobada
   palabra por palabra en la página.
3. `escribir`: Claude recibe la instrucción + el expediente de UN tema y
   contesta el guion en JSON. Sin herramientas y sin el system prompt de
   Claude Code. El código lo guarda y lo revisa (`instruccion_papasia.problemas`).
4. Si no pasa, se le manda SOLO la lista de problemas, hasta `CORRECCIONES`
   veces, y contesta solo las escenas que cambian.
5. `anotar`: lo que gastó cada guion queda en su carpeta (`tokens.json`) y en
   la bitácora del canal (`BITACORA`).

No depende de `bot.py`: lo que necesita del bot lo recibe como argumento, para
que el canal se pueda separar sin tocar este archivo.
"""

import csv
import json
import logging
import os
import re
import unicodedata
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

from dato_mata_gato_bot import canal, claude_runner, expediente, ia_gratis
from dato_mata_gato_bot import instruccion_papasia as formula

logger = logging.getLogger(__name__)

# Siempre la carpeta del canal, lo corra quien lo corra (15/11/2026).
ANDROID_IN = canal.entrada("papasia")
PREFIJO = "guion-papasia-"
BITACORA = ANDROID_IN / "fabrica" / "papasia_tokens.csv"
COLUMNAS = ("fecha", "slug", "modelo", "effort", "turnos", "entrada", "lectura_cache", "escritura_cache",
            "salida", "total", "paso", "problemas", "ia_gratis")

# PAPASIA_MODELO vacío = el modelo de la cuenta. PAPASIA_EFFORT: la mitad de la
# salida del 12/11 fue razonamiento, y aquí ya no hay nada que investigar.
MODELO = (os.getenv("PAPASIA_MODELO") or "").strip()
EFFORT = (os.getenv("PAPASIA_EFFORT") or "low").strip()
CORRECCIONES = 2
PAGINAS = 3          # cuántas páginas se leen por tema
TOPE_PAGINA = 5000   # letras de cada página que ve la IA gratis
TOPE_EXTRACTO = 1000  # letras de cada página que ve Claude
MIN_DATOS = 5        # con menos datos comprobados no hay de dónde escribir (3 dio un expediente flaco, 15/11)

SISTEMA = ("Eres el guionista de un canal de videos cortos en español de México para papás y mamás "
           "primerizos. Contestas SOLO con el objeto JSON que se te pide, completo, sin texto antes ni "
           "después y sin ```.")

QUE_SACAR = ("Saca de 6 a 10 datos para un video que le contesta esta duda a un papá primerizo: qué es lo "
             "normal, los números (a qué edad empieza, cuánto dura, cada cuánto), cuándo se quita, lo que "
             "la gente cree, y SOBRE TODO las señales con las que hay que llamar al pediatra y lo que "
             "nunca se debe hacer. Nada de medicamentos ni dosis. Si una nota NO habla de esta duda, no saques "
             "nada de ella.")


# --- 1 y 2. El expediente, sin Claude -------------------------------------------

def _slug(texto: str) -> str:
    plano = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().lower()
    return "-".join(re.findall(r"[a-z0-9]+", plano)[:5])


def _de_institucion(liga: str) -> bool:
    casa = urlparse(liga).netloc.lower().removeprefix("www.")
    return any(casa == d or casa.endswith("." + d) for d in formula.FUENTES_BUENAS)


def proponer(tema: str | None, cuantos: int, ya_hechos: str) -> list[dict]:
    """Las dudas de primerizos, escogidas por la IA gratis."""
    sobre = (f"todas sobre esto: {tema} (cada una una duda distinta)" if tema else
             "de las primeras doce semanas: el llanto, el sueño, las tomas, el hipo, los sobresaltos, la "
             "popó, el peso, la costra láctea, el ombligo, los estornudos, la piel")
    r = ia_gratis.pedir(
        f"Busco {cuantos} temas para videos cortos en español de México para papás y mamás PRIMERIZOS: una "
        "preocupación real de quien acaba de tener su primer bebé, de las que se buscan en el celular de "
        f"madrugada, y que las instituciones de salud contestan claro. Temas {sobre}.\n"
        "NO propongas temas de vacunas, medicamentos, ni enfermedades que haya que diagnosticar.\n"
        "El protagonista es \"Bebe\", o \"Biberon\" si el tema es de alimentación.\n"
        f"No repitas nada de lo ya hecho:\n{ya_hechos[:4000]}\n\n"
        'Responde JSON: {"temas": [{"pregunta": "¿…?, como la diría un papá primerizo", "slug": "<2 a 4 '
        'palabras, minúsculas>", "protagonista": "Bebe|Biberon", "busqueda": "<3 a 6 palabras para buscarlo '
        'en la web de pediatría, en español>", "por_que": "<una línea>"}]} con exactamente '
        f"{cuantos} temas, el mejor primero.",
        rapido=True,  # el 15/11/2026 el modelo fuerte se quedó colgado 5 min; el rápido contesta en 1 s
        local=False, reintentos=1)
    temas = []
    for t in (r.get("temas") if isinstance(r, dict) else r) or []:
        if not (isinstance(t, dict) and str(t.get("pregunta", "")).strip()):
            continue
        slug = _slug(t.get("slug") or t["pregunta"])
        if not slug or any(p.search(t["pregunta"]) for p, _ in formula.PROHIBIDO[:2] + formula.PROHIBIDO[5:]):
            continue
        temas.append({"titulo": t["pregunta"].strip(), "slug": PREFIJO + slug,
                      "protagonista": t.get("protagonista") if t.get("protagonista") in formula.PROTAGONISTAS
                      else "Bebe",
                      "busqueda": str(t.get("busqueda") or t["pregunta"]).strip(),
                      "motivo": str(t.get("por_que", ""))})
    return temas


# Dónde se busca, en orden. Las dos están en español y se dejan leer (medido el
# 15/11/2026: cdc.gov y mayoclinic.org devuelven vacío). Limitar la búsqueda al
# sitio es lo que la hace pertinente: la búsqueda abierta trajo una página de
# lunares para la duda de los pujidos.
SITIOS = ("healthychildren.org/Spanish", "medlineplus.gov/spanish")


def _misma(liga: str) -> str:
    """La liga sin lo que no cambia la página (mayúsculas, ?parámetros)."""
    return unquote(liga).split("?")[0].rstrip("/").lower()


def paginas(t: dict) -> list[dict]:
    """Las páginas de las instituciones cuyo título toca la duda, la más cercana
    primero. DuckDuckGo por sitio (menos de 1 s y sin cuota); si no da nada, la
    búsqueda abierta de `expediente.web`."""
    buscadas = expediente._palabras(t["busqueda"] + " " + t["titulo"])
    vistas, out = set(), []
    for sitio in SITIOS:
        for r in expediente._web_duckduckgo(f"site:{sitio} {t['busqueda']}")[:8]:
            toca = len(expediente._palabras(r.get("titulo", "")) & buscadas)
            if toca and _de_institucion(r["liga"]) and _misma(r["liga"]) not in vistas:
                vistas.add(_misma(r["liga"]))
                out.append({**r, "toca": toca})
    if not out:
        out = [{**r, "toca": 1} for r in expediente.web(f"{t['busqueda']} bebé healthychildren.org medlineplus")
               if _de_institucion(r["liga"])]
    return sorted(out, key=lambda r: -r["toca"])


def investigar(t: dict) -> None:
    """Las páginas de las instituciones que contestan la duda, y sus datos con
    cita comprobada. Deja `t["notas"]` (solo las que dieron datos) y `t["datos"]`."""
    notas = []
    for r in paginas(t):
        if len(notas) == PAGINAS:
            break
        texto = expediente.leer(r["liga"], tope=None)
        if texto and len(texto) > 400:
            notas.append({"liga": r["liga"], "titulo": r.get("titulo", ""),
                          "medio": urlparse(r["liga"]).netloc.removeprefix("www."),
                          "texto": expediente.lo_que_toca(texto, t["titulo"], TOPE_PAGINA)})
    try:
        datos = expediente.datos(t["titulo"], notas, que=QUE_SACAR, tipos=True) if notas else []
    except ia_gratis.SinIA as exc:
        logger.warning("papasia: sin datos de %s: %s", t["titulo"][:60], exc)
        datos = []
    datos = [d for d in datos if d.get("comprobada") and d.get("tipo") != "falso"]
    # Solo quedan las páginas que dieron algo, renumeradas.
    con_datos = sorted({d["nota"] for d in datos})
    t["notas"] = [notas[i] for i in con_datos]
    t["datos"] = [{**d, "nota": con_datos.index(d["nota"])} for d in datos]


def armar(tema: str | None, cuantos: int, ya_hechos: str) -> list[dict]:
    """Los temas que sí tienen de dónde escribirse, con sus fuentes leídas.
    Pide de más: un tema sin fuentes se cae y entra el siguiente."""
    ia_gratis.reiniciar_usados()
    temas = [t for t in proponer(tema, cuantos + 2, ya_hechos)
             if not (ANDROID_IN / t["slug"] / "guion.json").exists()]
    with ThreadPoolExecutor(3) as pool:
        list(pool.map(investigar, temas))
    for t in temas:
        if len(t["datos"]) < MIN_DATOS:
            logger.info("papasia: fuera %s (%d datos comprobados)", t["titulo"], len(t["datos"]))
    return [t for t in temas if len(t["datos"]) >= MIN_DATOS][:cuantos]


MARCAS = {"hecho": "HECHO", "saber_popular": "SABER POPULAR (dilo atribuido)"}


def bloque(t: dict) -> str:
    """El expediente de un tema, como lo lee Claude."""
    partes = [
        "EXPEDIENTE (ya investigado; no tienes herramientas ni hace falta buscar nada)",
        "- Usa SOLO lo que está aquí. Lo que no esté, no lo afirmes: un dato de memoria no entra.",
        "- Cada dato trae entre «» la cita literal de la página. En _schema.fuentes pon, para cada "
        "escena con respaldo, qué dice, quién lo dice y LA LIGA COMPLETA de esa página, tal cual "
        "viene aquí: una liga que no esté en este expediente se rechaza.",
        f"\nLA DUDA: {t['titulo']}",
    ]
    for i, n in enumerate(t["notas"]):
        partes.append(f"\n[{i}] {n['medio']} — {n['liga']}")
        for d in t["datos"]:
            if d.get("nota") == i:
                partes.append(f"   {MARCAS[d['tipo']]}: {expediente.renglon(d)}")
        partes.append("   Extracto: " + re.sub(r"\s+", " ", expediente.lo_que_toca(
            n["texto"], t["titulo"], TOPE_EXTRACTO)))
    return "\n".join(partes)


# --- 3. La instrucción de un turno ----------------------------------------------

EJEMPLO = ('{"id": "numeros", "tiempo": "numeros", "respaldo": "hecho", "texto": "Empieza cerca de las dos '
           'semanas y llega a su punto más alto a las seis.", "camara": "plano", "visual": [{"objeto": '
           '"Calendario", "casillas": 12, "marcada": 5, "marca": {"de": 0, "a": 1, "desde": 0.4, "hasta": 0.8}}, '
           '{"objeto": "Bebe", '
           '"escala": 0.5, "posicion": [1.4, 0, 0], "llora": 0.6}], "etiquetas": [{"titulo": "Semana seis", '
           '"subtitulo": "Academia Americana de Pediatría", "desde": 0.45, "hasta": 0.95}], "claves": '
           '["dos", "semanas", "seis"]}')


def _catalogo() -> str:
    """El catálogo sin la biblioteca de modelos de tradiciones (comida, panteón,
    fiestas): 4 mil letras que en este canal no se usan."""
    lineas = [f"  - {nombre}: {que}. " + ", ".join(f"{k} ({v})" for k, v in props.items())
              for nombre, (que, props) in formula.CATALOGO.items() if nombre != "Modelo"]
    lineas.append("  Todos aceptan además: " + ", ".join(f"{k} ({v})" for k, v in formula.COMUNES.items()))
    return "\n".join(lineas)


def instruccion(t: dict) -> str:
    """La fórmula del canal (la misma de `instruccion_papasia`) para UN guion que
    se contesta en JSON, más el expediente del tema."""
    base, _, resto = formula.INSTRUCCION.partition("FORMATO DE CADA GUION")
    molde = resto.partition("{")[2].partition("\nAL TERMINAR")[0]
    if not base or not molde:
        raise RuntimeError("instruccion_papasia.INSTRUCCION cambió de forma: revisa papasia_guion.instruccion")
    texto = (base.replace("<<N>> guiones", "UN guion").replace("<<N>>", "1")
             .replace("<<TEMA>>", f"{t['titulo']} (protagonista: {t['protagonista']})")
             .replace("y abriste la página", "y viene en el EXPEDIENTE de abajo")
             .replace("<<CATALOGO>>", _catalogo())
             .replace("<<FUENTES>>", "las del expediente")
             .replace("<<PROTAGONISTAS>>", "; ".join(f"{k} ({v})" for k, v in formula.PROTAGONISTAS.items()))
             .replace("<<CAMARAS>>", "; ".join(f"{k} ({v})" for k, v in formula.CAMARAS.items())))
    return (texto
            + "UNA ESCENA COMPLETA, DE EJEMPLO (todas llevan estas mismas llaves)\n" + EJEMPLO + "\n\n"
            + "TU RESPUESTA\nSOLO este objeto JSON, sin texto antes ni después y sin ```:\n{" + molde.rstrip()
            + "\n\n" + bloque(t))


# --- 4. Escribir, revisar y corregir --------------------------------------------

@dataclass
class Guion:
    slug: str
    problemas: list[str] = field(default_factory=list)
    tokens: dict = field(default_factory=dict)
    sesion: str = ""
    turnos: int = 0
    error: str = ""          # el de Claude, si no contestó (p. ej. el límite de uso)

    @property
    def paso(self) -> bool:
        return not self.problemas and not self.error


def _json_de(texto: str):
    """El objeto JSON de una respuesta, aunque venga con ``` o una línea de más."""
    texto = (texto or "").strip()
    inicio, fin = texto.find("{"), texto.rfind("}")
    for intento in (texto, texto[inicio:fin + 1] if 0 <= inicio < fin else ""):
        try:
            r = json.loads(intento)
            return r if isinstance(r, dict) else None
        except ValueError:
            continue
    return None


def aplicar(guion: dict | None, respuesta: dict) -> dict:
    """La respuesta de una corrección sobre el guion: si trae "formato" es el
    guion entero; si no, sus escenas sustituyen a las del mismo id y el resto de
    las llaves a las de arriba (las fuentes se suman)."""
    if guion is None or "formato" in respuesta:
        return respuesta
    nuevo = {**guion}
    for k, v in respuesta.items():
        if k == "escenas" and isinstance(v, list):
            por_id = {e.get("id"): e for e in v if isinstance(e, dict)}
            nuevo["escenas"] = [por_id.get(e.get("id"), e) for e in guion.get("escenas") or []]
        elif k == "_schema" and isinstance(v, dict):
            viejo = guion.get("_schema") or {}
            nuevo["_schema"] = {**viejo, **v, "fuentes": {**(viejo.get("fuentes") or {}),
                                                          **(v.get("fuentes") or {})}}
        else:
            nuevo[k] = v
    return nuevo


def limpiar(guion: dict) -> None:
    """Lo que el código arregla solo, sin gastar un turno de corrección: las
    "claves" que la voz no dice en su escena (el único problema de la primera
    corrida real, 15/11/2026). Si quedan menos de 2, no las toca y lo ve Claude."""
    for e in guion.get("escenas") or []:
        if not isinstance(e, dict) or not isinstance(e.get("claves"), list):
            continue
        dichas = {formula._trad._norma(w) for w in str(e.get("texto", "")).split()}
        # "leche materna" son dos claves, no una (Sonnet y Haiku las dieron así).
        sueltas = [w for c in e["claves"] for w in str(c).split()]
        buenas = list(dict.fromkeys(w for w in sueltas if formula._trad._norma(w) in dichas))[:4]
        if len(buenas) >= 2:
            e["claves"] = buenas


def problemas(guion: dict, t: dict) -> list[str]:
    """La revisión del canal, más una que solo se puede hacer aquí: que las ligas
    de las fuentes sean páginas que de verdad se leyeron."""
    out = formula.problemas(guion)
    leidas = {_misma(n["liga"]) for n in t["notas"]}
    for eid, fuente in ((guion.get("_schema") or {}).get("fuentes") or {}).items():
        for liga in re.findall(r"https?://[^\s,;)\"']+", str(fuente)):
            if _misma(liga.rstrip(".")) not in leidas:
                out.append(f"{eid}: la liga {liga} no es del expediente; usa solo las páginas que te di")
    return out


def escribir(t: dict, contar_tokens=None, modelo: str | None = None, effort: str | None = None) -> Guion:
    """Un guion: un turno para escribir y hasta CORRECCIONES para corregir, en la
    misma sesión. Lo que pase la revisión (o lo último que haya) queda en disco.
    `contar_tokens(sesiones)` es `fabrica.tokens_de_sesiones`."""
    g = Guion(t["slug"], sesion=str(uuid.uuid4()))
    mensaje, guion = instruccion(t), None
    ruta = ANDROID_IN / t["slug"] / "guion.json"
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
            guion.setdefault("formato", "papasia")
            limpiar(guion)
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_text(json.dumps(guion, ensure_ascii=False, indent=1), encoding="utf-8")
            g.problemas = problemas(guion, t)
        if not g.problemas:
            break
        mensaje = ("La revisión marcó esto:\n" + "\n".join(f"- {p}" for p in g.problemas) + "\n\n"
                   'Corrígelo TODO. Responde SOLO un objeto JSON con lo que cambia: {"escenas": [las escenas '
                   "corregidas, COMPLETAS y con su mismo id], y las llaves de arriba que cambien (titulo, "
                   "descripcion, hashtags, plus, _schema)}. No repitas las escenas que no cambian. Si hay que "
                   "agregar, quitar o reordenar escenas, responde el guion ENTERO (con \"formato\").")
    return g


# --- 5. La bitácora -------------------------------------------------------------

def anotar(g: Guion, modelo: str = "", effort: str = "", gratis: str = "") -> None:
    """Lo que costó el guion: en su carpeta y en la bitácora del canal."""
    fila = {"fecha": datetime.now().isoformat(timespec="seconds"), "slug": g.slug,
            "modelo": modelo or MODELO or "(el de la cuenta)", "effort": effort or EFFORT, "turnos": g.turnos,
            **{k: g.tokens.get(k, 0) for k in ("entrada", "lectura_cache", "escritura_cache", "salida", "total")},
            "paso": "si" if g.paso else "no", "problemas": "; ".join(g.problemas)[:300] or g.error[:300],
            "ia_gratis": gratis}
    try:
        carpeta = ANDROID_IN / g.slug
        if carpeta.is_dir():
            (carpeta / "tokens.json").write_text(json.dumps({**fila, "sesion": g.sesion}, ensure_ascii=False,
                                                            indent=1), encoding="utf-8")
        BITACORA.parent.mkdir(parents=True, exist_ok=True)
        nueva = not BITACORA.exists()
        with BITACORA.open("a", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, COLUMNAS)
            if nueva:
                w.writeheader()
            w.writerow(fila)
    except OSError as exc:
        logger.warning("papasia: no pude anotar los tokens de %s: %s", g.slug, exc)


def renglon(g: Guion) -> str:
    """Un guion, para el aviso de Telegram."""
    t = g.tokens
    gasto = (f"{t.get('total', 0):,} tokens ({t.get('salida', 0):,} de salida) en {g.turnos} turno(s)"
             if t else f"{g.turnos} turno(s)")
    if g.paso:
        return f"✅ {g.slug}: {gasto}"
    return f"⚠️ {g.slug}: no pasó ({gasto}): " + ("; ".join(g.problemas[:4]) or g.error)


def lote(tema: str | None, cantidad: int, ya_hechos: str, contar_tokens=None, avisar=None,
         es_limite=claude_runner.es_limite_de_uso) -> tuple[list[Guion], str | None]:
    """El lote entero. Devuelve (los guiones, el mensaje de límite de Claude si se
    cortó por eso). Lanza `ia_gratis.SinIA` si no se pudo armar ni un expediente:
    quien llama decide si escribe como antes."""
    temas = armar(tema, cantidad, ya_hechos)
    if not temas:
        raise ia_gratis.SinIA("no encontré dudas con fuentes de instituciones de salud")
    gratis = ", ".join(sorted(ia_gratis.usados()))
    if avisar:
        avisar(f"🆓 Expediente de papasia armado sin Claude ({gratis or 'IA gratis'}): {len(temas)} dudas, "
               f"{sum(len(t['notas']) for t in temas)} páginas leídas, "
               f"{sum(len(t['datos']) for t in temas)} datos con cita comprobada. Claude escribe en un turno.")
    hechos: list[Guion] = []
    for t in temas:
        g = escribir(t, contar_tokens)
        anotar(g, gratis=gratis)
        hechos.append(g)
        if g.error and es_limite(g.error):
            return hechos, g.error
    return hechos, None
