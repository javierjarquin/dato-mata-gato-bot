"""Fábrica de lotes grandes (12/10/2026): 1000 videos sin que nadie la cuide.

Antes, un lote dependía de que alguien estuviera ahí: si se acababa la cuota de
Claude había que correr /completarlote a mano; si VoiceStudio se caía (Exited
255, varias veces) los videos fallaban uno tras otro; si Windows se reiniciaba
la tanda se perdía. A ~38 min por video, 1000 videos son ~26 días seguidos.

Cómo funciona:
- Todo el avance vive en `ANDROID_IN/fabrica/<lote>/estado.json`. Nada está
  solo en memoria: cualquier corte se retoma desde ahí.
- `ciclo()` hace el trabajo: levanta Docker y VoiceStudio si hace falta,
  mantiene un colchón de guiones (los escribe Claude de `POR_TANDA` en
  `POR_TANDA`, con la MISMA instrucción y revisión que /lotefish3) y renderiza
  un video a la vez, cada uno en su propio proceso con límite de tiempo.
- Si se acaba la cuota de Claude, se anota hasta cuándo y se sigue
  renderizando lo que ya hay. Los guiones se retoman solos al liberarse.
- Un fallido se reintenta UNA vez (otra voz no: la misma, para no ensuciar la
  prueba de voces). El segundo fallo lo deja como fallido y avisa.
- El Programador de tareas de Windows llama a `ciclo()` cada 15 minutos (ver
  tools/fabrica.py instalar); tras un reinicio vuelve a correr al iniciar sesión. Un latido en disco evita que
  corran dos a la vez: si el latido tiene más de 20 min, el ciclo anterior
  murió y el nuevo toma su lugar.
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

from dato_mata_gato_bot import expediente, formatos, lote_grande, pipeline

logger = logging.getLogger(__name__)

RAIZ = pipeline.ANDROID_IN / "fabrica"
POR_TANDA = 10          # guiones por pedido a Claude (lo que ya se probaba con /lotefish3)
COLCHON = 5             # con menos pendientes, se escribe la tanda siguiente: 10
                        # videos son ~6.3 h de render, una tanda cada ~6 h
MAX_INTENTOS = 2        # el original y un reintento
TIMEOUT_VIDEO = 3 * 3600  # un video tarda ~38 min; 3 h ya es que algo se colgó
LATIDO_VIEJO = 20 * 60
ESPERA_CUOTA = 30 * 60  # si el aviso de Claude no dice la hora, se reintenta en 30 min
AVISO_INFRA_CADA = 3600
DISCO_MINIMO_GB = 20

BOT_PY = Path(sys.executable)
DOCKER_DESKTOP = r"C:\Program Files\Docker\Docker\Docker Desktop.exe"
VOICESTUDIO = "http://localhost:3900/engines/tts"
_SIN_VENTANA = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # corre oculto (pythonw)


# --------------------------------------------------------------------- estado

def ruta_estado(lote: str) -> Path:
    return RAIZ / lote / "estado.json"


def leer(lote: str) -> dict:
    return json.loads(ruta_estado(lote).read_text(encoding="utf-8"))


def guardar(lote: str, estado: dict) -> None:
    """Escritura atómica: un corte a mitad no deja un estado.json roto.

    Y respeta un /pararfabrica que haya entrado mientras tanto (15/10/2026). El
    ciclo lee el estado al empezar la vuelta y lo guarda minutos u horas después
    -- `escribir_tanda` tarda lo que Claude tarde en investigar y escribir. Si en
    esa ventana el bot marcó el lote como detenido, la copia vieja en memoria lo
    revivía al guardar, y la tarea de Windows lo retomaba como si nada. Pasó con
    `viral-20261015-1856`: Javier canceló un lote de 5 y se generó igual.
    La bandera `detenida` solo la pone el bot, así que si está en disco gana.
    """
    ruta = ruta_estado(lote)
    if "detenida" not in estado:
        try:
            previo = leer(lote)
        except (OSError, ValueError):
            previo = {}
        if previo.get("detenida"):
            estado = {**estado, "detenida": previo["detenida"], "terminado": True}
    tmp = ruta.with_suffix(".tmp")
    tmp.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, ruta)


def detenida(lote: str) -> bool:
    """¿Entró un /pararfabrica? Se relee del disco: el ciclo puede llevar horas
    con su copia en memoria (ver `guardar`)."""
    try:
        return bool(leer(lote).get("detenida"))
    except (OSError, ValueError):
        return False


def crear(lote: str, objetivo: int, formato: str = "cercania", **opciones) -> dict:
    """`opciones` (modo automático de /lotegrande, 14/10/2026): horas_claude
    ("" = todo el día, "0-9"), tema (una clave de instruccion_cercania o None =
    repartido), por_tanda, colchon y vigencias (mezcla conversacion/perenne)."""
    ruta = ruta_estado(lote)
    if ruta.exists():
        raise FileExistsError(f"Ya existe la fábrica '{lote}': {ruta}")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    estado = {
        "lote": lote, "objetivo": objetivo, "formato": formato,
        "creado": datetime.now().isoformat(timespec="seconds"),
        "carpeta_videos": str(pipeline.ANDROID_IN / "lotes" / lote),
        "guiones_pedidos": 0, "videos": {}, "cuota_libre_desde": None,
        "ultimo_aviso_infra": 0, "terminado": False,
        **opciones,
    }
    guardar(lote, estado)
    return estado


def pendientes(estado: dict) -> list[str]:
    """Los que faltan, en el orden en que se escribieron. Un fallido con
    intentos de sobra vuelve a la fila, pero DETRÁS de los nuevos."""
    nuevos = [s for s, v in estado["videos"].items() if v["estado"] == "pendiente"]
    # Los temas de conversación son de este mes: van antes que las perennes.
    nuevos.sort(key=lambda s: estado["videos"][s].get("vigencia") not in ("conversacion", "noticia"))
    reintentos = [s for s, v in estado["videos"].items()
                  if v["estado"] == "fallido" and v["intentos"] < MAX_INTENTOS]
    return nuevos + reintentos


def resumen(estado: dict) -> str:
    vs = estado["videos"].values()
    cuenta = {e: sum(1 for v in vs if v["estado"] == e) for e in ("listo", "pendiente", "fallido")}
    return (f"{estado['lote']}: {cuenta['listo']} listos, {cuenta['pendiente']} pendientes, "
            f"{cuenta['fallido']} fallidos, {len(estado['videos'])}/{estado['objetivo']} guiones escritos")


def hora_de_reset(texto: str, ahora: datetime) -> datetime:
    """'You've hit your session limit · resets 3:40pm' -> la próxima 3:40 pm.
    Sin hora legible, se reintenta en ESPERA_CUOTA."""
    # El límite SEMANAL trae fecha o día (14/10/2026): "resets Oct 20, 3pm",
    # "resets Mon 9am". Sin fecha es el de la sesión de 5 h: la próxima vez que
    # llegue esa hora.
    m = re.search(r"resets\s+(?:(?:on\s+)?(?P<fecha>[a-z]{3,9})\.?\s*(?P<dia>\d{1,2})?(?:st|nd|rd|th)?,?\s+"
                  r"(?:at\s+)?)?(?:at\s+)?(?P<h>\d{1,2})(?::(?P<mi>\d{2}))?\s*(?P<ampm>[ap]\.?m\.?)?",
                  texto or "", re.IGNORECASE)
    if not m:
        return ahora + timedelta(seconds=ESPERA_CUOTA)
    h, mi = int(m.group("h")), int(m.group("mi") or 0)
    ampm = (m.group("ampm") or "").lower().replace(".", "")
    if ampm == "pm" and h != 12:
        h += 12
    if ampm == "am" and h == 12:
        h = 0
    cuando = ahora.replace(hour=h % 24, minute=mi, second=0, microsecond=0)
    palabra = (m.group("fecha") or "").lower()[:3]
    meses = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    dias = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    if palabra in meses and m.group("dia"):
        cuando = cuando.replace(month=meses.index(palabra) + 1, day=int(m.group("dia")))
        if cuando <= ahora:
            cuando = cuando.replace(year=cuando.year + 1)
    elif palabra in dias:
        cuando += timedelta(days=(dias.index(palabra) - ahora.weekday()) % 7)
        if cuando <= ahora:
            cuando += timedelta(days=7)
    elif cuando <= ahora:
        cuando += timedelta(days=1)
    return cuando + timedelta(minutes=2)


# ------------------------------------------------------------------- telegram

def telegram(texto: str, video: Path | None = None) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = (os.getenv("TELEGRAM_ALLOWED_CHAT_IDS") or "").split(",")[0].strip()
    if not (token and chat):
        return
    for _ in range(3):  # Telegram corta conexiones de vez en cuando
        try:
            if video is None:
                requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                              data={"chat_id": chat, "text": texto[:4000]}, timeout=30)
            else:
                with open(video, "rb") as f:
                    requests.post(f"https://api.telegram.org/bot{token}/sendVideo",
                                  data={"chat_id": chat, "caption": texto[:1000],
                                        "supports_streaming": "true"},
                                  files={"video": f}, timeout=600)
            return
        except Exception as exc:  # noqa: BLE001 -- un aviso nunca tira la fábrica
            logger.warning("Telegram: %s", exc)
            time.sleep(5)


def telegram_fotos(fotos: list[tuple[Path, str]]) -> None:
    """Varias fotos en un solo mensaje (las portadas del video, 14/10/2026)."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = (os.getenv("TELEGRAM_ALLOWED_CHAT_IDS") or "").split(",")[0].strip()
    fotos = [(r, c) for r, c in fotos if r.exists()]
    if not (token and chat and fotos):
        return
    media = [{"type": "photo", "media": f"attach://f{i}", "caption": c} for i, (_, c) in enumerate(fotos)]
    for _ in range(3):
        archivos = {f"f{i}": open(r, "rb") for i, (r, _) in enumerate(fotos)}
        try:
            if len(fotos) == 1:  # sendMediaGroup pide de 2 a 10 fotos
                requests.post(f"https://api.telegram.org/bot{token}/sendPhoto",
                              data={"chat_id": chat, "caption": fotos[0][1]},
                              files={"photo": archivos["f0"]}, timeout=300)
            else:
                requests.post(f"https://api.telegram.org/bot{token}/sendMediaGroup",
                              data={"chat_id": chat, "media": json.dumps(media)}, files=archivos, timeout=300)
            return
        except Exception as exc:  # noqa: BLE001 -- un aviso nunca tira la fábrica
            logger.warning("Telegram fotos: %s", exc)
            time.sleep(5)
        finally:
            for f in archivos.values():
                f.close()


