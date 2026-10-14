"""Troceo de un video ajeno: parseo del resultado y nombre de carpeta local."""

from dato_mata_gato_bot import pipeline


def test_lee_la_linea_de_resultado_entre_el_ruido():
    # El CLI imprime avisos de progreso y los logs de yt-dlp y ffmpeg; el
    # resultado es UNA línea en medio de todo eso.
    salida = (
        "[download] 100%\n"
        "… cortando 1/2\n"
        'RESULTADO {"titulo": "Un video", "trozos": [{"indice": 1}]}\n'
        "algo mas despues\n"
    )
    assert pipeline._parsear_resultado_troceo(salida)["titulo"] == "Un video"


def test_sin_linea_de_resultado_devuelve_none():
    # Pasa cuando el CLI muere a mitad: mejor avisar que reventar parseando.
    assert pipeline._parsear_resultado_troceo("solo logs\ny mas logs") is None


def test_un_json_roto_no_explota():
    assert pipeline._parsear_resultado_troceo('RESULTADO {"titulo": roto}') is None


def test_se_queda_con_la_ultima_linea_de_resultado():
    salida = 'RESULTADO {"titulo": "viejo"}\nRESULTADO {"titulo": "nuevo"}'
    assert pipeline._parsear_resultado_troceo(salida)["titulo"] == "nuevo"


def test_la_carpeta_local_sale_de_la_url_sin_caracteres_raros():
    carpeta = pipeline._slug_de_url("https://www.youtube.com/watch?v=D8tbR3r9R3U&t=10s")
    assert "?" not in carpeta and "&" not in carpeta and "/" not in carpeta
    assert "D8tbR3r9R3U" in carpeta


def test_dos_urls_distintas_no_comparten_carpeta():
    a = pipeline._slug_de_url("https://www.youtube.com/watch?v=AAAAAAAAAAA")
    b = pipeline._slug_de_url("https://www.youtube.com/watch?v=BBBBBBBBBBB")
    assert a != b


# --- chequeo del motor de voz antes del lote ---------------------------------

def test_con_voicestudio_arriba_no_avisa_nada(monkeypatch):
    monkeypatch.setenv("TTS_ENGINE", "voicestudio")
    monkeypatch.setattr(pipeline.requests, "get",
                        lambda *a, **k: type("R", (), {"ok": True, "status_code": 200})())
    assert pipeline.motor_tts_listo() == ""


def test_con_voicestudio_caido_avisa_antes_de_arrancar(monkeypatch):
    # Es lo que pasó el 14/09/2026: el contenedor estaba abajo, el primer video
    # se cayó en el audio y escaló a Claude. Quince minutos por un chequeo.
    monkeypatch.setenv("TTS_ENGINE", "voicestudio")

    def _explota(*a, **k):
        raise pipeline.requests.RequestException("connection refused")

    monkeypatch.setattr(pipeline.requests, "get", _explota)
    aviso = pipeline.motor_tts_listo()
    assert "Docker" in aviso and "no responde" in aviso


def test_un_http_de_error_tambien_avisa(monkeypatch):
    monkeypatch.setenv("TTS_ENGINE", "voicestudio")
    monkeypatch.setattr(pipeline.requests, "get",
                        lambda *a, **k: type("R", (), {"ok": False, "status_code": 503})())
    assert "503" in pipeline.motor_tts_listo()


def test_con_kokoro_no_se_chequea_nada(monkeypatch):
    # Kokoro corre local, no hay contenedor que levantar.
    monkeypatch.setenv("TTS_ENGINE", "kokoro")
    monkeypatch.setattr(pipeline.requests, "get",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no debió consultar")))
    assert pipeline.motor_tts_listo() == ""
