"""Lista los videos programados/publicados en Drive -- puro código, sin
Claude. Lee publish_schedule.json, no llama a la API de Drive."""

from dataclasses import dataclass
from datetime import date

from dato_mata_gato_bot import publish_schedule


@dataclass(frozen=True)
class VideoInfo:
    slug: str
    nombre_archivo: str | None
    fecha_publicacion: date | None
    drive_link: str | None

    @property
    def subido(self) -> bool:
        return self.drive_link is not None


def list_generated_videos() -> list[VideoInfo]:
    """Ordenado por fecha de publicación, más próxima primero."""
    data = publish_schedule.all_entries()
    videos = []
    for slug, entry in data.items():
        fecha_str = entry.get("fecha")
        fecha = publish_schedule.parse_fecha(fecha_str) if fecha_str else None
        videos.append(VideoInfo(
            slug=slug,
            nombre_archivo=entry.get("nombre_archivo"),
            fecha_publicacion=fecha,
            drive_link=entry.get("drive_link"),
        ))
    videos.sort(key=lambda v: v.fecha_publicacion or date.max)
    return videos


def format_video_list(videos: list[VideoInfo]) -> str:
    if not videos:
        return "Todavía no hay ningún video programado."

    lineas = [f"{len(videos)} video(s):", ""]
    for v in videos:
        fecha = v.fecha_publicacion.strftime("%d/%m/%Y") if v.fecha_publicacion else "?"
        estado = "subido" if v.subido else "PENDIENTE de subir"
        nombre = v.nombre_archivo or v.slug
        lineas.append(f"• {nombre} — publicar el {fecha} — {estado}")
    return "\n".join(lineas)