class _Avisador:
    """Lo único que usan del `update` de Telegram las funciones del bot que
    escriben y revisan guiones es `update.message.reply_text`."""

    class _Mensaje:
        async def reply_text(self, texto, **_):
            telegram(texto)

    message = _Mensaje()


# ---------------------------------------------------------------- infraestructura

def _voicestudio_responde() -> bool:
    try:
        return requests.get(VOICESTUDIO, timeout=10).status_code == 200
    except requests.RequestException:
        return False


def _docker_ok() -> bool:
    return subprocess.run(["docker", "info"], capture_output=True, creationflags=_SIN_VENTANA).returncode == 0


def asegurar_infra() -> str | None:
    """Docker Desktop y VoiceStudio arriba. Devuelve el problema, o None."""
    if _voicestudio_responde():
        return None
    if not _docker_ok():
        logger.warning("Docker no responde: arranco Docker Desktop")
        subprocess.Popen([DOCKER_DESKTOP])
        for _ in range(36):
            time.sleep(5)
            if _docker_ok():
                break
        else:
            return "Docker Desktop no arrancó en 3 minutos."
    subprocess.run(["docker", "start", "voicestudio"], capture_output=True, creationflags=_SIN_VENTANA)
    for _ in range(60):
        if _voicestudio_responde():
            return None
        time.sleep(5)
    return "VoiceStudio no responde ni después de reiniciarlo (5 min)."


# ----------------------------------------------------------------------- latido

def _ruta_latido(lote: str) -> Path:
    return RAIZ / lote / "latido.json"


def _proceso_vivo(pid: int) -> bool:
    """¿Sigue corriendo ese proceso? En la prueba de corte del 12/10/2026 el
    latido quedó fresco tras matar el ciclo, y solo por la edad del latido la
    fábrica habría esperado hasta 35 min para retomar."""
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    import ctypes

    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    try:
        codigo = ctypes.c_ulong()
        return bool(k.GetExitCodeProcess(h, ctypes.byref(codigo))) and codigo.value == 259  # STILL_ACTIVE
    finally:
        k.CloseHandle(h)


def tomar_latido(lote: str) -> bool:
    """True si este proceso queda a cargo del ciclo."""
    ruta = _ruta_latido(lote)
    try:
        previo = json.loads(ruta.read_text(encoding="utf-8"))
        if (time.time() - previo["t"] < LATIDO_VIEJO and previo["pid"] != os.getpid()
                and _proceso_vivo(previo["pid"])):
            return False
    except (OSError, ValueError, KeyError):
        pass
    ruta.write_text(json.dumps({"pid": os.getpid(), "t": time.time()}), encoding="utf-8")
    return True


def _latir(lote: str, parar: threading.Event) -> None:
    while not parar.wait(60):
        _ruta_latido(lote).write_text(json.dumps({"pid": os.getpid(), "t": time.time()}),
                                      encoding="utf-8")


# ---------------------------------------------------------------------- trabajo

# La fórmula de Javier (12/10/2026), "la contradicción local": te afecta (autorreferencia)
# + está pasando ahorita (actualidad) + algo no cuadra (brecha de curiosidad) + coraje
# (indignación moral), y además que se pueda grabar o mostrar.
CONDICIONES = ("1_te_afecta", "2_esta_pasando_ahorita", "3_algo_no_cuadra", "4_coraje",
               "5_se_puede_grabar", "6_hace_hablar")


