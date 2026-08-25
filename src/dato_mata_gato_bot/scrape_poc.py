"""POC suelto, sin ninguna relación con el pipeline de Dato Mata Gato: baja
todas las imágenes y audios de UNA página (no recorre links, a propósito --
todavía no). Usa un navegador real (Playwright) y agarra los archivos que
efectivamente se descargan al cargar la página, no lo que dice el HTML
crudo -- así funciona igual si el sitio es estático o un SPA de React que
arma todo con JavaScript.
"""

from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Response, sync_playwright

_IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".bmp", ".ico")
_AUDIO_EXT = (".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac")


def _kind_of(url: str, content_type: str) -> str | None:
    path = urlparse(url).path.lower()
    if path.endswith(_IMAGE_EXT) or content_type.startswith("image/"):
        return "images"
    if path.endswith(_AUDIO_EXT) or content_type.startswith("audio/"):
        return "audio"
    return None


def _unique_dest(out_dir: Path, kind: str, url: str) -> Path:
    name = Path(urlparse(url).path).name or "recurso"
    dest = out_dir / kind / name
    i = 1
    while dest.exists():
        dest = out_dir / kind / f"{dest.stem}_{i}{dest.suffix}"
        i += 1
    return dest


def scrape_page(url: str, out_dir: Path, timeout_ms: int = 30_000) -> tuple[list[Path], list[Path]]:
    """Carga UNA página y guarda cada imagen/audio que se descargue al
    renderizarla. Devuelve (rutas_imagenes, rutas_audio)."""
    (out_dir / "images").mkdir(parents=True, exist_ok=True)
    (out_dir / "audio").mkdir(parents=True, exist_ok=True)
    imagenes: list[Path] = []
    audios: list[Path] = []
    vistas: set[str] = set()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        def on_response(response: Response) -> None:
            resp_url = response.url
            if resp_url in vistas:
                return
            kind = _kind_of(resp_url, response.headers.get("content-type", ""))
            if not kind:
                return
            try:
                body = response.body()
            except Exception:
                return
            vistas.add(resp_url)
            dest = _unique_dest(out_dir, kind, resp_url)
            dest.write_bytes(body)
            (imagenes if kind == "images" else audios).append(dest)

        page.on("response", on_response)
        page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        browser.close()

    return imagenes, audios
