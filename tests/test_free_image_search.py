from unittest.mock import MagicMock, patch

from dato_mata_gato_bot import free_image_search


def _resp(json_data):
    r = MagicMock()
    r.json.return_value = json_data
    r.raise_for_status.return_value = None
    return r


@patch("dato_mata_gato_bot.free_image_search.wiki_images.fetch_content_images")
def test_search_wikipedia_url_adapta_wikiimage_a_imageresult(mock_fetch):
    mock_fetch.return_value = [
        wiki_images_stub("Archivo:Foto.jpg", "https://example.com/foto.jpg", "CC BY-SA 4.0", "Alguien"),
    ]
    resultado = free_image_search.search_wikipedia_url("https://es.wikipedia.org/wiki/Prueba")
    assert resultado == [
        free_image_search.ImageResult(
            titulo="Archivo:Foto.jpg",
            url="https://example.com/foto.jpg",
            licencia="CC BY-SA 4.0",
            autor="Alguien",
            fuente="wikipedia",
        )
    ]


def wiki_images_stub(archivo, url, licencia, autor):
    from dato_mata_gato_bot.wiki_images import WikiImage
    return WikiImage(archivo=archivo, url=url, licencia=licencia, autor=autor, credito=None, commons=True)


@patch("dato_mata_gato_bot.free_image_search.wiki_images.find_article_url")
@patch("dato_mata_gato_bot.free_image_search.search_wikipedia_url")
def test_search_wikipedia_busca_articulo_por_query(mock_search_url, mock_find_url):
    mock_find_url.return_value = "https://es.wikipedia.org/wiki/Criptograf%C3%ADa"
    mock_search_url.return_value = [
        free_image_search.ImageResult("x", "https://x", None, None, "wikipedia")
    ]
    resultado = free_image_search.search_wikipedia("criptografía")
    mock_find_url.assert_called_once_with("criptografía")
    mock_search_url.assert_called_once_with("https://es.wikipedia.org/wiki/Criptograf%C3%ADa")
    assert len(resultado) == 1


@patch("dato_mata_gato_bot.free_image_search.wiki_images.find_article_url")
def test_search_wikipedia_sin_articulo_devuelve_lista_vacia(mock_find_url):
    mock_find_url.return_value = None
    assert free_image_search.search_wikipedia("algo inexistente") == []


@patch("dato_mata_gato_bot.free_image_search.wiki_images.find_article_url")
def test_search_wikipedia_atrapa_excepciones(mock_find_url):
    mock_find_url.side_effect = Exception("red caída")
    assert free_image_search.search_wikipedia("algo") == []


@patch("dato_mata_gato_bot.free_image_search.requests.get")
def test_search_openverse_devuelve_resultados(mock_get):
    mock_get.return_value = _resp({"results": [
        {"title": "Máquina Enigma", "url": "https://example.com/enigma.jpg",
         "license": "cc0", "creator": "Alguien", "provider": "flickr"},
        {"title": "Sin url"},
    ]})
    resultado = free_image_search.search_openverse("enigma")
    assert len(resultado) == 1
    assert resultado[0] == free_image_search.ImageResult(
        titulo="Máquina Enigma", url="https://example.com/enigma.jpg",
        licencia="cc0", autor="Alguien", fuente="openverse/flickr",
    )


@patch("dato_mata_gato_bot.free_image_search.requests.get")
def test_search_openverse_atrapa_excepciones(mock_get):
    mock_get.side_effect = Exception("timeout")
    assert free_image_search.search_openverse("enigma") == []


@patch("dato_mata_gato_bot.free_image_search.requests.get")
def test_search_nasa_devuelve_resultados_con_link_preview(mock_get):
    mock_get.return_value = _resp({"collection": {"items": [
        {
            "data": [{"title": "Foto NASA", "photographer": "Fulano"}],
            "links": [{"href": "https://nasa.example/preview.jpg", "rel": "preview"}],
        },
        {
            "data": [{"title": "Sin preview"}],
            "links": [{"href": "https://nasa.example/otra.jpg", "rel": "orig"}],
        },
    ]}})
    resultado = free_image_search.search_nasa("apollo")
    assert len(resultado) == 1
    assert resultado[0].titulo == "Foto NASA"
    assert resultado[0].url == "https://nasa.example/preview.jpg"
    assert resultado[0].fuente == "nasa"
    assert "público" in resultado[0].licencia.lower()


@patch("dato_mata_gato_bot.free_image_search.requests.get")
def test_search_nasa_atrapa_excepciones(mock_get):
    mock_get.side_effect = Exception("500")
    assert free_image_search.search_nasa("apollo") == []


@patch("dato_mata_gato_bot.free_image_search.search_nasa")
@patch("dato_mata_gato_bot.free_image_search.search_openverse")
@patch("dato_mata_gato_bot.free_image_search.search_wikipedia")
def test_search_all_concatena_las_tres_fuentes(mock_wiki, mock_openverse, mock_nasa):
    mock_wiki.return_value = [free_image_search.ImageResult("a", "urlA", None, None, "wikipedia")]
    mock_openverse.return_value = [free_image_search.ImageResult("b", "urlB", None, None, "openverse/x")]
    mock_nasa.return_value = [free_image_search.ImageResult("c", "urlC", None, None, "nasa")]

    resultado = free_image_search.search_all("algo")

    assert [r.titulo for r in resultado] == ["a", "b", "c"]