def problemas_de_preguntas(guion: dict) -> list[str]:
    """Dos preguntas directas a quien ve (14/10/2026, idea de Javier): una antes
    del segundo diez (p01 o p02) y otra a la mitad (p03 a p05). Enganchan con
    su propio caso y dejan la respuesta lista para los comentarios."""
    narr = {p.get("id"): p.get("narracion", "") for p in guion.get("planos", [])}
    out = []
    for planos, cuando in ((("p01", "p02"), "antes del segundo diez (p01 o p02)"),
                           (("p03", "p04", "p05"), "a la mitad (p03, p04 o p05)")):
        if not any(re.search(r"¿[^?]{3,}\?", narr.get(p, "")) for p in planos):
            out.append(f"falta una pregunta directa a quien ve {cuando}, sobre SU caso, con ¿…?")
    return out


# Que el video envejezca bien (14/10/2026): en la voz no va tiempo relativo,
# porque el video se ve semanas después ("ayer" deja de ser verdad). "Mañana"
# no entra: casi siempre es "esa mañana".
_TIEMPO_RELATIVO = re.compile(
    r"\b(hoy|ayer|anoche|anteayer|esta semana|este mes|este año|la semana pasada|el mes pasado|"
    r"el año pasado|el pasado (?:lunes|martes|miércoles|jueves|viernes|sábado|domingo)|"
    r"hace (?:un|una|dos|tres|cuatro|cinco|unos|unas|pocos|pocas) (?:días|día|semanas|semana|meses|mes))\b",
    re.IGNORECASE)


