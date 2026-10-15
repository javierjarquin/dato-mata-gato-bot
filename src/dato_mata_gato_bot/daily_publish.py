"""Publicación diaria automática (un video por día, 20:00 hora de México).

Facebook se publica solo por la Graph API (ya configurada y verificada).
TikTok NO: la Content Posting API deja los posts en privado de forma
permanente mientras la app no esté auditada, así que el aviso de Telegram
incluye el material listo (título, hashtags, link de Drive) para subirlo a
mano -- ver README. Automatizar TikTok con un navegador headless para
saltear esa auditoría violaría sus términos y expone la cuenta a baneo:
no se hace.
"""

import json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from dato_mata_gato_bot import pipeline, publish_schedule

logger = logging.getLogger(__name__)

NARRATOR_PROJECTS = Path(r"C:\illustrated-narrator\projects")
TIMEZONE = "America/Mexico_City"


@dataclass
class VideoDelDia:
    slug: str
    titulo: str
    hashtags: list[str]
    drive_link: str | None
    final_mp4: Path

    @property
    def caption_tiktok(self) -> str:
        tags = " ".join(self.hashtags)
        return f"{self.titulo}\n\n{tags}".strip()


def fecha_hoy(hoy: date) -> str:
    """date -> DDMMYYYY, el formato que usa publish_schedule."""
    return hoy.strftime("%d%m%Y")


def leer_guion(slug: str) -> dict:
    path = NARRATOR_PROJECTS / slug / "guion.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.exception("No se pudo leer el guion de %s", slug)
        return {}


def video_del_dia(hoy: date) -> VideoDelDia | None:
    """El video que toca publicar hoy, o None si no hay ninguno agendado o
    si el de hoy ya se publicó (idempotencia ante reinicios del bot)."""
    slug = publish_schedule.slug_para_fecha(fecha_hoy(hoy))
    if slug is None:
        return None
    if publish_schedule.ya_publicado_en_facebook(slug):
        logger.info("%s ya estaba publicado en Facebook, no se repite", slug)
        return None

    entry = publish_schedule.all_entries().get(slug, {})
    guion = leer_guion(slug)
    return VideoDelDia(
        slug=slug,
        titulo=guion.get("titulo") or slug,
        hashtags=guion.get("hashtags") or [],
        drive_link=entry.get("drive_link"),
        final_mp4=NARRATOR_PROJECTS / slug / "final.mp4",
    )


def _extraer_post(salida: str) -> tuple[str, str | None]:
    """`narrator publish` imprime 'Publicado. ID: <id>' y opcionalmente
    'URL: <url>'. Se parsea de ahí porque el pipeline invoca el CLI como
    subproceso y no tiene acceso al PublishResult."""
    post_id, url = "", None
    for linea in salida.splitlines():
        linea = linea.strip()
        if linea.startswith("Publicado. ID:"):
            post_id = linea.split(":", 1)[1].strip()
        elif linea.startswith("URL:"):
            url = linea.split(":", 1)[1].strip()
    return post_id, url


def publicar_en_facebook(video: VideoDelDia) -> tuple[bool, str]:
    """Publica y deja registrado el resultado. Devuelve (ok, mensaje listo
    para Telegram)."""
    if not video.final_mp4.exists():
        return False, (
            f"⚠️ Hoy tocaba *{video.titulo}* pero no existe el video "
            f"(`{video.final_mp4.name}` no está). No se publicó nada."
        )

    ok, salida = pipeline.publish_to_facebook(video.slug)
    if not ok:
        return False, (
            f"❌ Falló la publicación en Facebook de *{video.titulo}*.\n\n"
            f"```\n{salida[-600:]}\n```"
        )

    post_id, url = _extraer_post(salida)
    publish_schedule.record_facebook_publish(video.slug, post_id, url)

    texto = f"✅ Publicado en Facebook: *{video.titulo}*"
    if url:
        texto += f"\n{url}"
    return True, texto


def mensaje_tiktok(video: VideoDelDia) -> str:
    """Aviso con el material listo para subir a TikTok a mano."""
    partes = [
        "📱 *Para subir a TikTok* (manual hasta que pase la auditoría):",
        "",
        "Caption listo para copiar:",
        f"```\n{video.caption_tiktok}\n```",
    ]
    if video.drive_link:
        partes.append(f"Video: {video.drive_link}")
    return "\n".join(partes)
