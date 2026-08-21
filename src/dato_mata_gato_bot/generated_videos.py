"""Lista los videos ya generados en Android_out -- puro código, sin
Claude. Solo lee el sistema de archivos."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ANDROID_OUT = Path(r"C:\Android_out")


@dataclass(frozen=True)
class VideoInfo:
    slug: str
    ruta: Path
    tamano_mb: float
    modificado: datetime


def list_generated_videos() -> list[VideoInfo]:
    """Más reciente primero."""
    if not ANDROID_OUT.exists():
        return []

    videos = []
    for f in ANDROID_OUT.glob("*.mp4"):
        stat = f.stat()
        videos.append(VideoInfo(
            slug=f.stem,
            ruta=f,
            tamano_mb=round(stat.st_size / (1024 * 1024), 1),
            modificado=datetime.fromtimestamp(stat.st_mtime),
        ))
    videos.sort(key=lambda v: v.modificado, reverse=True)
    return videos


def format_video_list(videos: list[VideoInfo]) -> str:
    if not videos:
        return f"Todavía no hay ningún video generado en {ANDROID_OUT}."

    lineas = [f"{len(videos)} video(s) generado(s):", ""]
    for v in videos:
        fecha = v.modificado.strftime("%d/%m/%Y %H:%M")
        lineas.append(f"• {v.slug} — {v.tamano_mb} MB — {fecha}")
    return "\n".join(lineas)
