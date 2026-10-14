"""Estado por chat de Telegram: fase (recolectando/listo), slug del
proyecto, sesión de Claude Code asociada, y si hay una generación en
curso. Persistido en disco para sobrevivir reinicios del bot."""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
SESSIONS_PATH = DATA_DIR / "sessions.json"
STAGING_DIR = DATA_DIR / "staging"
ANDROID_IN = Path(r"C:\Android_in")

PHASE_IDLE = "idle"
PHASE_COLLECTING = "recolectando"

DEFAULT_VOICE = "am_adam"
LOGO_DIR = Path(r"C:\illustrated-narrator\assets")
LOGO_STEM = "dato_mata_gato_logo"
CIERRE_STEM = "dato_mata_gato_cierre"


def _load() -> dict[str, Any]:
    if not SESSIONS_PATH.exists():
        return {}
    return json.loads(SESSIONS_PATH.read_text(encoding="utf-8"))


def _save(data: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _update(chat_id: int, **fields: Any) -> dict[str, Any]:
    data = _load()
    key = str(chat_id)
    state = data.get(key, {})
    state.update(fields)
    data[key] = state
    _save(data)
    return state


def get_chat_state(chat_id: int) -> dict[str, Any]:
    data = _load()
    return data.get(str(chat_id), {})


def ensure_session_id(chat_id: int) -> tuple[str, bool]:
    """Devuelve (session_id, es_nueva). Genera una sesión nueva la primera
    vez que este chat escribe; la reutiliza después."""
    state = get_chat_state(chat_id)
    if state.get("session_nueva") and "session_id" in state:
        # Recién rotada por nueva_sesion_claude: todavía no existe para
        # Claude, así que hay que crearla, no retomarla.
        _update(chat_id, session_nueva=False)
        return state["session_id"], True
    if "session_id" in state:
        return state["session_id"], False
    session_id = str(uuid.uuid4())
    _update(chat_id, session_id=session_id)
    return session_id, True


def reset_session(chat_id: int) -> None:
    """Fuerza una sesión nueva en el próximo mensaje (ej. tras /nuevo)."""
    data = _load()
    data.pop(str(chat_id), None)
    _save(data)


def start_collection(chat_id: int, slug: str | None = None) -> None:
    """/nuevovideo: entra en modo recolección. Limpia el slug anterior si
    no se da uno nuevo -- se fija en cuanto llegue el guion.json."""
    _update(chat_id, phase=PHASE_COLLECTING, slug=slug)


def set_slug(chat_id: int, slug: str) -> None:
    _update(chat_id, slug=slug)


def get_slug(chat_id: int) -> str | None:
    return get_chat_state(chat_id).get("slug")


def get_phase(chat_id: int) -> str:
    return get_chat_state(chat_id).get("phase", PHASE_IDLE)


def set_phase(chat_id: int, phase: str) -> None:
    _update(chat_id, phase=phase)


def set_generating(chat_id: int, running: bool) -> None:
    _update(
        chat_id,
        generating=running,
        generating_since=(datetime.now(timezone.utc).isoformat() if running else None),
        # Quién genera: el bot o tools/retomar_lote.py, que es otro proceso.
        # Ver limpiar_generaciones_colgadas.
        generating_pid=(os.getpid() if running else None),
    )


def _proceso_vivo(pid) -> bool:
    """¿Sigue corriendo ese proceso? Sin dependencias: en Windows se le
    pregunta a kernel32 por su código de salida (259 = todavía activo)."""
    if not isinstance(pid, int) or pid <= 0:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    import ctypes
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return False
    try:
        codigo = ctypes.c_ulong()
        kernel32.GetExitCodeProcess(handle, ctypes.byref(codigo))
        return codigo.value == 259
    finally:
        kernel32.CloseHandle(handle)


def get_generating(chat_id: int) -> tuple[bool, str | None]:
    state = get_chat_state(chat_id)
    return bool(state.get("generating")), state.get("generating_since")


def set_tramos_faltantes(chat_id: int, tramos: list[tuple[str, str, int]]) -> None:
    """Los tramos de un lote que no llegaron a escribirse, para /completarlote."""
    _update(chat_id, tramos_faltantes=[list(t) for t in tramos])


def get_tramos_faltantes(chat_id: int) -> list[tuple[str, str, int]]:
    return [tuple(t) for t in (get_chat_state(chat_id).get("tramos_faltantes") or [])]


def nueva_sesion_claude(chat_id: int) -> str:
    """Empieza una conversación nueva con Claude para el chat, SIN tocar el
    resto del estado (lote pendiente, slug, voz). reset_session() borra todo."""
    session_id = str(uuid.uuid4())
    _update(chat_id, session_id=session_id, session_nueva=True)
    return session_id


def set_pausa(chat_id: int, pausado: bool) -> None:
    """Pide que el lote se detenga en el corte entre videos (o lo reanuda).

    Es una bandera en disco y no una variable en memoria a propósito: el que
    la lee es el bucle del lote, que puede estar a media hora de distancia de
    la orden, y el que la escribe es el manejador de /pausa.
    """
    _update(chat_id, pausa=pausado)


def get_pausa(chat_id: int) -> bool:
    return bool(get_chat_state(chat_id).get("pausa"))


def set_lote_sin_avatar(chat_id: int, sin_avatar: bool) -> None:
    """Marca el lote pendiente como "sin presentador" (lo escribe /lotefish3).

    El presentador es la cara de Javier con su voz; los videos de /lotefish3
    van con la voz de Fish 3 y el logo fijo, y un presentador en medio del lote
    rompería justo eso. Va en disco porque quien lo lee es /generargrande,
    que se corre después (a veces al día siguiente).
    """
    _update(chat_id, lote_sin_avatar=sin_avatar)


def get_lote_sin_avatar(chat_id: int) -> bool:
    return bool(get_chat_state(chat_id).get("lote_sin_avatar"))


def limpiar_generaciones_colgadas() -> list[str]:
    """Apaga la bandera `generating` de todos los chats. Se llama al arrancar.

    La bandera se apaga en un `finally` DENTRO del proceso que genera, así que
    si el proceso muere (lo matamos, se reinicia la máquina, se corta la luz)
    queda encendida para siempre y el bot no vuelve a arrancar nada: todos los
    comandos salen por "Ya hay algo corriendo desde ...".

    Pasó de verdad el 20/09/2026: se cortó un lote a mano y dos días después
    /lotegrande seguía rebotando con un `generating_since` de cuarenta horas
    antes. Como el pipeline corre DENTRO de este proceso (asyncio.to_thread),
    que el bot esté arrancando ya prueba que no hay nada corriendo -- así que
    apagarlas acá es correcto, no un parche.

    Devuelve los chats que estaban colgados, para dejarlo en el log.
    """
    data = _load()
    # Salvo que el que genera sea OTRO proceso que sigue vivo: desde que existe
    # tools/retomar_lote.py, un lote puede correr desde la consola mientras el
    # bot se reinicia. Antes se apagaba la bandera igual, y el bot quedaba
    # libre para arrancar un segundo lote encima -- dos corridas peleando por
    # los mismos 8 GB de la placa.
    colgados = [k for k, v in data.items()
                if v.get("generating")
                and not (v.get("generating_pid") != os.getpid()
                         and _proceso_vivo(v.get("generating_pid")))]
    for key in colgados:
        data[key]["generating"] = False
        data[key]["generating_since"] = None
        data[key]["progress"] = None
    # La pausa tampoco sobrevive al reinicio: el bucle que la esperaba ya no
    # existe, y dejarla puesta haría que el próximo lote arrancara frenado.
    pausados = [k for k, v in data.items() if v.get("pausa")]
    for key in pausados:
        data[key].pop("pausa", None)
    if colgados or pausados:
        _save(data)
    return colgados


def set_progress(chat_id: int, paso: str) -> None:
    """Paso actual del pipeline (ej. 'generando audio', 'narrator generate
    intento 2/3') -- para que /estatus diga algo mas util que 'sigue
    corriendo'."""
    _update(chat_id, progress=paso)


def get_progress(chat_id: int) -> str | None:
    return get_chat_state(chat_id).get("progress")


def staging_dir_for(chat_id: int) -> Path:
    d = STAGING_DIR / str(chat_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def set_voice(chat_id: int, voice: str) -> None:
    _update(chat_id, voice=voice)


def set_pending_batch(chat_id: int, slugs: list[str]) -> None:
    """Slugs de un lote recién escrito por /nuevolote, pendientes de que el
    usuario revise la veracidad antes de correr /generarlote sobre ellos."""
    _update(chat_id, pending_batch=slugs)


def get_pending_batch(chat_id: int) -> list[str]:
    return get_chat_state(chat_id).get("pending_batch") or []


def clear_pending_batch(chat_id: int) -> None:
    _update(chat_id, pending_batch=[])


def get_voice(chat_id: int) -> str:
    return get_chat_state(chat_id).get("voice") or DEFAULT_VOICE


def set_awaiting_logo(chat_id: int, waiting: bool) -> None:
    _update(chat_id, awaiting_logo=waiting)


def is_awaiting_logo(chat_id: int) -> bool:
    return bool(get_chat_state(chat_id).get("awaiting_logo"))


def logo_path() -> Path | None:
    """Ruta del logo del canal si ya se subió alguno con /logo (cualquier
    extensión de imagen). Es global, no por chat -- un solo logo para
    toda la serie."""
    if not LOGO_DIR.exists():
        return None
    for p in LOGO_DIR.glob(f"{LOGO_STEM}.*"):
        return p
    return None


def set_awaiting_cierre(chat_id: int, waiting: bool) -> None:
    _update(chat_id, awaiting_cierre=waiting)


def is_awaiting_cierre(chat_id: int) -> bool:
    return bool(get_chat_state(chat_id).get("awaiting_cierre"))


def cierre_path() -> Path | None:
    """Ruta del cartel/clip de cierre fijo del canal si ya se subió alguno
    con /cierre. Mismo principio que logo_path(): el plano identidad_cierre
    (logo final sobre negro puro) es contenido genérico que ninguna
    búsqueda de stock real puede encontrar -- en vez de que el pipeline se
    quede sin medio y escale a Claude cada vez, usa siempre este archivo
    fijo, igual que el logo de apertura en el plano 0."""
    if not LOGO_DIR.exists():
        return None
    for p in LOGO_DIR.glob(f"{CIERRE_STEM}.*"):
        return p
    return None


def cierre_mito_path() -> Path | None:
    """El cartel de cierre de los mitos, si existe (tools/cartel_cierre_mito.py).

    Mismo cartel del canal pero sin la palabra "caso": "¿CONOCÍAS ESTA
    LEYENDA?" en vez de "¿QUÉ OPINAS DE ESTE CASO?". El glob no choca con
    cierre_path(): "dato_mata_gato_cierre.*" no incluye "..._cierre_mito.png".
    """
    if not LOGO_DIR.exists():
        return None
    for p in LOGO_DIR.glob(f"{CIERRE_STEM}_mito.*"):
        return p
    return None


def manual_images_dir_for(slug: str) -> Path:
    """Carpeta donde se acumulan las imagenes que el usuario manda ANTES
    de /generar -- Claude las mueve a media/<plano>/elegido_N.* siguiendo
    la convencion documentada en illustrated-narrator/CLAUDE.md."""
    d = ANDROID_IN / slug / "imagenes_manuales"
    d.mkdir(parents=True, exist_ok=True)
    return d


def set_preguntas_pendientes(chat_id: int, preguntas: list[dict]) -> None:
    """Preguntas que Claude propuso y que el usuario todavía no aprobó.

    Viven en la sesión y no en el banco a propósito: al banco solo entra lo
    aprobado, que es lo que hace que el generador nunca arme un video con un
    dato que nadie miró."""
    _update(chat_id, preguntas_pendientes=preguntas)


def get_preguntas_pendientes(chat_id: int) -> list[dict]:
    return get_chat_state(chat_id).get("preguntas_pendientes") or []


def clear_preguntas_pendientes(chat_id: int) -> None:
    _update(chat_id, preguntas_pendientes=[])
