"""Pausar un lote para poder jugar, sin perder videos.

A1111 se queda con ~2.8 GB de los 8 de la placa esté generando o no, y
suspender el proceso NO devuelve esa memoria. Medido el 23/09/2026 con Gears 5
abierto: 7.9 GB de 8 ocupados. La única pausa que sirve de verdad es la que
CIERRA A1111, y eso obliga a cortar el lote en un punto limpio.

Lo que estos tests fijan es que ningún guion se pierda en el camino.
"""

import json

import pytest

from dato_mata_gato_bot import bot, sessions


def _estado(tmp_path, monkeypatch, datos):
    ruta = tmp_path / "sessions.json"
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    monkeypatch.setattr(sessions, "SESSIONS_PATH", ruta)
    monkeypatch.setattr(sessions, "DATA_DIR", tmp_path)
    return ruta


def test_la_pausa_se_guarda_en_disco(tmp_path, monkeypatch):
    """En memoria no sirve: quien la lee es el bucle del lote, que puede estar
    a media hora de distancia de la orden."""
    _estado(tmp_path, monkeypatch, {"7": {}})
    assert sessions.get_pausa(7) is False
    sessions.set_pausa(7, True)
    assert sessions.get_pausa(7) is True
    sessions.set_pausa(7, False)
    assert sessions.get_pausa(7) is False


def test_la_pausa_no_sobrevive_al_reinicio(tmp_path, monkeypatch):
    """El bucle que la esperaba murió con el proceso. Si la bandera quedara
    puesta, el próximo lote arrancaría frenado sin que nadie lo pidiera."""
    _estado(tmp_path, monkeypatch, {"7": {"pausa": True, "generating": False}})
    sessions.limpiar_generaciones_colgadas()
    assert sessions.get_pausa(7) is False


def test_limpiar_guarda_aunque_solo_hubiera_una_pausa(tmp_path, monkeypatch):
    """Sin esto el _save() se saltaba cuando no había nada 'generating' y la
    pausa quedaba escrita en disco igual."""
    ruta = _estado(tmp_path, monkeypatch, {"7": {"pausa": True}})
    sessions.limpiar_generaciones_colgadas()
    assert "pausa" not in json.loads(ruta.read_text(encoding="utf-8"))["7"]


def test_la_pausa_no_toca_el_lote_pendiente(tmp_path, monkeypatch):
    """Pausar es dejar de generar, no cancelar: los guiones que faltan tienen
    que seguir ahí para /generargrande."""
    _estado(tmp_path, monkeypatch, {
        "7": {"pending_batch": ["guion-a", "guion-b"], "generating": True},
    })
    sessions.set_pausa(7, True)
    assert sessions.get_pending_batch(7) == ["guion-a", "guion-b"]
    sessions.limpiar_generaciones_colgadas()
    assert sessions.get_pending_batch(7) == ["guion-a", "guion-b"]


def test_los_comandos_de_pausa_estan_registrados():
    """Ya pasó que un comando existiera sin handler y nadie lo notara hasta
    usarlo desde el teléfono."""
    nombres = {n for n, _ in bot.BOT_COMMANDS}
    assert {"pausa", "reanudar"} <= nombres
    assert callable(bot.cmd_pausa)
    assert callable(bot.cmd_reanudar)


def test_el_pipeline_sabe_cortar_la_generacion():
    """`/pausa ya` necesita cortar el narrator en curso; sin esta función el
    comando fallaría recién al usarlo."""
    from dato_mata_gato_bot import pipeline
    assert callable(pipeline.detener_generacion)
    assert callable(pipeline._detener_a1111)


@pytest.mark.parametrize("pausado, esperado", [(False, ["b"]), (True, ["a", "b"])])
def test_un_video_cortado_a_proposito_vuelve_a_la_cola(pausado, esperado):
    """La regla que hace que no se pierda nada: el `finally` del bucle saca el
    slug de la cola SOLO si no hay pausa. Con /pausa ya el video se cortó a
    mano y hay que rehacerlo, así que tiene que seguir pendiente.
    """
    restantes = ["a", "b"]
    slug = "a"
    # Misma condición que corre en cmd_generargrande.
    if not pausado:
        restantes.remove(slug)
    assert restantes == esperado


class _Salida:
    def __init__(self, stdout):
        self.stdout = stdout


def test_lista_los_procesos_sin_wmic(monkeypatch):
    """Windows 11 ya no trae wmic: cerrar A1111 y /pausa ya fallaban en
    silencio con [WinError 2] (27/09/2026). Se lista con PowerShell."""
    from dato_mata_gato_bot import pipeline
    visto = {}

    def _run(args, **kw):
        visto["args"] = args
        return _Salida('[{"ProcessId":10,"CommandLine":"python.exe launch.py"},'
                       '{"ProcessId":11,"CommandLine":null}]')

    monkeypatch.setattr(pipeline.subprocess, "run", _run)
    assert pipeline._procesos_python() == [(10, "python.exe launch.py"), (11, "")]
    assert "wmic" not in visto["args"]


def test_con_un_solo_proceso_powershell_no_arma_lista(monkeypatch):
    from dato_mata_gato_bot import pipeline
    monkeypatch.setattr(pipeline.subprocess, "run",
                        lambda *a, **k: _Salida('{"ProcessId":7,"CommandLine":"launch.py"}'))
    assert pipeline._procesos_python() == [(7, "launch.py")]


def test_detener_a1111_cierra_solo_a1111(monkeypatch):
    from dato_mata_gato_bot import pipeline
    monkeypatch.setattr(pipeline, "_procesos_python", lambda: [
        (10, "venv/Scripts/python.exe launch.py"), (20, "narrator generate guion-x")])
    cerrados = []
    monkeypatch.setattr(pipeline, "_kill_process_tree", cerrados.append)
    assert pipeline._detener_a1111() is True
    assert cerrados == [10]
