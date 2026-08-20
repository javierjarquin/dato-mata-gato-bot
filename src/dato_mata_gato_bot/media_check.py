"""Validación determinística de coherencia geográfica en manifest.json —
sin Claude. Blocklist armada con los falsos positivos reales que ya vimos
en corridas anteriores (Pexels/Wikimedia devuelven resultados de
cualquier país aunque la query diga "Mexico City")."""

import json
import re
from dataclasses import dataclass
from pathlib import Path

# Frases completas primero (para que "New Mexico" no choque con "Mexico"),
# despues nombres sueltos de lugar. Case-insensitive.
_BLOCKLIST_PHRASES = ["new mexico"]
_BLOCKLIST_WORDS = [
    "china", "poland", "polonia", "turkey", "turquía", "turquia",
    "istanbul", "İstanbul", "argentina", "ushuaia", "philadelphia",
    "alcatraz", "beijing", "wisconsin", "bucharest", "bucarest",
    "berlin", "berlín", "sochi", "russia", "rusia", "hong kong",
    "srinagar", "bangladesh", "kashmir", "stafford", "oxford",
    "gloucester", "england", "united kingdom", "wroclaw", "wrocław",
    "bursa", "buenos aires", "manila", "philippines", "filipinas",
    "ludhiana", "venezuela", "hawaii", "haway",
]

_PATTERN = re.compile(
    "|".join(re.escape(p) for p in _BLOCKLIST_PHRASES + _BLOCKLIST_WORDS),
    re.IGNORECASE,
)


@dataclass
class FlaggedShot:
    shot_id: str
    reason: str  # "pais_incoherente" | "sin_medio"
    detalle: str


def _manifest_path(illustrated_narrator_projects: Path, slug: str) -> Path:
    return illustrated_narrator_projects / slug / "media" / "manifest.json"


def check_manifest(illustrated_narrator_projects: Path, slug: str) -> list[FlaggedShot]:
    """Escanea manifest.json y devuelve las tomas con país incoherente o
    sin ningún medio resuelto. No hace red ni llama a Claude."""
    path = _manifest_path(illustrated_narrator_projects, slug)
    if not path.exists():
        return []

    manifest = json.loads(path.read_text(encoding="utf-8"))
    flagged: list[FlaggedShot] = []

    for shot_id, entry in manifest.items():
        chosen = entry.get("chosen")
        if chosen is None:
            flagged.append(FlaggedShot(shot_id, "sin_medio", ""))
            continue
        title = chosen.get("title", "")
        match = _PATTERN.search(title)
        if match:
            flagged.append(FlaggedShot(shot_id, "pais_incoherente", f"'{match.group()}' en: {title[:80]}"))

    return flagged
