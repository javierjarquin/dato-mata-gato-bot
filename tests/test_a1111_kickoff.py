from unittest.mock import MagicMock, patch

from dato_mata_gato_bot import pipeline


@patch("dato_mata_gato_bot.pipeline.requests.get")
def test_a1111_ready_true_si_responde_ok(mock_get):
    mock_get.return_value = MagicMock(ok=True)
    assert pipeline._a1111_ready() is True


@patch("dato_mata_gato_bot.pipeline.requests.get")
def test_a1111_ready_false_si_falla_la_conexion(mock_get):
    import requests
    mock_get.side_effect = requests.exceptions.ConnectionError("no está corriendo")
    assert pipeline._a1111_ready() is False


@patch("dato_mata_gato_bot.pipeline.subprocess.Popen")
@patch("dato_mata_gato_bot.pipeline._a1111_ready", return_value=True)
def test_kick_off_no_lanza_nada_si_ya_esta_listo(mock_ready, mock_popen):
    pipeline._kick_off_a1111_if_needed()
    mock_popen.assert_not_called()


@patch("dato_mata_gato_bot.pipeline.subprocess.Popen")
@patch("dato_mata_gato_bot.pipeline._a1111_ready", return_value=False)
def test_kick_off_lanza_el_bat_sin_esperar_si_no_esta_listo(mock_ready, mock_popen):
    pipeline._kick_off_a1111_if_needed()
    mock_popen.assert_called_once()
    args, kwargs = mock_popen.call_args
    assert args[0] == [pipeline.A1111_BAT]
    assert kwargs["cwd"] == pipeline.A1111_TOOLS_DIR


@patch("dato_mata_gato_bot.pipeline.subprocess.Popen", side_effect=OSError("no se pudo"))
@patch("dato_mata_gato_bot.pipeline._a1111_ready", return_value=False)
def test_kick_off_no_rompe_la_corrida_si_falla_el_lanzamiento(mock_ready, mock_popen):
    pipeline._kick_off_a1111_if_needed()  # no debe lanzar
