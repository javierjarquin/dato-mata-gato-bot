from unittest.mock import MagicMock, patch

from dato_mata_gato_bot import wiki_images


def _resp(json_data):
    r = MagicMock()
    r.json.return_value = json_data
    r.raise_for_status.return_value = None
    return r


@patch("dato_mata_gato_bot.wiki_images.requests.get")
def test_filtra_logos_de_proyectos_hermanos(mock_get):
    lista_imagenes = _resp({"query": {"pages": {"1": {"images": [
        {"title": "Archivo:Commons-logo.svg"},
        {"title": "Archivo:Wikidata-logo.svg"},
        {"title": "Archivo:Foto real de contenido.jpg"},
    ]}}}})
    info_imagenes = _resp({"query": {"pages": {"1": {
        "title": "Archivo:Foto real de contenido.jpg",
        "imagerepository": "shared",
        "imageinfo": [{"url": "https://example.com/foto.jpg", "extmetadata": {
            "LicenseShortName": {"value": "CC BY-SA 4.0"},
            "Artist": {"value": "Alguien"},
        }}],
    }}}})
    mock_get.side_effect = [lista_imagenes, info_imagenes]

    resultado = wiki_images.fetch_content_images("https://es.wikipedia.org/wiki/Prueba")

    assert len(resultado) == 1
    assert resultado[0].archivo == "Archivo:Foto real de contenido.jpg"
    assert resultado[0].licencia == "CC BY-SA 4.0"


@patch("dato_mata_gato_bot.wiki_images.requests.get")
def test_sin_imagenes_devuelve_lista_vacia(mock_get):
    mock_get.return_value = _resp({"query": {"pages": {"1": {"images": []}}}})
    assert wiki_images.fetch_content_images("https://es.wikipedia.org/wiki/Vacio") == []


@patch("dato_mata_gato_bot.wiki_images.requests.get")
def test_descarta_no_commons_si_solo_libres(mock_get):
    lista_imagenes = _resp({"query": {"pages": {"1": {"images": [
        {"title": "Archivo:Local.jpg"},
    ]}}}})
    info_imagenes = _resp({"query": {"pages": {"1": {
        "title": "Archivo:Local.jpg",
        "imagerepository": "local",  # NO es de Commons
        "imageinfo": [{"url": "https://example.com/local.jpg", "extmetadata": {}}],
    }}}})
    mock_get.side_effect = [lista_imagenes, info_imagenes]

    resultado = wiki_images.fetch_content_images("https://es.wikipedia.org/wiki/Prueba", solo_libres=True)
    assert resultado == []


@patch("dato_mata_gato_bot.wiki_images.requests.get")
def test_find_article_url_devuelve_url_del_primer_resultado(mock_get):
    mock_get.return_value = _resp({"query": {"search": [{"title": "Criptografía"}]}})
    url = wiki_images.find_article_url("criptografia")
    assert url == "https://es.wikipedia.org/wiki/Criptografía"


@patch("dato_mata_gato_bot.wiki_images.requests.get")
def test_find_article_url_sin_resultados_devuelve_none(mock_get):
    mock_get.return_value = _resp({"query": {"search": []}})
    assert wiki_images.find_article_url("asdkjhaskjdh") is None
