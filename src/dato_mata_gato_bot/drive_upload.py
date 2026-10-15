"""Sube el video final a la carpeta de Drive de publicación, con el
nombre progresivo (ver publish_schedule.py)."""

import logging
import re
import time
import unicodedata
from pathlib import Path

from googleapiclient.http import MediaFileUpload

from dato_mata_gato_bot.drive_auth import get_drive_service

logger = logging.getLogger(__name__)

_WORD_RE = re.compile(r"[a-z0-9]+")

# Subida por trozos de 8 MB: un corte de red cuesta ese trozo y no el archivo.
_CHUNK_BYTES = 8 * 1024 * 1024
_REINTENTOS = 5


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
    return subir_archivo(local_path, build_filename(titulo, fecha), folder_id)


def subir_archivo(
    local_path: Path, nombre: str, folder_id: str, reusar_existente: bool = False
) -> tuple[str, str]:
    """Sube un archivo con el nombre que se le diga. Devuelve (nombre, link).

    Aparte de upload_video porque el nombre progresivo (titulo_DDMMYYYY) es la
    convención del CALENDARIO del canal; los trozos de un video ajeno no
    tienen fecha de publicación ni entran ahí.

    Con `reusar_existente`, si ya hay un archivo con ese nombre en la carpeta
    se devuelve ese en vez de subir otro. Es lo que hace que repetir un troceo
    que se cortó a mitad (token vencido, red) retome en vez de dejar cada
    trozo duplicado: Drive acepta nombres repetidos sin chistar.
    """
    service = get_drive_service()
    if reusar_existente:
        ya = _buscar_por_nombre(service, nombre, folder_id)
        if ya is not None:
            return ya

    # Por trozos y con reintentos: subir 46 MB de un tirón se cortaba con
    # "EOF occurred in violation of protocol" a mitad del TLS (confirmado
    # subiendo los trozos de una película). next_chunk(num_retries=...) hace
    # backoff y reintenta SOLO el trozo que falló, no el archivo entero.
    media = MediaFileUpload(
        str(local_path), mimetype="video/mp4", resumable=True, chunksize=_CHUNK_BYTES,
    )
    pedido = service.files().create(
        body={"name": nombre, "parents": [folder_id]},
        media_body=media,
        fields="id, webViewLink",
    )
    file = None
    fallos = 0
    while file is None:
        try:
            _, file = pedido.next_chunk(num_retries=_REINTENTOS)
            fallos = 0
        except OSError as exc:
            # `num_retries` de googleapiclient NO cubre el SSLEOFError que tira
            # esta conexión al subir archivos grandes (visto real: murió en el
            # trozo 12 de 73). Se reintenta sobre el MISMO pedido, que conserva
            # la URI de sesión y por lo tanto RETOMA en vez de empezar de cero.
            fallos += 1
            if fallos > _REINTENTOS:
                raise
            espera = min(2 ** fallos, 30)
            logger.warning(
                "Subida de %s cortada (%s); reintento %d/%d en %ds",
                nombre, exc, fallos, _REINTENTOS, espera,
            )
            time.sleep(espera)
    link = file.get("webViewLink") or f"https://drive.google.com/file/d/{file['id']}/view"
    return nombre, link


def _escapar(valor: str) -> str:
    """Escapa un nombre para meterlo en una query de la API de Drive."""
    return valor.replace("\\", "\\\\").replace("'", "\\'")


def _buscar_por_nombre(service, nombre: str, folder_id: str) -> tuple[str, str] | None:
    consulta = (
        f"name = '{_escapar(nombre)}' and '{folder_id}' in parents and trashed = false"
    )
    archivos = service.files().list(
        q=consulta, fields="files(id, name, webViewLink)", pageSize=1,
    ).execute().get("files", [])
    if not archivos:
        return None
    f = archivos[0]
    return f["name"], f.get("webViewLink") or f"https://drive.google.com/file/d/{f['id']}/view"


def asegurar_carpeta(nombre: str, parent_id: str | None = None) -> str:
    """ID de la carpeta `nombre` dentro de `parent_id`, creándola si no está.

    Se busca antes de crear para que repetir el mismo video no deje carpetas
    duplicadas con el mismo nombre -- Drive las permite, y quedarían dos
    "Resumen 19 Junio" distintas sin forma de saber cuál es cuál.
    """
    service = get_drive_service()
    consulta = (
        "mimeType = 'application/vnd.google-apps.folder'"
        f" and name = '{_escapar(nombre)}' and trashed = false"
    )
    if parent_id:
        consulta += f" and '{parent_id}' in parents"
    encontrados = service.files().list(
        q=consulta, fields="files(id, name)", pageSize=1,
    ).execute().get("files", [])
    if encontrados:
        return encontrados[0]["id"]

    cuerpo = {"name": nombre, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        cuerpo["parents"] = [parent_id]
    return service.files().create(body=cuerpo, fields="id").execute()["id"]
