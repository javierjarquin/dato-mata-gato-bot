"""Busca imágenes libres en varias fuentes verificadas (Wikipedia,
Openverse, NASA) a partir de una URL o de palabras clave -- ninguna
necesita API key. Cada fuente es independiente: si una falla, se ignora
y se sigue con las demás -- nunca bloquea la búsqueda completa ni el
pipeline de /generar (esto es una herramienta aparte, /investigar)."""

import logging
from dataclasses import dataclass

import requests

from dato_mata_gato_bot import wiki_images

logger = logging.getLogger(__name__)

UA = "Mozilla/5.0 (compatible; DatoMataGatoBot/1.0)"
TIMEOUT = 20


@dataclass(frozen=True)
class ImageResult:
    titulo: str
    url: str
    licencia: str | None
    autor: str | None
    fuente: str


def search_wikipedia_url(url: str) -> list[ImageResult]:
    imagenes = wiki_images.fetch_content_images(url)
    return [
        ImageResult(titulo=i.archivo, url=i.url, licencia=i.licencia, autor=i.autor, fuente="wikipedia")
        for i in imagenes
    ]


def search_wikipedia(query: str) -> list[ImageResult]:
    try:
        url = wiki_images.find_article_url(query)
        if not url:
            return []
        return search_wikipedia_url(url)
    except Exception as exc:
        logger.warning("search_wikipedia falló para %r: %s", query, exc)
        return []


def search_openverse(query: str, limite: int = 5) -> list[ImageResult]:
    try:
        r = requests.get(
            "https://api.openverse.org/v1/images/", timeout=TIMEOUT,
            headers={"User-Agent": UA},
            params={"q": query, "license_type": "all", "page_size": limite},
        )
        r.raise_for_status()
        resultados = r.json().get("results", [])
        return [
            ImageResult(
                titulo=item.get("title") or "(sin título)",
                url=item["url"],
                licencia=item.get("license"),
                autor=item.get("creator"),
                fuente=f"openverse/{item.get('provider', '?')}",
            )
            for item in resultados if item.get("url")
        ]
    except Exception as exc:
        logger.warning("search_openverse falló para %r: %s", query, exc)
        return []


def search_nasa(query: str, limite: int = 3) -> list[ImageResult]:
    try:
        r = requests.get(
            "https://images-api.nasa.gov/search", timeout=TIMEOUT,
            headers={"User-Agent": UA},
            params={"q": query, "media_type": "image"},
        )
        r.raise_for_status()
        items = (r.json().get("collection", {}).get("items") or [])[:limite]
        resultado = []
        for item in items:
            data = (item.get("data") or [{}])[0]
            links = item.get("links") or []
            url = next((link["href"] for link in links if link.get("rel") == "preview"), None)
            if not url:
                continue
            resultado.append(ImageResult(
                titulo=data.get("title") or "(sin título)",
                url=url,
                licencia="Dominio público (obra del gobierno de EE.UU.)",
                autor=data.get("photographer") or data.get("center"),
                fuente="nasa",
            ))
        return resultado
    except Exception as exc:
        logger.warning("search_nasa falló para %r: %s", query, exc)
        return []


def search_all(query: str) -> list[ImageResult]:
    """Busca en todas las fuentes libres verificadas a partir de
    palabras clave (sin URL). Cada fuente falla en silencio si hay
    problema de red -- nunca tira toda la búsqueda."""
    resultados: list[ImageResult] = []
    resultados += search_wikipedia(query)
    resultados += search_openverse(query)
    resultados += search_nasa(query)
    return resultados
