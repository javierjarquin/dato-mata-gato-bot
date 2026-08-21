"""Trae imágenes de contenido de un artículo de Wikipedia, con su licencia
real, vía la API oficial de MediaWiki (adaptado de fuentes.py del
usuario). Filtra los íconos/logos genéricos de los proyectos hermanos de
Wikimedia, que no son contenido real del artículo.

Uso pensado: herramienta de investigación manual (/investigar en el bot),
NUNCA parte obligatoria del pipeline de /generar -- si esto falla, no
debe bloquear la generación de ningún video."""

import re
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

import requests

UA = "Mozilla/5.0 (compatible; InvestigacionPersonal/1.0)"
TIMEOUT = 25

# Iconos/logos de proyectos hermanos y de mantenimiento de Wikimedia --
# nunca son "contenido" del artículo, aunque aparezcan en la lista de
# imágenes embebidas.
_RUIDO = re.compile(
    r"commons-logo|wikidata|wikibooks|wiktionary|wikiquote|wikisource|"
    r"wikiversity|wikivoyage|wikispecies|wikinews|wikimedia[-_]|"
    r"wikipedia[-_]?logo|padlock|ambox|question[_ ]book|nuvola|ooui|"
    r"edit-icon|folder icon|crystal_clear|gnome-|pictogram|"
    r"disambig|merge-arrow",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class WikiImage:
    archivo: str
    url: str
    licencia: str | None
    autor: str | None
    credito: str | None
    commons: bool


WIKI_API_ES = "https://es.wikipedia.org/w/api.php"


def _api_wiki(url: str) -> tuple[str, str]:
    p = urlparse(url)
    titulo = unquote(p.path.split("/wiki/", 1)[-1])
    return f"{p.scheme}://{p.netloc}/w/api.php", titulo


def find_article_url(query: str, api: str = WIKI_API_ES) -> str | None:
    """Busca por palabras clave y devuelve la URL del artículo más
    relevante, o None si no hay resultados."""
    r = requests.get(api, timeout=TIMEOUT, headers={"User-Agent": UA}, params={
        "action": "query", "list": "search", "srsearch": query,
        "srlimit": 1, "format": "json",
    })
    r.raise_for_status()
    resultados = r.json().get("query", {}).get("search", [])
    if not resultados:
        return None
    titulo = resultados[0]["title"]
    dominio = api.split("/w/api.php")[0]
    return f"{dominio}/wiki/{titulo.replace(' ', '_')}"


def fetch_content_images(wiki_url: str, solo_libres: bool = True) -> list[WikiImage]:
    """Imágenes de contenido de un artículo (sin logos de proyecto). Si
    solo_libres=True, descarta las que no están en Commons (imágenes de
    "uso legítimo" locales, casi nunca reutilizables)."""
    api, titulo = _api_wiki(wiki_url)
    r = requests.get(api, timeout=TIMEOUT, headers={"User-Agent": UA}, params={
        "action": "query", "prop": "images", "imlimit": "max",
        "redirects": 1, "format": "json", "titles": titulo,
    })
    r.raise_for_status()
    pagina = next(iter(r.json()["query"]["pages"].values()))
    archivos = [i["title"] for i in pagina.get("images", []) if not _RUIDO.search(i["title"])]
    if not archivos:
        return []

    resultado: list[WikiImage] = []
    for i in range(0, len(archivos), 20):
        lote = "|".join(archivos[i : i + 20])
        r = requests.get(api, timeout=TIMEOUT, headers={"User-Agent": UA}, params={
            "action": "query", "prop": "imageinfo",
            "iiprop": "url|extmetadata", "format": "json", "titles": lote,
        })
        r.raise_for_status()
        for pag in r.json()["query"]["pages"].values():
            info = (pag.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata", {})

            def m(k: str) -> str | None:
                v = meta.get(k, {}).get("value", "")
                return re.sub(r"<[^>]+>", "", v).strip() or None

            es_commons = pag.get("imagerepository") == "shared"
            if solo_libres and not es_commons:
                continue
            if not info.get("url"):
                continue
            resultado.append(WikiImage(
                archivo=pag.get("title", ""),
                url=info["url"],
                licencia=m("LicenseShortName"),
                autor=m("Artist"),
                credito=m("Credit"),
                commons=es_commons,
            ))
    return resultado
