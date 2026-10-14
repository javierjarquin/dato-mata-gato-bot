"""Calendario de publicación progresivo -- puro código, sin Claude.

Desde el 12/09/2026 la modalidad es de POR_DIA videos por día: cada slug nuevo
va al primer día con cupo libre a partir de ANCLA_ACTUAL. Antes de eso era uno
por día, arrancando en ANCHOR_DATE.

Reintentos del mismo slug (ej. Claude corrige y vuelve a subir) NO consumen una
fecha nueva -- assign_date es idempotente por slug.
"""

import json
from datetime import date, datetime, timedelta
from pathlib import Path

ANCHOR_DATE = date(2026, 8, 25)  # martes 25/08/2026 -- ancla de la modalidad vieja

# Modalidad nueva: 5 videos por día, arrancando el 12/09/2026. Las entradas
# anteriores quedan como están (ya se publicaron) y NO cuentan para el cupo: se
# distinguen porque no llevan el campo `modalidad`. Sin esa distinción, un slug
# nuevo caería en los días sueltos que dejó el calendario viejo.
ANCLA_ACTUAL = date(2026, 9, 12)
POR_DIA = 5
MODALIDAD = f"{POR_DIA}-por-dia"

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


def _ocupacion(data: dict[str, dict]) -> dict[str, int]:
    """Cuántos slugs de la modalidad actual hay en cada fecha."""
    cuenta: dict[str, int] = {}
    for entry in data.values():
        if entry.get("modalidad") == MODALIDAD and entry.get("fecha"):
            cuenta[entry["fecha"]] = cuenta.get(entry["fecha"], 0) + 1
    return cuenta


def _primer_dia_con_cupo(data: dict[str, dict]) -> date:
    cuenta = _ocupacion(data)
    dia = ANCLA_ACTUAL
    while cuenta.get(dia.strftime("%d%m%Y"), 0) >= POR_DIA:
        dia += timedelta(days=1)
    return dia


def assign_date(slug: str) -> str:
    """Fecha (DDMMYYYY) asignada a este slug -- idempotente: si ya tenía una, la
    devuelve tal cual; si es nuevo, va al primer día con cupo desde ANCLA_ACTUAL."""
    data = _load()
    entry = data.get(slug)
    if entry and entry.get("fecha"):
        return entry["fecha"]

    fecha_str = _primer_dia_con_cupo(data).strftime("%d%m%Y")
    nueva = data.setdefault(slug, {})
    nueva["fecha"] = fecha_str
    # Marca la modalidad con la que se asignó: es lo que separa estas entradas
    # de las del calendario viejo a la hora de contar el cupo del día.
    nueva["modalidad"] = MODALIDAD
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


def slugs_para_fecha(fecha_str: str) -> list[str]:
    """Slugs agendados para esa fecha (DDMMYYYY). Con la modalidad de POR_DIA
    por día pueden ser varios."""
    return [slug for slug, entry in _load().items() if entry.get("fecha") == fecha_str]


def slug_para_fecha(fecha_str: str) -> str | None:
    """El primero de los agendados para esa fecha, o None.

    Se conserva para el job diario, que publica de a uno. Con varios el mismo
    día devuelve solo el primero: usá slugs_para_fecha() si los querés todos."""
    slugs = slugs_para_fecha(fecha_str)
    return slugs[0] if slugs else None


def all_entries() -> dict[str, dict]:
    return _load()


def contar_por_tipo() -> dict[str, int]:
    """Cuántos videos de cada tipo hay agendados en la modalidad actual.

    Se cuenta sobre el calendario y no sobre los lotes pedidos, así el reparto
    se corrige solo si un lote se generó a medias."""
    cuenta = {"crimen": 0, "trivia": 0}
    for slug, entry in _load().items():
        if entry.get("modalidad") != MODALIDAD:
            continue
        cuenta["trivia" if slug.startswith("trivia-") else "crimen"] += 1
    return cuenta
