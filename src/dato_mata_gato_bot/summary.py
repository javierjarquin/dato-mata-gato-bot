"""Resumen por plano de un guion -- puro código, sin Claude. Lee
guion.json (y manifest.json si ya se generó) para armar un vistazo
rápido de qué dice cada plano y cómo va su estado de medios."""

import json
from pathlib import Path

ANDROID_IN = Path(r"C:\Android_in")
NARRATOR_PROJECTS = Path(r"C:\illustrated-narrator\projects")

_NARRACION_MAX = 90


def _find_guion(slug: str) -> Path | None:
    # Preferir el del proyecto ya generado (tiene duraciones reales); si
    # no existe todavía, caer al original recién subido.
    for candidate in (NARRATOR_PROJECTS / slug / "guion.json", ANDROID_IN / slug / "guion.json"):
        if candidate.exists():
            return candidate
    return None


def load_guion_dict(slug: str) -> dict | None:
    guion_path = _find_guion(slug)
    if guion_path is None:
        return None
    return json.loads(guion_path.read_text(encoding="utf-8"))


def find_plano(guion: dict, plano_id: str) -> dict | None:
    plano_id = plano_id.lower()
    for p in guion.get("planos", []):
        if str(p.get("id", "")).lower() == plano_id:
            return p
    return None


def _shot_status(manifest: dict, plano_id: str) -> str:
    shots = [k for k in manifest if k.startswith(f"{plano_id}_")]
    if not shots:
        return ""
    resueltos = sum(1 for k in shots if manifest[k].get("chosen"))
    return f" [medios: {resueltos}/{len(shots)}]"


def build_summary(slug: str) -> str:
    guion_path = _find_guion(slug)
    if guion_path is None:
        return f"No encontré guion.json para '{slug}' (ni en Android_in ni en illustrated-narrator/projects)."

    guion = json.loads(guion_path.read_text(encoding="utf-8"))
    planos = guion.get("planos", [])
    if not planos:
        return f"'{slug}' no tiene planos en su guion.json."

    manifest_path = NARRATOR_PROJECTS / slug / "media" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}

    lines = [f"{guion.get('titulo', slug)}", f"{len(planos)} planos", ""]
    for p in planos:
        pid = p.get("id", "?")
        seccion = p.get("seccion", "")
        dur = p.get("duracion_seg", "?")
        narr = (p.get("narracion") or "").strip()
        if len(narr) > _NARRACION_MAX:
            narr = narr[:_NARRACION_MAX] + "…"
        estado = _shot_status(manifest, pid)
        lines.append(f"{pid} ({seccion}, {dur}s){estado}\n  {narr}")

    return "\n".join(lines)
