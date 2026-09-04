"""Calendario de publicación progresivo -- puro código, sin Claude.

Cada slug NUEVO toma el día siguiente al último ya asignado (días de
calendario consecutivos, arrancando en ANCHOR_DATE). Reintentos del mismo
slug (ej. Claude corrige y vuelve a subir) NO consumen una fecha nueva --
assign_date es idempotente por slug.
"""

import json
from datetime import date, datetime, timedelta
from pathlib import Path

ANCHOR_DATE = date(2026, 8, 25)  # martes 25/08/2026
SCHEDULE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "publish_schedule.json"


def _load() -> dict[str, dict]:
    if not SCHEDULE_PATH.exists():
        return {}
    return json.loads(SCHEDULE_PATH.read_text(encoding="utf-8"))


def _save(data: dict[str, dict]) -> None:
    SCHEDULE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULE_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def parse_fecha(fecha_str: str) -> date:
    return date(int(fecha_str[4:8]), int(fecha_str[2:4]), int(fecha_str[0:2]))


def _last_date(data: dict[str, dict]) -> date | None:
    fechas = [parse_fecha(entry["fecha"]) for entry in data.values() if entry.get("fecha")]
    return max(fechas) if fechas else None


def assign_date(slug: str) -> str:
    """Fecha (DDMMYYYY) asignada a este slug -- idempotente: si ya tenía
    una, la devuelve tal cual; si es nuevo, toma el día siguiente al
    último asignado (o el ancla, si es el primero de todos)."""
    data = _load()
    entry = data.get(slug)
    if entry and entry.get("fecha"):
        return entry["fecha"]

    last = _last_date(data)
    next_date = (last + timedelta(days=1)) if last else ANCHOR_DATE
    fecha_str = next_date.strftime("%d%m%Y")
    data.setdefault(slug, {})["fecha"] = fecha_str
    _save(data)
    return fecha_str


def record_upload(slug: str, nombre_archivo: str, drive_link: str) -> None:
    """Guarda el resultado de la subida (nombre real usado + link) contra
    la fecha ya asignada al slug."""
    data = _load()
    entry = data.setdefault(slug, {})
    entry["nombre_archivo"] = nombre_archivo
    entry["drive_link"] = drive_link
    entry["subido_en"] = datetime.now().isoformat(timespec="seconds")
    _save(data)


def record_facebook_publish(slug: str, post_id: str, url: str | None) -> None:
    """Marca el slug como YA publicado en Facebook. Es lo que hace idempotente
    a la publicación diaria: el bot se reinicia solo (acceso directo en Inicio
    de Windows) y el job diario puede volver a dispararse el mismo día, así
    que sin esta marca se publicaría el mismo video dos veces en la Página."""
    data = _load()
    entry = data.setdefault(slug, {})
    entry["facebook_post_id"] = post_id
    if url:
        entry["facebook_url"] = url
    entry["publicado_fb_en"] = datetime.now().isoformat(timespec="seconds")
    _save(data)


def ya_publicado_en_facebook(slug: str) -> bool:
    return bool(_load().get(slug, {}).get("publicado_fb_en"))


def slug_para_fecha(fecha_str: str) -> str | None:
    """Slug al que le toca publicarse en esa fecha (DDMMYYYY), o None."""
    for slug, entry in _load().items():
        if entry.get("fecha") == fecha_str:
            return slug
    return None


def all_entries() -> dict[str, dict]:
    return _load()
