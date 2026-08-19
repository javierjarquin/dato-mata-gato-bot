"""Estado por chat de Telegram: qué sesión de Claude Code le corresponde,
y en qué slug (proyecto) está trabajando. Persistido en disco para
sobrevivir reinicios del bot."""

import json
import uuid
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
SESSIONS_PATH = DATA_DIR / "sessions.json"
STAGING_DIR = DATA_DIR / "staging"


def _load() -> dict[str, Any]:
    if not SESSIONS_PATH.exists():
        return {}
    return json.loads(SESSIONS_PATH.read_text(encoding="utf-8"))


def _save(data: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_chat_state(chat_id: int) -> dict[str, Any]:
    data = _load()
    return data.get(str(chat_id), {})


def ensure_session_id(chat_id: int) -> tuple[str, bool]:
    """Devuelve (session_id, es_nueva). Genera una sesión nueva la primera
    vez que este chat escribe; la reutiliza después."""
    data = _load()
    key = str(chat_id)
    state = data.get(key, {})
    if "session_id" in state:
        return state["session_id"], False
    session_id = str(uuid.uuid4())
    state["session_id"] = session_id
    data[key] = state
    _save(data)
    return session_id, True


def reset_session(chat_id: int) -> None:
    """Fuerza una sesión nueva en el próximo mensaje (ej. tras /nuevo)."""
    data = _load()
    data.pop(str(chat_id), None)
    _save(data)


def set_slug(chat_id: int, slug: str) -> None:
    data = _load()
    key = str(chat_id)
    state = data.get(key, {})
    state["slug"] = slug
    data[key] = state
    _save(data)


def get_slug(chat_id: int) -> str | None:
    return get_chat_state(chat_id).get("slug")


def staging_dir_for(chat_id: int) -> Path:
    d = STAGING_DIR / str(chat_id)
    d.mkdir(parents=True, exist_ok=True)
    return d
