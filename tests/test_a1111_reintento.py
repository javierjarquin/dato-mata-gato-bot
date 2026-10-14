"""Un tropiezo de A1111 no debe costar un video entero.

A1111 solo se usa como respaldo cuando una toma se quedó sin medio real, pero
cuando falla hace fallar todo el video. En un lote de treinta eso son horas de
máquina perdidas por un servicio auxiliar.
"""

from dato_mata_gato_bot.pipeline import _es_falla_de_a1111


def test_reconoce_el_500_por_falta_de_memoria():
    """Visto el 18/09/2026 en guion-ficrea-fraude."""
    assert _es_falla_de_a1111(
        "1 plano(s) sin medio real (NARR_IMAGE_BACKEND=none): p00: 500 Server "
        "Error: Internal Server Error for url: http://127.0.0.1:7860/sdapi/v1/txt2img"
    )


def test_reconoce_que_no_levanto():
    """Visto el mismo día al regenerarlo: el puerto y la ruta van separados,
    y la primera versión del detector se lo perdió."""
    assert _es_falla_de_a1111(
        "1 plano(s) sin medio real: p00: HTTPConnectionPool(host='127.0.0.1', "
        "port=7860): Max retries exceeded with url: /sdapi/v1/txt2img "
        "(Caused by NewConnectionError(...))"
    )


def test_no_reintenta_un_guion_roto():
    """Un plano mal escrito falla igual cuantas veces se reintente: gastar
    otra corrida de veinte minutos en eso no ayuda a nadie."""
    assert not _es_falla_de_a1111("guion.json inválido: p03 sin narración")
    assert not _es_falla_de_a1111("ffmpeg: Invalid data found when processing input")
    assert not _es_falla_de_a1111("")
    assert not _es_falla_de_a1111(None)
