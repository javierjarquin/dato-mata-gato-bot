"""Separación de canales (15/11/2026): Dato Mata Gato y papasia comparten el
motor, pero no los comandos, ni el estado del chat, ni los avisos."""

import importlib

import pytest

from dato_mata_gato_bot import canal


@pytest.fixture
def en_papasia(monkeypatch):
    monkeypatch.setenv(canal.VARIABLE, "papasia")


def test_el_canal_base_es_dato_mata_gato(monkeypatch):
    monkeypatch.delenv(canal.VARIABLE, raising=False)
    assert canal.actual() == ""
    assert canal.data_dir() == canal.RAIZ_BOT / "data"


def test_papasia_guarda_su_estado_aparte(en_papasia):
    assert canal.data_dir() == canal.RAIZ_BOT / "data" / "papasia"


def test_de_que_canal_es_cada_formato():
    assert canal.de_formato("papasia") == "papasia"
    for formato in ("todos", "redes", "cercania", "tradiciones", "viral", None):
        assert canal.de_formato(formato) == ""


def test_un_lote_viejo_sin_canal_se_reconoce_por_su_formato():
    assert canal.de_estado({"formato": "papasia"}) == "papasia"
    assert canal.de_estado({"formato": "todos"}) == ""
    assert canal.de_estado({"formato": "todos", "canal": "papasia"}) == "papasia"


def test_cada_bot_solo_ve_sus_lotes(monkeypatch, en_papasia):
    assert canal.es_mio({"formato": "papasia"})
    assert not canal.es_mio({"formato": "todos"})
    monkeypatch.delenv(canal.VARIABLE)
    assert canal.es_mio({"formato": "todos"})
    assert not canal.es_mio({"formato": "papasia"})


def test_perfil_de_la_linea_de_comandos():
    assert canal.de_argv(["bot"]) == ""
    assert canal.de_argv(["bot", "--perfil", "papasia"]) == "papasia"
    with pytest.raises(SystemExit):
        canal.de_argv(["bot", "--perfil"])


def test_cargar_un_perfil_que_no_existe_no_arranca():
    with pytest.raises(SystemExit):
        canal.cargar("no-existe")


def test_la_fabrica_anota_el_canal_del_lote(tmp_path, monkeypatch):
    from dato_mata_gato_bot import fabrica

    monkeypatch.setattr(fabrica, "RAIZ", tmp_path)
    assert fabrica.crear("papasia-x", 2, "papasia")["canal"] == "papasia"
    assert fabrica.crear("todos-x", 2, "todos")["canal"] == ""


def test_sesiones_y_log_van_a_la_carpeta_del_canal(en_papasia):
    from dato_mata_gato_bot import logging_config, sessions

    try:
        importlib.reload(sessions)
        importlib.reload(logging_config)
        assert sessions.SESSIONS_PATH == canal.RAIZ_BOT / "data" / "papasia" / "sessions.json"
        assert logging_config.LOG_PATH == canal.RAIZ_BOT / "data" / "papasia" / "bot.log"
    finally:
        import os

        os.environ.pop(canal.VARIABLE, None)
        importlib.reload(sessions)
        importlib.reload(logging_config)


def test_el_menu_de_dato_mata_gato_ya_no_trae_papasia():
    from dato_mata_gato_bot import bot

    assert "papasia" not in [c for c, _ in bot.BOT_COMMANDS]
    assert "/papasia" not in bot.HELP_TEXT
    comandos = [c for c, _ in bot.BOT_COMMANDS_PAPASIA]
    assert "papasia" in comandos and "lotegrande" not in comandos
    assert "/lotegrande" not in bot.HELP_PAPASIA


# --- Carpetas por canal (punto 3, 15/11/2026) ---------------------------------

def test_cada_canal_tiene_su_carpeta(monkeypatch, en_papasia):
    assert canal.entrada() == canal.ENTRADA_BASE / "papasia"
    assert canal.raiz_fabrica() == canal.ENTRADA_BASE / "papasia" / "fabrica"
    assert canal.entrada("") == canal.ENTRADA_BASE
    monkeypatch.delenv(canal.VARIABLE)
    assert canal.entrada() == canal.ENTRADA_BASE
    assert canal.entrada("papasia") == canal.ENTRADA_BASE / "papasia"


def test_los_guiones_de_papasia_van_siempre_a_su_carpeta():
    from dato_mata_gato_bot import instruccion_papasia, papasia_guion

    assert papasia_guion.ANDROID_IN == canal.ENTRADA_BASE / "papasia"
    assert papasia_guion.BITACORA.parent == canal.ENTRADA_BASE / "papasia" / "fabrica"
    texto = instruccion_papasia.instruccion(1, None, "")
    assert str(canal.ENTRADA_BASE / "papasia") + r"\<slug>\guion.json" in texto
    assert r"C:\Android_in\<slug>" not in texto


def test_el_vigilante_ve_los_lotes_de_todos_los_canales(tmp_path, monkeypatch):
    import json

    from dato_mata_gato_bot import fabrica

    monkeypatch.delenv(canal.VARIABLE, raising=False)
    monkeypatch.setattr(canal, "ENTRADA_BASE", tmp_path)
    monkeypatch.setattr(fabrica, "RAIZ", tmp_path / "fabrica")

    def lote(raiz, nombre, formato, terminado=False):
        (raiz / nombre).mkdir(parents=True)
        (raiz / nombre / "estado.json").write_text(json.dumps(
            {"lote": nombre, "formato": formato, "terminado": terminado, "videos": {}}), encoding="utf-8")

    lote(tmp_path / "fabrica", "todos-1", "todos")
    lote(tmp_path / "fabrica", "todos-0", "todos", terminado=True)
    lote(tmp_path / "papasia" / "fabrica", "papasia-1", "papasia")
    activas = {e["lote"]: e["canal"] for e in fabrica.activas_de_todos()}
    assert activas == {"todos-1": "", "papasia-1": "papasia"}


def test_la_migracion_mueve_solo_lo_de_papasia(tmp_path):
    import importlib.util
    import json

    ruta = canal.RAIZ_BOT / "tools" / "migrar_carpetas_papasia.py"
    spec = importlib.util.spec_from_file_location("migrar_carpetas_papasia", ruta)
    migrar = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migrar)

    base, destino = tmp_path, tmp_path / "papasia"
    for d in ("guion-papasia-hipo", "guion-viral-x", "lotes/papasia-1", "lotes/todos-1",
              "fabrica/papasia-1", "fabrica/todos-1"):
        (base / d).mkdir(parents=True)
    (base / "fabrica" / "papasia_tokens.csv").write_text("fecha\n", encoding="utf-8")
    estado = base / "fabrica" / "papasia-1" / "estado.json"
    estado.write_text(json.dumps({"lote": "papasia-1", "formato": "papasia", "terminado": True,
                                  "carpeta_videos": str(base / "lotes" / "papasia-1")}), encoding="utf-8")

    pares = migrar.movimientos(base, destino)
    assert sorted(a.name for a, _ in pares) == ["guion-papasia-hipo", "papasia-1", "papasia-1",
                                                "papasia_tokens.csv"]
    assert migrar.problemas(pares) == []
    estado.write_text(json.dumps({"lote": "papasia-1", "formato": "papasia", "terminado": False}),
                      encoding="utf-8")
    assert "no ha terminado" in migrar.problemas(pares)[0]
