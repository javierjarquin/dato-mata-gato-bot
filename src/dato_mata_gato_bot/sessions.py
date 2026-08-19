"""Estado por chat de Telegram: fase (recolectando/listo), slug del
proyecto, sesión de Claude Code asociada, y si hay una generación en
curso. Persistido en disco para sobrevivir reinicios del bot."""

import json
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
    )


def get_generating(chat_id: int) -> tuple[bool, str | None]:
    state = get_chat_state(chat_id)
    return bool(state.get("generating")), state.get("generating_since")


def staging_dir_for(chat_id: int) -> Path:
    d = STAGING_DIR / str(chat_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def manual_images_dir_for(slug: str) -> Path:
    """Carpeta donde se acumulan las imagenes que el usuario manda ANTES
    de /generar -- Claude las mueve a media/<plano>/elegido_N.* siguiendo
    la convencion documentada en illustrated-narrator/CLAUDE.md."""
    d = ANDROID_IN / slug / "imagenes_manuales"
    d.mkdir(parents=True, exist_ok=True)
    return d
