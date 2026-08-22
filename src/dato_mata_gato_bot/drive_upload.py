"""Sube el video final a la carpeta de Drive de publicación, con el
nombre progresivo (ver publish_schedule.py)."""

import re
import unicodedata
from pathlib import Path

from googleapiclient.http import MediaFileUpload

from dato_mata_gato_bot.drive_auth import get_drive_service

_WORD_RE = re.compile(r"[a-z0-9]+")


def slugify_titulo(titulo: str) -> str:
    """'Criptografía' -> 'criptografia'. Minúsculas, sin acentos, sin
    espacios/símbolos -- palabras unidas sin separador (así se pidió:
    criptografia_25082026, no cripto-grafia)."""
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFKD", titulo) if not unicodedata.combining(c)
    )
    return "".join(_WORD_RE.findall(sin_acentos.lower())) or "video"


def build_filename(titulo: str, fecha: str) -> str:
    return f"{slugify_titulo(titulo)}_{fecha}.mp4"


def upload_video(local_path: Path, titulo: str, fecha: str, folder_id: str) -> tuple[str, str]:
    """Sube local_path a la carpeta de Drive. Devuelve (nombre_usado, link)."""
    nombre = build_filename(titulo, fecha)
    service = get_drive_service()
    media = MediaFileUpload(str(local_path), mimetype="video/mp4", resumable=True)
    file = service.files().create(
        body={"name": nombre, "parents": [folder_id]},
        media_body=media,
        fields="id, webViewLink",
    ).execute()
    link = file.get("webViewLink") or f"https://drive.google.com/file/d/{file['id']}/view"
    return nombre, link
