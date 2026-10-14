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

from dato_mata_gato_bot import formatos, lote_grande, pipeline

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
    """Escritura atómica: un corte a mitad no deja un estado.json roto."""
    ruta = ruta_estado(lote)
    tmp = ruta.with_suffix(".tmp")
    tmp.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, ruta)


def crear(lote: str, objetivo: int, formato: str = "cercania", **opciones) -> dict:
    """`opciones` (modo automático de /lotegrande, 14/10/2026): horas_claude
    ("" = todo el día, "0-9"), tema (una clave de instruccion_cercania o None =
    repartido), por_tanda, colchon y vigencias (mezcla noticia/perenne)."""
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
    # Las noticias caducan (no más de dos días): van antes que las perennes.
    nuevos.sort(key=lambda s: estado["videos"][s].get("vigencia") != "noticia")
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
               "5_se_puede_grabar")


# Que el video envejezca bien (14/10/2026): en la voz no va tiempo relativo,
# porque el video se ve semanas después ("ayer" deja de ser verdad). "Mañana"
# no entra: casi siempre es "esa mañana".
_TIEMPO_RELATIVO = re.compile(
    r"\b(hoy|ayer|anoche|anteayer|esta semana|este mes|este año|la semana pasada|el mes pasado|"
    r"el año pasado|el pasado (?:lunes|martes|miércoles|jueves|viernes|sábado|domingo)|"
    r"hace (?:un|una|dos|tres|cuatro|cinco|unos|unas|pocos|pocas) (?:días|día|semanas|semana|meses|mes))\b",
    re.IGNORECASE)


