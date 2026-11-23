"""Música de fondo propia, una pista distinta en cada video (22/11/2026).

Javier escuchó 5 ambientes por canal, hechos con código (osciladores y ruido,
sin bibliotecas ni IA: son nuestros, nadie los reclama), y pidió usarlos
TODOS, rotando, "para dar percepción de variación". Las pistas se generan con
C:\\clip_assistance\\analisis\\musica\\sintetizar.py y viven en
MUSICA_DIR\\<dmg|papasia>\\*.m4a.

La música va unos 17 dB por debajo de la voz y baja sola cuando la voz habla
(sidechaincompress); entra y sale con un fundido. El video no se recodifica
(-c:v copy), solo el audio. MUSICA=0 la apaga; `plus.sin_musica` en el guion
la quita de un video.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

MUSICA_DIR = Path(os.getenv("MUSICA_DIR") or r"C:\Android_in\musica")
VOLUMEN = 0.9  # medido el 22/11/2026: la música queda ~17 dB bajo la voz (-12.7 LUFS)
FILTRO = ("[0:a]asplit=2[voz][sc];[1:a]volume={vol},afade=t=in:d=1.5,afade=t=out:st={fin}:d=2[m];"
          "[m][sc]sidechaincompress=threshold=0.02:ratio=5:attack=15:release=450[md];"
          "[voz][md]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]")
_SIN_VENTANA = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def carpeta(canal: str) -> Path:
    return MUSICA_DIR / ("papasia" if canal == "papasia" else "dmg")


def pistas(canal: str) -> list[Path]:
    return sorted(carpeta(canal).glob("*.m4a"))


def siguiente(canal: str) -> Path | None:
    """La pista que toca en este canal; avanza el turno (una distinta por video)."""
    todas = pistas(canal)
    if not todas:
        return None
    turno = carpeta(canal) / "turno.json"
    try:
        i = int(json.loads(turno.read_text(encoding="utf-8")).get("siguiente", 0))
    except (OSError, ValueError):
        i = 0
    turno.write_text(json.dumps({"siguiente": (i + 1) % len(todas)}), encoding="utf-8")
    return todas[i % len(todas)]


def _duracion(video: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                        str(video)], capture_output=True, text=True, creationflags=_SIN_VENTANA)
    return float(r.stdout.strip())


def mezclar(video: Path, pista: Path) -> bool:
    """Pone la pista debajo de la voz, en el mismo archivo. False si no se pudo
    (el video queda como estaba)."""
    fin = max(_duracion(video) - 2.0, 0.0)
    tmp = video.with_name(video.stem + "_con_musica.mp4")
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(video), "-stream_loop", "-1", "-i", str(pista),
         "-filter_complex", FILTRO.format(vol=VOLUMEN, fin=f"{fin:.2f}"),
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", "-shortest", str(tmp)],
        capture_output=True, text=True, creationflags=_SIN_VENTANA)
    if r.returncode != 0 or not tmp.exists() or tmp.stat().st_size < 100_000:
        logger.warning("música: ffmpeg falló con %s: %s", pista.name, (r.stderr or "")[-500:])
        tmp.unlink(missing_ok=True)
        return False
    os.replace(tmp, video)
    return True


def poner(guion: dict, canal: str, video: Path) -> str:
    """Le pone al video la pista que toca. Devuelve la línea para el aviso de
    Telegram ("música: dmg_3_pista"), o "" si no lleva."""
    if (os.getenv("MUSICA") or "1").strip() == "0" or (guion.get("plus") or {}).get("sin_musica"):
        return ""
    # Una sola vez por render: si el archivo es el mismo que ya se mezcló, no
    # se le encima otra pista (p. ej. un reintento de archivar).
    marca = video.with_name("musica.json")
    huella = [video.stat().st_size, int(video.stat().st_mtime)]
    try:
        previo = json.loads(marca.read_text(encoding="utf-8"))
        if previo.get("huella") == huella:
            return f"música: {previo['pista']}"
    except (OSError, ValueError, KeyError):
        pass
    pista = siguiente(canal)
    if pista is None:
        return ""
    try:
        if not mezclar(video, pista):
            return "música: falló la mezcla, el video va sin música"
    except Exception:  # noqa: BLE001 -- sin música el video sirve igual
        logger.exception("música: no se pudo mezclar %s", pista.name)
        return "música: falló la mezcla, el video va sin música"
    marca.write_text(json.dumps({"pista": pista.stem, "huella": [video.stat().st_size,
                                                                 int(video.stat().st_mtime)]}),
                     encoding="utf-8")
    return f"música: {pista.stem}"
