"""Evidencia de redes sociales (15/10/2026).

El formato de tema viral necesita enseñar EL FENÓMENO, y el fenómeno vive en
redes, no en los noticieros. Javier: "vamos a optar por esa parte de agarrar la
evidencia en las redes sociales". Hasta hoy `evidencia.py` solo sabía capturar
titulares de prensa, páginas de PDF y fotos de Wikimedia, y por eso estos videos
salían planos: contaban un video viral sin enseñarlo nunca.

Dos piezas, según lo que haya:

  video_red   el clip en sí (yt-dlp), recortado a unos segundos. Es la prueba en
              movimiento: lo que se ve es lo que se discute.
  red_social  la publicación capturada (Playwright): el post con su autor, su
              fecha y sus números -- vistas, likes, comentarios. Sirve cuando el
              video ya no se puede bajar (lo borraron, pide sesión) y, sobre
              todo, para probar QUÉ TAN GRANDE fue el fenómeno, que es la pieza
              que al canal le faltaba para justificar el tema.

Va con crédito siempre, como cita de actualidad (LFDA art. 148-II). El crédito
sale del autor real de la publicación, no del sitio.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image

from dato_mata_gato_bot import evidencia

logger = logging.getLogger(__name__)

SEGUNDOS = 6          # lo que dura una toma en el guion
_SIN_VENTANA = getattr(subprocess, "CREATE_NO_WINDOW", 0)

REDES = {
    "tiktok.com": "TikTok", "vm.tiktok.com": "TikTok", "vt.tiktok.com": "TikTok",
    "instagram.com": "Instagram", "facebook.com": "Facebook", "fb.watch": "Facebook",
    "x.com": "X", "twitter.com": "X", "youtube.com": "YouTube", "youtu.be": "YouTube",
    "threads.net": "Threads",
}


def es_red_social(url: str) -> bool:
    host = urlparse(url or "").netloc.lower().removeprefix("www.")
    return any(host == d or host.endswith("." + d) for d in REDES)


def red_de(url: str) -> str:
    host = urlparse(url or "").netloc.lower().removeprefix("www.")
    for dominio, nombre in REDES.items():
        if host == dominio or host.endswith("." + dominio):
            return nombre
    return host or "redes"


def _credito(pieza: dict, meta: dict) -> str:
    """Lo que va al pie. Primero lo que diga el guion; si no, autor y red."""
    if pieza.get("fuente"):
        return pieza["fuente"]
    autor = meta.get("uploader") or meta.get("channel") or ""
    red = red_de(pieza.get("url", ""))
    return f"{autor} · {red}".strip(" ·") if autor else red


def bajar_video(pieza: dict, destino: Path) -> dict:
    """El clip, recortado a `SEGUNDOS`. Devuelve el meta para el manifest.

    `destino` es el .jpg de la pieza (la portada, para el manifest); el video
    queda a su lado con .mp4, que es lo que usa el render.
    """
    import yt_dlp

    url = pieza["url"]
    with tempfile.TemporaryDirectory() as tmp:
        plantilla = str(Path(tmp) / "x.%(ext)s")
        opciones = {"outtmpl": plantilla, "quiet": True, "no_warnings": True,
                    "noprogress": True, "consoletitle": False, "logger": logger,
                    "noplaylist": True, "format": "mp4/best[ext=mp4]/best",
                    # Lo público, sin sesión: si pide login, que falle y se use
                    # la captura de la publicación en vez de inventar nada.
                    "cookiesfrombrowser": None, "retries": 2, "socket_timeout": 30}
        with yt_dlp.YoutubeDL(opciones) as y:
            meta = y.extract_info(url, download=True)
        bajado = next((p for p in Path(tmp).iterdir() if p.suffix in (".mp4", ".webm", ".mkv")), None)
        if bajado is None:
            raise ValueError("yt-dlp no dejó archivo de video")
        mp4 = destino.with_suffix(".mp4")
        desde = float(pieza.get("desde_seg", 0) or 0)
        # Recorte + vertical 1080x1920 con los bordes rellenos, como el resto.
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-ss", str(desde), "-i", str(bajado),
             "-t", str(float(pieza.get("segundos", SEGUNDOS))),
             "-vf", (f"scale={evidencia.ANCHO}:{evidencia.ALTO}:force_original_aspect_ratio=decrease,"
                     f"pad={evidencia.ANCHO}:{evidencia.ALTO}:(ow-iw)/2:(oh-ih)/2:color=0x0e0e10"),
             "-an", "-c:v", "libx264", "-crf", "23", "-pix_fmt", "yuv420p", str(mp4)],
            check=True, creationflags=_SIN_VENTANA)
        # Un cuadro como portada, para que la pieza también exista como imagen.
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp4),
                        "-frames:v", "1", str(destino)], check=False, creationflags=_SIN_VENTANA)
    cred = _credito(pieza, meta or {})
    return {"fuente": url, "credito": cred, "video": mp4.name,
            "titulo": (meta or {}).get("title", "")[:200],
            "vistas": (meta or {}).get("view_count"), "likes": (meta or {}).get("like_count")}


_JS_NUMEROS = r"""
() => {
  const txt = document.body.innerText || "";
  const pat = /([\d.,]+\s?(?:mil|millones|M|K|B)?)\s*(vistas|views|reproducciones|me gusta|likes|comentarios|comments|compartidos|shares)/gi;
  const out = [];
  let m;
  while ((m = pat.exec(txt)) !== null && out.length < 6) out.push(m[0].trim());
  return out;
}
"""


def capturar_publicacion(paginas, pieza: dict, destino: Path) -> dict:
    """La publicación como se ve, con sus números. Sin login: lo público.

    No se exige que mencione el caso (a diferencia de `capturar_titular`): un
    post de TikTok casi no trae texto, y lo que prueba es el fenómeno, no el
    dato. El dato lo sostiene el nivel 2.
    """
    pagina = paginas.new_page()
    try:
        resp = pagina.goto(pieza["url"], wait_until="domcontentloaded", timeout=45000)
        if resp is not None and resp.status >= 400:
            raise ValueError(f"HTTP {resp.status}")
        pagina.wait_for_timeout(4500)
        for texto in ("Aceptar", "Acepto", "Permitir todas", "Entendido", "Cerrar",
                      "Ahora no", "Not now", "Allow all", "Accept all"):
            try:
                pagina.get_by_role("button", name=texto).first.click(timeout=500)
            except Exception:  # noqa: BLE001
                pass
        pagina.wait_for_timeout(800)
        try:
            numeros = pagina.evaluate(_JS_NUMEROS) or []
        except Exception:  # noqa: BLE001
            numeros = []
        crudo = destino.with_suffix(".captura.png")
        pagina.screenshot(path=str(crudo), clip={"x": 0, "y": 0, "width": 430, "height": 620})
        evidencia.montar_tarjeta(Image.open(crudo), _credito(pieza, {}), destino)
        crudo.unlink(missing_ok=True)
        return {"fuente": pieza["url"], "credito": _credito(pieza, {}),
                "numeros": numeros[:3], "red": red_de(pieza["url"])}
    finally:
        pagina.close()


def armar(paginas, pieza: dict, destino: Path) -> dict:
    """La pieza de redes: el video si se deja bajar, si no la publicación.

    Un clip que no se puede bajar (borrado, privado, pide sesión) no tira el
    tema: la captura del post prueba igual que existió y qué tan grande fue.
    """
    if pieza.get("tipo") == "video_red":
        try:
            return {"tipo": "video_red", **bajar_video(pieza, destino)}
        except Exception as exc:  # noqa: BLE001 -- se cae a la captura
            logger.warning("video_red %s: %s; se usa la publicación", pieza.get("id"), exc)
            if paginas is None:
                raise
    return {"tipo": "red_social", **capturar_publicacion(paginas, pieza, destino)}