def problemas_de_vigencia(guion: dict, vigencia: str | None = None, hoy: datetime | None = None) -> list[str]:
    """Las reglas de noticia/perenne y de "que envejezca bien"."""
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
    if (vigencia or escrita) == "noticia":
        if not str(schema.get("impacto", "")).strip():
            out.append('falta "_schema.impacto": de dónde sale que la noticia movió al público '
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
            out.append(f"la noticia es del {max(fechas):%d/%m/%Y}: tiene que ser del {limite:%d/%m/%Y} o "
                       "más nueva. Busca otra de los últimos dos días")
    return out


def problemas_cercania(slug: str, vigencia: str | None = None) -> list[str]:
    """Revisión sin Claude de un guion de cercanía: lugar exacto y evidencia
    real (las reglas de revision_guion, sin el mínimo de 3 nombres del true
    crime), las CUATRO condiciones de la fórmula escritas en el guion y, desde
    el 14/10/2026, las reglas de noticia/perenne y de que envejezca bien."""
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
    return out + problemas_de_vigencia(guion, vigencia)


def sesion_ligera() -> bool:
    """FABRICA_SESION_LIGERA (default 1): escribir en la sesión ligera de
    claude_runner con las herramientas locales (13/10/2026). 0 = como antes."""
    return (os.getenv("FABRICA_SESION_LIGERA") or "1").strip() != "0"


async def _guiones_de_cercania(avisador, clave: str, cantidad: int, ligera: bool | None = None,
                               vigencia: str | None = None) -> tuple[list[dict], list[str]]:
    """Un tema de la fórmula de cercanía: escribe, revisa, una ronda de
    corrección (en la misma conversación: ya tiene el tema investigado) y deja
    fuera lo que siga fallando. Devuelve (guiones buenos, sesiones usadas)."""
    from dato_mata_gato_bot import bot, instruccion_cercania
    from dato_mata_gato_bot.claude_runner import es_limite_de_uso, run_turn

    ligera = sesion_ligera() if ligera is None else ligera
    session_id, _ = bot._sesion_nueva()
    texto = instruccion_cercania.instruccion(clave, cantidad, bot._ya_cubiertos("guion"), ligera=ligera,
                                             vigencia=vigencia)
    r = await asyncio.to_thread(run_turn, session_id, texto, True, ligera)
    if not r.ok:
        if es_limite_de_uso(r.text):
            raise bot.LimiteDeClaude(r.text)
        await avisador.message.reply_text(f"Falló el tema {clave}: {r.text[:800]}")
        return [], [session_id]
    guiones = bot._parse_lote_response(r.text) or []
    fallas = {g["slug"]: p for g in guiones if g.get("slug") if (p := problemas_cercania(g["slug"], vigencia))}
    if fallas:
        pedido = ("Revisé los guiones y estos no cumplen la fórmula. Corrígelos en su guion.json "
                  "(mismo slug); si un tema no cumple las cuatro condiciones o no tiene evidencia, "
                  "reemplázalo por otro, con otro slug. Responde con el mismo bloque JSON, con TODOS "
                  "los guiones.\n\n" + "\n".join(f"- {s}: " + "; ".join(p) for s, p in fallas.items()))
        r2 = await asyncio.to_thread(run_turn, session_id, pedido, False, ligera)
        if r2.ok:
            guiones = bot._parse_lote_response(r2.text) or guiones
        elif es_limite_de_uso(r2.text):
            raise bot.LimiteDeClaude(r2.text)
    buenos, fuera = [], {}
    for g in guiones:
        p = problemas_cercania(g.get("slug", ""), vigencia)
        if p:
            fuera[g.get("slug", "?")] = p
        else:
            g["vigencia"] = vigencia or ""
            buenos.append(g)
    if fuera:
        await avisador.message.reply_text(
            f"⚠️ Tema {clave}: {len(fuera)} guion(es) quedan fuera porque no cumplen la fórmula:\n"
            + "\n".join(f"- {s}: " + "; ".join(p) for s, p in fuera.items()))
    return buenos, [session_id]


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
    if estado.get("formato", "cercania") == "cercania":
        conteo: dict[str, int] = {}
        for slug in estado["videos"]:
            if (t := instruccion_cercania.tema_de(slug)):
                conteo[t] = conteo.get(t, 0) + 1
        temas = ([(estado["tema"], cuantos)] if estado.get("tema")
                 else instruccion_cercania.repartir(cuantos, conteo))
        if estado.get("vigencias"):
            # Mezcla noticia/perenne (3:2) sobre lo que ya lleva el lote.
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
        for (clave, vig), cant in grupos.items():
            try:
                guiones, usadas = asyncio.run(_guiones_de_cercania(_Avisador(), clave, cant, vigencia=vig))
            except bot.LimiteDeClaude as exc:
                return nuevos, str(exc)
            sesiones += usadas
            for g in guiones:
                if g.get("slug"):
                    nuevos.append(g["slug"])
                    vigencias[g["slug"]] = vig or ""
        estado["guiones_pedidos"] += cuantos
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
    maximo = int(os.getenv("FABRICA_TANDAS_5H") or 1)
    recientes = [c for c in estado.get("consumo", [])
                 if ahora - datetime.fromisoformat(c["t"]) < timedelta(hours=5)]
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
        etiqueta = {"noticia": "📰 NOTICIA: publícala pronto, caduca", "perenne": "🌲 PERENNE"}.get(vig, "")
        telegram(f"🎬 {slug} ({(time.time() - inicio) / 60:.0f} min)" + (f"\n{etiqueta}" if etiqueta else "")
                 + f"\n{r.mensaje[-700:]}", liviano if liviano.exists() else None)
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
                and cuota_libre and not freno):
            inicio_tanda = datetime.now()
            nuevos, limite = escribir_tanda(estado)
            gasto = tokens_de_sesiones(estado.pop("_sesiones_tanda", []))
            estado.setdefault("consumo", []).append(
                {"t": inicio_tanda.isoformat(timespec="minutes"), "guiones": len(nuevos), **gasto})
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
            fila = pendientes(estado)

        if not fila:
            if len(estado["videos"]) >= estado["objetivo"]:
                estado["terminado"] = True
                guardar(lote, estado)
                telegram(f"✅ Fábrica {lote} terminada.\n{resumen(estado)}")
                return "terminado"
            return freno or "esperando la cuota de Claude para escribir más guiones"

        slug = fila[0]
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
