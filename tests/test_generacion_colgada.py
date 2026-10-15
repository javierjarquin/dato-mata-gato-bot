"""La bandera `generating` no puede sobrevivir a un reinicio del bot.

Se apaga en un `finally` dentro del proceso que genera, así que si ese proceso
muere la bandera queda encendida en disco y TODOS los comandos rebotan con
"Ya hay algo corriendo desde ...". Pasó de verdad: un lote cortado a mano el
20/09/2026 dejó /lotegrande inutilizable durante dos días.
"""

import json

from dato_mata_gato_bot import sessions


def _con_estado(tmp_path, monkeypatch, estado):
    ruta = tmp_path / "sessions.json"
    ruta.write_text(json.dumps(estado), encoding="utf-8")
    monkeypatch.setattr(sessions, "SESSIONS_PATH", ruta)
    monkeypatch.setattr(sessions, "DATA_DIR", tmp_path)
    return ruta


def test_una_generacion_que_no_termino_no_bloquea_el_arranque(tmp_path, monkeypatch):
    _con_estado(tmp_path, monkeypatch, {
        "111": {"generating": True,
                "generating_since": "2026-09-21T02:31:36+00:00",
                "progress": "corriendo narrator generate (intento 1)"},
    })
    assert sessions.get_generating(111)[0]

    colgados = sessions.limpiar_generaciones_colgadas()

    assert colgados == ["111"]
    assert sessions.get_generating(111) == (False, None)
    assert sessions.get_progress(111) is None


def test_limpia_todos_los_chats_no_solo_el_primero(tmp_path, monkeypatch):
    _con_estado(tmp_path, monkeypatch, {
        "111": {"generating": True, "generating_since": "ayer"},
        "222": {"generating": False, "generating_since": None},
        "333": {"generating": True, "generating_since": "ayer"},
    })
    assert sorted(sessions.limpiar_generaciones_colgadas()) == ["111", "333"]
    assert not sessions.get_generating(111)[0]
    assert not sessions.get_generating(333)[0]


def test_no_toca_el_resto_del_estado(tmp_path, monkeypatch):
    """Apagar la bandera no puede costar el lote pendiente ni la sesión: el
    usuario tiene que poder retomar con /generarlote después del reinicio."""
    _con_estado(tmp_path, monkeypatch, {
        "111": {"generating": True, "generating_since": "ayer",
                "session_id": "abc-123", "slug": "guion-clancy-co",
                "pending_batch": ["guion-uno", "trivia-dos"]},
    })
    sessions.limpiar_generaciones_colgadas()

    estado = sessions.get_chat_state(111)
    assert estado["session_id"] == "abc-123"
    assert estado["slug"] == "guion-clancy-co"
    assert sessions.get_pending_batch(111) == ["guion-uno", "trivia-dos"]


def test_sin_nada_colgado_no_reescribe_el_archivo(tmp_path, monkeypatch):
    ruta = _con_estado(tmp_path, monkeypatch, {
        "111": {"generating": False, "generating_since": None},
    })
    antes = ruta.stat().st_mtime_ns
    assert sessions.limpiar_generaciones_colgadas() == []
    assert ruta.stat().st_mtime_ns == antes


def test_no_limpia_la_bandera_de_un_lote_que_corre_desde_la_consola(tmp_path, monkeypatch):
    """tools/retomar_lote.py es otro proceso: si el bot se reinicia mientras
    ese lote corre, la bandera tiene que quedar, o el bot arranca un segundo
    lote encima."""
    import os
    _con_estado(tmp_path, monkeypatch, {
        "111": {"generating": True, "generating_since": "ahora",
                "generating_pid": os.getppid()},   # un proceso que sigue vivo
        "222": {"generating": True, "generating_since": "ayer",
                "generating_pid": 999999},          # uno que ya no existe
    })
    assert sessions.limpiar_generaciones_colgadas() == ["222"]
    assert sessions.get_generating(111)[0] is True
    assert sessions.get_generating(222)[0] is False


def test_la_bandera_guarda_quien_genera(tmp_path, monkeypatch):
    import os
    _con_estado(tmp_path, monkeypatch, {"111": {}})
    sessions.set_generating(111, True)
    assert sessions.get_chat_state(111)["generating_pid"] == os.getpid()
    sessions.set_generating(111, False)
    assert sessions.get_chat_state(111)["generating_pid"] is None