def problemas_de_vigencia(guion: dict, vigencia: str | None = None, hoy: datetime | None = None) -> list[str]:
    """Las reglas de conversacion/perenne y de "que envejezca bien"."""
    from dato_mata_gato_bot import instruccion_cercania

    out = []
    for p in guion.get("planos", []):
        dichas = sorted({m.group(0).lower() for m in _TIEMPO_RELATIVO.finditer(p.get("narracion", ""))})
        if dichas:
            out.append(f"{p.get('id')}: la voz dice {', '.join(repr(d) for d in dichas)}; el video se ve "
                       "semanas después: di la fecha o el año, o \"sigue\"")
    schema = guion.get("_schema") or {}
    escrita = str(schema.get("vigencia", "")).strip().lower()
    if vigencia and escrita != vigencia:
        out.append(f'_schema.vigencia tiene que ser "{vigencia}" (dice "{escrita or "nada"}")')
    if (vigencia or escrita) == "conversacion":
        if not str(schema.get("impacto", "")).strip():
            out.append('falta "_schema.impacto": de dónde sale que la gente está hablando de esto '
                       "(lo más leído, comentarios, varios medios)")
        texto = str((schema.get("condiciones") or {}).get("2_esta_pasando_ahorita", ""))
        fechas = []
        for d, m, a in re.findall(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", texto):
            try:
                fechas.append(datetime(int(a), int(m), int(d)))
            except ValueError:
                pass
        limite = (hoy or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0) \
            - timedelta(days=instruccion_cercania.DIAS_NOTICIA)
        if not fechas:
            out.append("en _schema.condiciones.2_esta_pasando_ahorita falta la fecha de la nota (DD/MM/AAAA)")
        elif max(fechas) < limite:
            out.append(f"el dato es del {max(fechas):%d/%m/%Y}: tiene que ser del {limite:%d/%m/%Y} o "
                       "más nueva. Busca otra de los últimos dos días")
    return out


def problemas_cercania(slug: str, vigencia: str | None = None) -> list[str]:
    """Revisión sin Claude de un guion de cercanía: lugar exacto y evidencia
    real (las reglas de revision_guion, sin el mínimo de 3 nombres del true
    crime), las CUATRO condiciones de la fórmula escritas en el guion y, desde
    el 14/10/2026, las reglas de conversacion/perenne y de que envejezca bien."""
    from dato_mata_gato_bot import revision_guion

    try:
        guion = json.loads((pipeline.ANDROID_IN / slug / "guion.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ["no se pudo leer el guion.json"]
    out = revision_guion.problemas(guion, min_nombres=0)
    condiciones = (guion.get("_schema") or {}).get("condiciones") or {}
    faltan = [c for c in CONDICIONES if not str(condiciones.get(c, "")).strip()]
    if faltan:
        out.append("no explica cómo cumple estas piezas de la fórmula en _schema.condiciones: "
                   + ", ".join(faltan) + ". Si le falta una, cambia el tema por otro que las tenga todas")
    return (out + problemas_de_vigencia(guion, vigencia) + problemas_de_preguntas(guion)
            + problemas_de_publicacion(guion) + problemas_de_registro(guion))


# Español de España y giros de traducción (20/10/2026: Javier oía los guiones
# "en español neutro o de España"). Solo lo que en México casi nunca se dice:
# "vale" cuenta como muletilla ("vale," / "¡vale!"), no en "vale la pena".
_DE_ESPANA = re.compile(
    r"\b(vosotr[oa]s|vuestr[oa]s?|ordenador(es)?|m[oó]vil(es)?|guay|mola|chaval(es)?|zumos?|"
    r"aparcar|aparcamiento|coger|cog[ií]|gilipollas|flipar|los llegados|las llegadas)\b"
    # "veintiséis" y "dieciséis" no son vosotros: el falso positivo forzó una
    # reescritura completa en 4 de 8 guiones del 27-28/10/2026.
    r"|¡vale!|\bvale[,.]\s|\b(?!(?:veinti|dieci)s[eé]is\b)\w+(áis|éis)\b", re.IGNORECASE)


# Preguntas de opción (21/10/2026): con la voz mexicana, "¿A o B?" y "¿O …?"
# bajan el tono al final (-5.9 semitonos medido) y no suenan a pregunta; las
# de sí o no suben (+2.5 a +5.3).
_PREGUNTA_DE_OPCION = re.compile(r"¿(?:[^?¿]*\s)?o\s[^?¿]*\?", re.IGNORECASE)


def problemas_de_registro(guion: dict) -> list[str]:
    """Que la voz hable como en México, no como en España ni como un doblaje,
    y que sus preguntas suenen a pregunta."""
    out = []
    for p in guion.get("planos", []):
        texto = p.get("narracion", "")
        dichas = sorted({m.group(0).strip(" ,.").lower() for m in _DE_ESPANA.finditer(texto)})
        if dichas:
            out.append(f"{p.get('id')}: la voz dice {', '.join(repr(d) for d in dichas)}, que suena a "
                       "España o a traducción; dilo como se dice en México")
        for m in _PREGUNTA_DE_OPCION.finditer(texto):
            out.append(f'{p.get("id")}: "{m.group(0)}" es pregunta de opción y la voz la lee sin '
                       'tono de pregunta; pártela en dos de sí o no ("¿Fue X? ¿Tú crees que fue Y?")')
    return out


GENERICOS = {"#fyp", "#foryou", "#parati", "#viral", "#foryoupage", "#tiktok"}


def problemas_de_publicacion(guion: dict) -> list[str]:
    """Descripción y hashtags para el buscador de TikTok (20/10/2026)."""
    out = []
    if len(str(guion.get("descripcion", "")).split()) < 12:
        out.append('falta "descripcion": 2 o 3 frases con lo que la gente buscaría y la pregunta del p08')
    etiquetas = [str(h).strip().lower() for h in guion.get("hashtags", []) if str(h).strip()]
    utiles = [h for h in etiquetas if h.lstrip("#") not in {g.lstrip("#") for g in GENERICOS}]
    if len(utiles) < 4:
        out.append(f"lleva {len(utiles)} hashtags útiles y van de 4 a 5 (lugar, tema, institución, "
                   "nicho y #DatoMataGato; sin #fyp ni #viral)")
    return out


def sesion_ligera() -> bool:
    """FABRICA_SESION_LIGERA (default 1): escribir en la sesión ligera de
    claude_runner con las herramientas locales (13/10/2026). 0 = como antes."""
    return (os.getenv("FABRICA_SESION_LIGERA") or "1").strip() != "0"


# Vueltas extra en la MISMA sesión (20/10/2026): corregir lo que no pasa,
# completar lo que falta o seguir tras un corte de conexión. La sesión ya tiene
# el tema investigado; empezar otra cuesta toda la investigación de nuevo.
MAX_RONDAS = int(os.getenv("FABRICA_RONDAS") or 2)


def _guiones_en_disco(prefijo: str, desde: float) -> list[str]:
    """Slugs con un guion.json escrito desde `desde`. El 20/10/2026 una sesión
    escribió un guion que pasaba la revisión, se cortó la API antes de
    responder, y se tiró: el trabajo estaba en disco y nadie lo miró."""
    slugs = []
    for ruta in pipeline.ANDROID_IN.glob(f"{prefijo}*/guion.json"):
        try:
            if ruta.stat().st_mtime >= desde:
                slugs.append(ruta.parent.name)
        except OSError:
            continue
    return sorted(slugs)


async def _escribir_y_rescatar(avisador, nombre: str, texto: str, cantidad: int, prefijo: str,
                               revisar, ligera: bool) -> tuple[list[dict], list[str]]:
    """Escribe en una sesión y no tira trabajo (20/10/2026):
    - toma lo que Claude respondió Y lo que dejó en disco (el JSON de la
      respuesta se puede perder en un corte; el guion.json no);
    - si la API se corta, retoma la misma sesión en vez de darla por perdida;
    - si un guion no pasa, o entregó menos de los pedidos (el 20/10 entregó 1
      de 2 y terminó preguntando "dime cuál y lo escribo", sin nadie que
      contestara), se lo pide en la misma sesión, hasta MAX_RONDAS veces.
    Si se acaba la cuota, LimiteDeClaude lleva en `.slugs` lo que sí pasó.
    Devuelve (guiones buenos, sesiones usadas)."""
    from dato_mata_gato_bot import bot
    from dato_mata_gato_bot.claude_runner import es_limite_de_uso, run_turn

    session_id, _ = bot._sesion_nueva()
    desde = time.time() - 5
    r = await asyncio.to_thread(run_turn, session_id, texto, True, ligera)
    slugs: list[str] = []
    buenos: list[str] = []
    fallas: dict[str, list[str]] = {}
    for ronda in range(MAX_RONDAS + 1):
        respondidos = [g["slug"] for g in (bot._parse_lote_response(r.text) or []) if g.get("slug")] if r.ok else []
        for s in respondidos + _guiones_en_disco(prefijo, desde):
            if s not in slugs:
                slugs.append(s)
        revision = {s: revisar(s) for s in slugs}
        buenos = [s for s, p in revision.items() if not p]
        fallas = {s: p for s, p in revision.items() if p}
        if not r.ok and es_limite_de_uso(r.text):
            exc = bot.LimiteDeClaude(r.text)
            exc.slugs = buenos
            raise exc
        sin_tema = cantidad - len(buenos) - len(fallas)
        if (r.ok and not fallas and sin_tema <= 0) or ronda == MAX_RONDAS:
            break
        partes = []
        if not r.ok:
            logger.warning("%s: la sesión %s se cortó (%s); la retomo", nombre, session_id, r.text[:200])
            partes.append("Se cortó la conexión a media respuesta. Sigue donde ibas: lo que ya "
                          "escribiste en disco está a salvo y ya lo revisé.")
        if fallas:
            partes.append("Estos guiones no pasan la revisión. Corrígelos en su guion.json (mismo "
                          "slug); si el tema no tiene arreglo, cámbialo por otro, con otro slug:\n"
                          + "\n".join(f"- {s}: " + "; ".join(p) for s, p in fallas.items()))
        if sin_tema > 0:
            partes.append(f"Faltan {sin_tema} guion(es) de los {cantidad} pedidos. Si ya tienes un "
                          "tema de reemplazo investigado, escríbelo; si no, busca otro que cumpla. "
                          "No preguntes ni ofrezcas opciones: nadie va a contestar. Decide tú.")
        partes.append("Responde con el bloque JSON de TODOS los guiones.")
        r = await asyncio.to_thread(run_turn, session_id, "\n\n".join(partes), False, ligera)
    if fallas:
        await avisador.message.reply_text(
            f"⚠️ {nombre}: {len(fallas)} guion(es) quedan fuera porque no cumplen la fórmula:\n"
            + "\n".join(f"- {s}: " + "; ".join(p) for s, p in fallas.items()))
    if not r.ok and not buenos:
        await avisador.message.reply_text(f"Falló {nombre}: {r.text[:800]}")
    return [{"slug": s} for s in buenos], [session_id]


async def _guiones_de_cercania(avisador, clave: str, cantidad: int, ligera: bool | None = None,
                               vigencia: str | None = None) -> tuple[list[dict], list[str]]:
    """Un tema de la fórmula de cercanía (ver `_escribir_y_rescatar`)."""
    from dato_mata_gato_bot import bot, instruccion_cercania

    ligera = sesion_ligera() if ligera is None else ligera
    ya = bot._ya_cubiertos("guion")
    texto = instruccion_cercania.instruccion(clave, cantidad, ya, ligera=ligera, vigencia=vigencia)
    texto = await asyncio.to_thread(expediente.agregar, texto, clave, None, cantidad, ya,
                                    2 if vigencia != "perenne" else instruccion_cercania.DIAS_NOTICIA,
                                    telegram)
    buenos, sesiones = await _escribir_y_rescatar(
        avisador, f"el tema {clave}", texto, cantidad, f"guion-{clave}-",
        lambda s: problemas_cercania(s, vigencia), ligera)
    for g in buenos:
        g["vigencia"] = vigencia or ""
    return buenos, sesiones


def problemas_viral(slug: str) -> list[str]:
    """Revisión sin Claude de un guion de tema viral: todo lo de cercanía más lo
    propio de los tres niveles (candado, pieza 8, documento, sin_nota_animada)."""
    from dato_mata_gato_bot import instruccion_viral

    out = problemas_cercania(slug, vigencia="conversacion")
    if out == ["no se pudo leer el guion.json"]:
        return out
    try:
        guion = json.loads((pipeline.ANDROID_IN / slug / "guion.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ["no se pudo leer el guion.json"]
    return out + instruccion_viral.problemas(guion)


async def _guiones_virales(avisador, tema: str | None, cantidad: int,
                           ligera: bool | None = None) -> tuple[list[dict], list[str]]:
    """Un lote de temas virales. Sin `tema`, Claude busca primero de qué se está
    hablando (ver `_escribir_y_rescatar`)."""
    from dato_mata_gato_bot import bot, instruccion_viral

    ligera = sesion_ligera() if ligera is None else ligera
    ya = bot._ya_cubiertos("guion")
    texto = instruccion_viral.instruccion(cantidad, tema, ya, ligera=ligera)
    texto = await asyncio.to_thread(expediente.agregar, texto, "viral", tema, cantidad, ya, 2, telegram)
    buenos, sesiones = await _escribir_y_rescatar(
        avisador, "el tema viral", texto, cantidad, "guion-viral-", problemas_viral, ligera)
    for g in buenos:
        g["vigencia"] = "conversacion"
    return buenos, sesiones


def problemas_polemica(slug: str) -> list[str]:
    """Revisión sin Claude de un guion de polémica: todo lo de cercanía más lo
    propio de esta fórmula (la frase citada, la reacción medida, la prueba del
    ofensor, el veredicto del público)."""
    from dato_mata_gato_bot import instruccion_polemica

    out = problemas_cercania(slug, vigencia="conversacion")
    if out == ["no se pudo leer el guion.json"]:
        return out
    try:
        guion = json.loads((pipeline.ANDROID_IN / slug / "guion.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ["no se pudo leer el guion.json"]
    return out + instruccion_polemica.problemas(guion)


async def _guiones_de_polemica(avisador, tema: str | None, cantidad: int,
                               ligera: bool | None = None) -> tuple[list[dict], list[str]]:
    """Un lote de polémicas (17/10/2026; ver `_escribir_y_rescatar`)."""
    from dato_mata_gato_bot import bot, instruccion_polemica

    ligera = sesion_ligera() if ligera is None else ligera
    ya = bot._ya_cubiertos("guion")
    texto = instruccion_polemica.instruccion(cantidad, tema, ya, ligera=ligera)
    texto = await asyncio.to_thread(expediente.agregar, texto, "polemica", tema, cantidad, ya, 2, telegram)
    buenos, sesiones = await _escribir_y_rescatar(
        avisador, "la polémica", texto, cantidad, "guion-polemica-", problemas_polemica, ligera)
    for g in buenos:
        g["vigencia"] = "conversacion"
    return buenos, sesiones


def problemas_comparativa(slug: str) -> list[str]:
    """Revisión sin Claude de una comparativa (20/10/2026): lo de cercanía (tema
    perenne: la comparación es de años) más la misma vara, el veredicto, el
    balance de cada lado y la prueba del espejo."""
    from dato_mata_gato_bot import instruccion_comparativa

    out = problemas_cercania(slug, vigencia="perenne")
    if out == ["no se pudo leer el guion.json"]:
        return out
    try:
        guion = json.loads((pipeline.ANDROID_IN / slug / "guion.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ["no se pudo leer el guion.json"]
    return out + instruccion_comparativa.problemas(guion)


async def _guiones_comparativa(avisador, tema: str | None, cantidad: int,
                               ligera: bool | None = None) -> tuple[list[dict], list[str]]:
    """Un lote de comparativas: ahora contra antes, o aquí contra allá (20/10/2026)."""
    from dato_mata_gato_bot import bot, instruccion_cercania, instruccion_comparativa

    ligera = sesion_ligera() if ligera is None else ligera
    ya = bot._ya_cubiertos("guion")
    texto = instruccion_comparativa.instruccion(cantidad, tema, ya, ligera=ligera)
    # 29/10/2026: antes Claude buscaba sola el tema y las dos cifras oficiales.
    texto = await asyncio.to_thread(expediente.agregar, texto, "comparativa", tema, cantidad, ya,
                                    instruccion_cercania.DIAS_NOTICIA, telegram)
    buenos, sesiones = await _escribir_y_rescatar(
        avisador, "la comparativa", texto, cantidad, "guion-comparativa-", problemas_comparativa, ligera)
    for g in buenos:
        g["vigencia"] = "perenne"
    return buenos, sesiones


# Cómo se escribe y con qué vigencia queda cada fórmula de redes.
FORMULAS_REDES = {"polemica": ("_guiones_de_polemica", "conversacion"),
                  "viral": ("_guiones_virales", "conversacion"),
                  "comparativa": ("_guiones_comparativa", "perenne")}


def en_sesiones(cantidad: int) -> list[int]:
    """Reparte `cantidad` guiones en sesiones de Claude de a lo más
    FABRICA_GUIONES_POR_SESION (default 2). Medido el 20/10/2026: con 5 por
    sesión el contexto crecía de 23k a 350k y cada paso lo releía; con uno por
    sesión se releía 61 % menos. Dos conserva la investigación compartida del
    tema. Cada sesión ve en la lista de "ya hechos" lo que escribió la anterior."""
    try:
        tope = max(1, int(os.getenv("FABRICA_GUIONES_POR_SESION") or 2))
    except ValueError:
        tope = 2
    partes = []
    while cantidad > 0:
        partes.append(min(tope, cantidad))
        cantidad -= partes[-1]
    return partes


# /lotegrande (20/10/2026, teoría de Javier): la mayoría polémica y el resto
# tema viral, porque el viral trae gente nueva (el de Vicky Wolff); y UNA de
# cada cinco es comparativa (ahora contra antes). 12:8:5 = 20 % comparativa, y
# el 80 % restante sigue 3:2 polémica contra viral.
MEZCLA_REDES = {"polemica": 12, "viral": 8, "comparativa": 5}


def repartir_redes(n: int, hechos: dict[str, int] | None = None) -> list[tuple[str, int]]:
    """n guiones repartidos según MEZCLA_REDES sobre lo que ya hay (como
    `repartir_vigencias`): cada uno va a la fórmula que más se atrasó."""
    hechos = hechos or {}
    pedidos = {f: 0 for f in MEZCLA_REDES}
    peso = sum(MEZCLA_REDES.values())
    for _ in range(n):
        total = sum(hechos.get(f, 0) for f in MEZCLA_REDES) + sum(pedidos.values()) + 1
        f = max(MEZCLA_REDES, key=lambda x: MEZCLA_REDES[x] * total / peso - hechos.get(x, 0) - pedidos[x])
        pedidos[f] += 1
    return [(f, k) for f, k in pedidos.items() if k]


ESPERA_IA_GRATIS_MIN = int(os.getenv("FABRICA_ESPERA_IA_GRATIS_MIN") or 60)


def esperando_ia_gratis(estado: dict, ahora: datetime) -> bool:
    """Se acabó la cuota gratis y Javier no dijo /iaclaude: no se escriben
    guiones (los videos siguen) hasta que pase ESPERA_IA_GRATIS_MIN y se
    vuelva a probar. Con /iaclaude nunca espera."""
    agotada = estado.get("ia_gratis_agotada")
    if not agotada or estado.get("sin_ia_gratis") == "claude":
        return False
    return ahora < datetime.fromisoformat(agotada) + timedelta(minutes=ESPERA_IA_GRATIS_MIN)


def escribir_tanda(estado: dict) -> tuple[list[str], str | None]:
    """Pide a Claude la siguiente tanda. Devuelve (slugs nuevos, aviso de cuota
    agotada o None).

    Formato "cercania" (el de los 1000, 12/10/2026): la fórmula de Cancún
    repartida entre los temas de instruccion_cercania.TEMAS. Formato "crimen":
    el reparto e instrucción de /lotefish3.

    Si la cuota se acaba a mitad, lo que ya se escribió en esta tanda se
    devuelve igual: esos guion.json ya están en disco y no se pueden perder.
    """
    from dato_mata_gato_bot import bot, instruccion_cercania  # import tardío: trae Telegram y Claude

    faltan = estado["objetivo"] - len(estado["videos"])
    cuantos = min(int(estado.get("por_tanda", POR_TANDA)), faltan)
    nuevos: list[str] = []
    sesiones = estado.setdefault("_sesiones_tanda", [])
    sesiones.clear()
    vigencias = estado.setdefault("_vigencias", {})
    def cortada(exc, vig: str) -> tuple[list[str], str]:
        # Lo que ya pasó la revisión antes de que se acabara la cuota entra igual.
        for s in getattr(exc, "slugs", []):
            nuevos.append(s)
            vigencias[s] = vig
        return nuevos, str(exc)

    # 27/10/2026, Javier: si la IA gratis se queda sin cuota, preguntar antes de
    # que Claude investigue solo (gasta 2-3 M tokens por guion).
    expediente.SI_SE_ACABA = "claude" if estado.get("sin_ia_gratis") == "claude" else "preguntar"

    def sin_cuota_gratis(exc) -> tuple[list[str], None]:
        estado["ia_gratis_agotada"] = datetime.now().isoformat(timespec="minutes")
        if estado.get("sin_ia_gratis") != "esperar" and not estado.get("ia_gratis_preguntado"):
            estado["ia_gratis_preguntado"] = True
            telegram(f"🆓⛔ Fábrica {estado['lote']}: se acabó la cuota de las IA gratis que investigan "
                     f"los temas ({str(exc)[:120]}).\n"
                     "¿Sigo con Claude investigando? Gasta ~2-3 M tokens por guion en vez de ~0.5 M.\n"
                     "/iaclaude = sí, que siga Claude\n"
                     f"/iaesperar = no, espero a que se renueve (reintento cada {ESPERA_IA_GRATIS_MIN} min).\n"
                     "Mientras, sigo generando los videos de los guiones que ya hay.")
        return nuevos, None

    if estado.get("formato") in ("redes", *FORMULAS_REDES):
        # Tema viral (15/10/2026) y polémica (17/10/2026); el tema puede venir
        # vacío, y entonces Claude busca primero de qué se está hablando. Se
        # eligen por la prueba del papel: si existe un documento que cerraría la
        # discusión, es "viral"; si lo que detonó todo es una opinión, "polemica".
        # "redes" (20/10/2026): la mayoría polémica y el resto viral, sobre lo
        # que el lote YA tiene (un guion descartado no cuenta).
        if estado["formato"] == "redes":
            hechos = {f: sum(s.startswith(f"guion-{f}-") for s in estado["videos"]) for f in MEZCLA_REDES}
            plan = repartir_redes(cuantos, hechos)
        else:
            plan = [(estado["formato"], cuantos)]
        # Polémica y viral sin tema solo se escriben con temas que el expediente ya
        # filtró (últimos 3 días, sin repetir); si no hay, esa fórmula espera
        # ESPERA_IA_GRATIS_MIN y Claude no sale a buscar (Javier, 29/10/2026).
        sin_frescos = estado.setdefault("sin_temas_frescos", {})
        for formato, total in plan:
            if (cuando := sin_frescos.get(formato)) and \
                    datetime.now() < datetime.fromisoformat(cuando) + timedelta(minutes=ESPERA_IA_GRATIS_MIN):
                continue
            funcion, vig = FORMULAS_REDES[formato]
            escribir = globals()[funcion]
            for cant in en_sesiones(total):
                try:
                    guiones, usadas = asyncio.run(escribir(_Avisador(), estado.get("tema") or None, cant))
                except bot.LimiteDeClaude as exc:
                    return cortada(exc, vig)
                except expediente.SinCuotaGratis as exc:
                    return sin_cuota_gratis(exc)
                except expediente.SinTemasFrescos as exc:
                    sin_frescos[formato] = datetime.now().isoformat(timespec="minutes")
                    telegram(f"🗓️ Fábrica {estado['lote']}: {formato} sin temas nuevos ({str(exc)[:300]}). "
                             f"Claude no busca por su cuenta; reintento en {ESPERA_IA_GRATIS_MIN} min.")
                    break
                sin_frescos.pop(formato, None)
                sesiones += usadas
                for g in guiones:
                    if g.get("slug"):
                        nuevos.append(g["slug"])
                        vigencias[g["slug"]] = vig
                estado["guiones_pedidos"] += cant
        return nuevos, None
    if estado.get("formato", "cercania") == "cercania":
        conteo: dict[str, int] = {}
        for slug in estado["videos"]:
            if (t := instruccion_cercania.tema_de(slug)):
                conteo[t] = conteo.get(t, 0) + 1
        temas = ([(estado["tema"], cuantos)] if estado.get("tema")
                 else instruccion_cercania.repartir(cuantos, conteo))
        if estado.get("vigencias"):
            # Mezcla conversación/perenne (3:2) sobre lo que ya lleva el lote.
            ya: dict = {}
            for v in estado["videos"].values():
                ya[v.get("vigencia")] = ya.get(v.get("vigencia"), 0) + 1
            lista_v = [v for v, k in instruccion_cercania.repartir_vigencias(cuantos, ya) for _ in range(k)]
        else:
            lista_v = [None] * cuantos
        lista_t = [c for c, k in temas for _ in range(k)]
        grupos: dict[tuple, int] = {}
        for par in zip(lista_t, lista_v):
            grupos[par] = grupos.get(par, 0) + 1
        for (clave, vig), total in grupos.items():
            for cant in en_sesiones(total):
                try:
                    guiones, usadas = asyncio.run(_guiones_de_cercania(_Avisador(), clave, cant, vigencia=vig))
                except bot.LimiteDeClaude as exc:
                    return cortada(exc, vig or "")
                except expediente.SinCuotaGratis as exc:
                    return sin_cuota_gratis(exc)
                sesiones += usadas
                for g in guiones:
                    if g.get("slug"):
                        nuevos.append(g["slug"])
                        vigencias[g["slug"]] = vig or ""
                estado["guiones_pedidos"] += cant
        return nuevos, None
    for tipo, desc, cant in formatos.repartir_fish3(cuantos):
        session_id, is_new = bot._sesion_nueva()
        sesiones.append(session_id)
        try:
            guiones = asyncio.run(bot._guiones_de_crimen(_Avisador(), session_id, is_new, cant,
                                                         desc, formato=tipo))
        except bot.LimiteDeClaude as exc:
            return nuevos, str(exc)
        nuevos += [g["slug"] for g in guiones if g.get("slug")]
    estado["guiones_pedidos"] += cuantos
    return nuevos, None


def tokens_de_sesiones(ids: list[str]) -> dict:
    """Lo que gastaron estas conversaciones de Claude, leído de su historial.

    Medido el 12/10/2026 sobre los lotes del bot: ~4.3 M tokens por guion, 85%
    relectura de caché. Los cortes por límite no salen de un total fijo (entre
    12 M y 210 M en las 5 h previas): pesa más escribir caché y la salida que
    releer. Por eso se guarda el desglose y no solo el total.

    Corregido el 13/10/2026: una respuesta de Claude queda en VARIAS líneas del
    historial (una por bloque: texto, cada herramienta), todas con el mismo id
    y el mismo `usage`. Sumar línea por línea contaba ~3 veces de más: el
    "4.3 M por guion" eran ~1.6 M reales.
    """
    from dato_mata_gato_bot import claude_runner

    carpetas = [claude_runner.carpeta_de_sesiones(claude_runner.CWD),
                claude_runner.carpeta_de_sesiones(claude_runner.CWD_LIGERO)]
    tot = {"entrada": 0, "lectura_cache": 0, "escritura_cache": 0, "salida": 0}
    for sid in ids:
        ruta = next((c / f"{sid}.jsonl" for c in carpetas if (c / f"{sid}.jsonl").exists()), None)
        if ruta is None:
            continue
        vistos = set()
        for linea in ruta.open(encoding="utf-8", errors="replace"):
            try:
                d = json.loads(linea)
            except ValueError:
                continue
            m = d.get("message") or {}
            u = m.get("usage") if d.get("type") == "assistant" else None
            if u and m.get("id") in vistos:
                continue
            vistos.add(m.get("id"))
            if u:
                tot["entrada"] += u.get("input_tokens", 0)
                tot["lectura_cache"] += u.get("cache_read_input_tokens", 0)
                tot["escritura_cache"] += u.get("cache_creation_input_tokens", 0)
                tot["salida"] += u.get("output_tokens", 0)
    tot["total"] = sum(tot.values())
    return tot


def puede_usar_claude(estado: dict, ahora: datetime) -> str | None:
    """None si se puede pedir una tanda ahora; si no, por qué no.

    Para no comerse la cuota que Javier usa en sus propias sesiones:
    - FABRICA_TANDAS_5H (default 1): cuántas tandas por cada 5 horas.
    - FABRICA_HORAS_CLAUDE (p. ej. "0-9"): solo escribe guiones en esas horas.
    """
    # Una fábrica puede traer su propio horario ("" = sin horario): el piloto
    # del 12/10/2026 se dejó sin él para terminar ese día.
    horas = (estado["horas_claude"] if "horas_claude" in estado
             else os.getenv("FABRICA_HORAS_CLAUDE") or "").strip()
    if horas:
        ini, fin = (int(x) for x in horas.split("-"))
        dentro = ini <= ahora.hour < fin if ini < fin else (ahora.hour >= ini or ahora.hour < fin)
        if not dentro:
            return f"fuera del horario de Claude ({horas} h)"
    # Una tanda que cortó el límite de Claude no cuenta como la de su ventana
    # (14/10/2026): el 14/10 la de las 09:13 se cortó a las 09:42 con 4 de 6
    # guiones, la cuota volvió a las 10:30 y la fábrica igual esperó a las 14:13
    # con ~1.5 h parada sin nada que generar.
    recientes = [c for c in estado.get("consumo", [])
                 if ahora - datetime.fromisoformat(c["t"]) < timedelta(hours=5) and not c.get("cortada")]
    if estado.get("guiones_5h"):
        # De 2 en 2 (20/10/2026): escribe 2, los genera, y escribe los
        # siguientes. Lo que se limita son los guiones pedidos por ventana, no
        # las tandas (con 1 tanda de 2 por ventana no avanzaría).
        pedidos = sum(c.get("pedidos", c.get("guiones", 0)) for c in recientes)
        if pedidos >= int(estado["guiones_5h"]):
            return f"ya se pidieron {pedidos} guiones en las últimas 5 h (máximo {estado['guiones_5h']})"
        return None
    maximo = int(os.getenv("FABRICA_TANDAS_5H") or 1)
    if len(recientes) >= maximo:
        return f"ya se pidieron {len(recientes)} tanda(s) en las últimas 5 h (máximo {maximo})"
    return None


def limpiar(slug: str, liviano: Path) -> None:
    """Lo que ya no sirve una vez archivado el video (medido el 12/10/2026: un
    video ocupaba ~220 MB entre carpetas; 1000 no cabían con margen en C:).
    Quedan el video en la carpeta del lote, el guion, la evidencia y los audios
    de la voz. Los clips y la copia del final del narrador se rehacen si hiciera
    falta regenerarlo."""
    import shutil

    proyecto = pipeline.NARRATOR_PROJECTS / slug
    shutil.rmtree(proyecto / "clips", ignore_errors=True)
    (proyecto / "final.mp4").unlink(missing_ok=True)
    (proyecto / "final_ffmpeg.mp4").unlink(missing_ok=True)  # respaldo del render con Remotion
    liviano.unlink(missing_ok=True)


def disco_libre_gb() -> float:
    import shutil

    return shutil.disk_usage(pipeline.ANDROID_IN).free / 1024 ** 3


def _correr_video(lote: str, slug: str) -> tuple[bool, str]:
    """Un video en su propio proceso: si se cuelga, se mata sin tumbar la fábrica."""
    try:
        proc = subprocess.run([str(BOT_PY), "-m", "dato_mata_gato_bot.fabrica", "video", lote, slug],
                              capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=TIMEOUT_VIDEO,
                              creationflags=_SIN_VENTANA)
    except subprocess.TimeoutExpired:
        return False, f"se colgó más de {TIMEOUT_VIDEO // 3600} h"
    linea = next((ln for ln in reversed(proc.stdout.splitlines()) if ln.startswith("RESULTADO ")), "")
    if not linea:
        return False, (proc.stderr or proc.stdout)[-800:] or f"salió con código {proc.returncode}"
    r = json.loads(linea[len("RESULTADO "):])
    return r["ok"], r["mensaje"]


def para_publicar(slug: str) -> str:
    """El título y los hashtags del guion, listos para copiar al subir el video
    (Javier, 16/10/2026). Sin esto había que abrir el guion.json a mano para
    saber con qué nombre y con qué etiquetas publicarlo."""
    try:
        guion = json.loads((pipeline.ANDROID_IN / slug / "guion.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    lineas = []
    if titulo := str(guion.get("titulo", "")).strip():
        lineas.append(f"📝 {titulo}")
    etiquetas = [h if str(h).startswith("#") else f"#{h}"
                 for h in guion.get("hashtags", []) if str(h).strip()]
    # Descripción con lo que la gente busca (20/10/2026): el buscador de TikTok
    # lee la descripción; antes solo había título y 3-4 hashtags.
    if descripcion := str(guion.get("descripcion", "")).strip():
        lineas.append("✍️ " + descripcion + (" " + " ".join(etiquetas) if etiquetas else ""))
    elif etiquetas:
        lineas.append("🏷️ " + " ".join(etiquetas))
    if lineas:
        lineas.append(CHECKLIST_PUBLICAR)
    return "\n".join(lineas)


CHECKLIST_PUBLICAR = (
    "☑️ Sube el mp4 de C:\\Android_in\\lotes (no el de Telegram) · alta calidad ON · público · "
    "dúos y stitch ON · revisión de derechos ON · etiqueta de IA si TikTok la pide · "
    "contesta comentarios la primera hora")


def video(lote: str, slug: str) -> None:
    """Lo que corre el proceso hijo: el pipeline de siempre + aviso con el video."""
    estado = leer(lote)
    carpeta = Path(estado["carpeta_videos"])
    inicio = time.time()
    r = pipeline.run(slug, "am_adam", destino_local=carpeta)
    if r.ok:
        final = pipeline.NARRATOR_PROJECTS / slug / "final.mp4"
        liviano = carpeta / f"{slug}_telegram.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(final), "-vf", "scale=-2:1280",
                        "-c:v", "libx264", "-crf", "28", "-c:a", "aac", "-b:a", "128k",
                        "-movflags", "+faststart", str(liviano)], check=False, creationflags=_SIN_VENTANA)
        vig = estado["videos"].get(slug, {}).get("vigencia", "")
        etiqueta = {"conversacion": "💬 CONVERSACIÓN: publícala primero", "perenne": "🌲 PERENNE"}.get(vig, "")
        publicar = para_publicar(slug)
        telegram(f"🎬 {slug} ({(time.time() - inicio) / 60:.0f} min)" + (f"\n{etiqueta}" if etiqueta else "")
                 + (f"\n\n{publicar}" if publicar else "")
                 + f"\n\n{r.mensaje[-700:]}", liviano if liviano.exists() else None)
        # La portada (estilo A, la nota) para subirla al publicar; ya va en el primer cuadro.
        proyecto = pipeline.NARRATOR_PROJECTS / slug
        pegada = pipeline.variante_portada(slug)
        telegram_fotos([(proyecto / f"portada_{v}.jpg",
                         "Portada"
                         + (" (ya va en el primer cuadro)" if v == pegada else "")) for v in ("nota", "dato")])
        limpiar(slug, liviano)
    print("RESULTADO " + json.dumps({"ok": r.ok, "mensaje": r.mensaje[-1500:]}, ensure_ascii=False),
          flush=True)


def ciclo(lote: str) -> str:
    """Trabaja hasta terminar, quedarse sin nada que hacer, o toparse con un
    problema de infraestructura. Devuelve por qué paró."""
    if not tomar_latido(lote):
        return "ya hay un ciclo corriendo"
    parar = threading.Event()
    threading.Thread(target=_latir, args=(lote, parar), daemon=True).start()
    try:
        return _ciclo(lote)
    finally:
        parar.set()
        _ruta_latido(lote).unlink(missing_ok=True)


def _ciclo(lote: str) -> str:
    while True:
        estado = leer(lote)
        if estado["terminado"]:
            return "terminado"
        problema = asegurar_infra()
        if not problema and disco_libre_gb() < DISCO_MINIMO_GB:
            problema = (f"quedan {disco_libre_gb():.0f} GB libres en el disco (mínimo "
                        f"{DISCO_MINIMO_GB}). Libera espacio o mueve videos ya publicados.")
        if problema:
            if time.time() - estado["ultimo_aviso_infra"] > AVISO_INFRA_CADA:
                telegram(f"⚠️ Fábrica {lote} en pausa: {problema}\nLo reintento cada 15 minutos.")
                estado["ultimo_aviso_infra"] = time.time()
                guardar(lote, estado)
            return problema

        fila = pendientes(estado)
        cuota_libre = (estado["cuota_libre_desde"] is None
                       or datetime.now() >= datetime.fromisoformat(estado["cuota_libre_desde"]))
        freno = puede_usar_claude(estado, datetime.now())
        if (len(fila) < int(estado.get("colchon", COLCHON)) and len(estado["videos"]) < estado["objetivo"]
                and cuota_libre and not freno and not esperando_ia_gratis(estado, datetime.now())):
            inicio_tanda = datetime.now()
            antes = estado["guiones_pedidos"]
            nuevos, limite = escribir_tanda(estado)
            gasto = tokens_de_sesiones(estado.pop("_sesiones_tanda", []))
            estado.setdefault("consumo", []).append(
                {"t": inicio_tanda.isoformat(timespec="minutes"), "guiones": len(nuevos),
                 "pedidos": estado["guiones_pedidos"] - antes, **gasto,
                 **({"cortada": True} if limite else {})})
            estado["cuota_libre_desde"] = None
            if limite:
                libre = hora_de_reset(limite, datetime.now())
                estado["cuota_libre_desde"] = libre.isoformat(timespec="minutes")
                telegram(f"⏸️ Fábrica {lote}: se acabó la cuota de Claude. Sigo renderizando "
                         f"lo que hay y retomo los guiones a las {libre:%H:%M}.")
            vigencias = estado.pop("_vigencias", {})
            for s in nuevos:
                estado["videos"].setdefault(s, {"estado": "pendiente", "intentos": 0, "error": "",
                                                "vigencia": vigencias.get(s, "")})
            if nuevos:
                plan = lote_grande.Plan(carpeta=Path(estado["carpeta_videos"]),
                                        tareas=[(s, None) for s in nuevos])
                lote_grande.repartir_voces(plan)
                telegram(f"📝 Fábrica {lote}: {len(nuevos)} guiones nuevos "
                         f"({gasto['total'] / 1e6:.0f} M tokens de Claude).\n{resumen(estado)}")
            guardar(lote, estado)
            if detenida(lote):
                return "detenida mientras se escribían los guiones"
            fila = pendientes(estado)

        if not fila:
            if len(estado["videos"]) >= estado["objetivo"]:
                estado["terminado"] = True
                guardar(lote, estado)
                telegram(f"✅ Fábrica {lote} terminada.\n{resumen(estado)}")
                return "terminado"
            return freno or "esperando la cuota de Claude para escribir más guiones"

        slug = fila[0]
        if detenida(lote):  # pudo entrar el /pararfabrica mientras se escribía
            return "detenida"
        ok, mensaje = _correr_video(lote, slug)
        estado = leer(lote)
        v = estado["videos"][slug]
        v["intentos"] += 1
        v["estado"] = "listo" if ok else "fallido"
        v["error"] = "" if ok else mensaje[-500:]
        guardar(lote, estado)
        if not ok:
            otra = "lo reintento al final de la fila" if v["intentos"] < MAX_INTENTOS else "queda fuera"
            telegram(f"⚠️ {slug} falló ({otra}):\n{mensaje[-500:]}")
        listos = sum(1 for x in estado["videos"].values() if x["estado"] == "listo")
        if ok and listos % 25 == 0:
            telegram(f"📊 {resumen(estado)}")


if __name__ == "__main__":
    # Solo para el proceso hijo de un video: `python -m dato_mata_gato_bot.fabrica video <lote> <slug>`.
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    if len(sys.argv) == 4 and sys.argv[1] == "video":
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        video(sys.argv[2], sys.argv[3])
