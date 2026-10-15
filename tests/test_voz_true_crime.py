"""Los true crime van con su propia voz; el resto sigue con la de Javier.

Elegida el 28/09/2026 entre tres voces en videos completos de Tierra Blanca.
"""

import pytest

from dato_mata_gato_bot import pipeline


@pytest.fixture
def entorno(monkeypatch):
    monkeypatch.setenv("TTS_ENGINE", "voicestudio")
    monkeypatch.setenv("VOICESTUDIO_VOICE_ID", "95e2570b")
    monkeypatch.setenv("VOICESTUDIO_VOICE_ID_CRIMEN", "81f929e4")
    monkeypatch.setenv("VOICESTUDIO_NUM_STEP_CRIMEN", "32")
    capturado = {}

    def _fake_run(args, cwd=None, env=None, timeout=None):
        capturado["env"] = env
        return type("P", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(pipeline, "_run", _fake_run)
    return capturado


def test_un_true_crime_usa_la_voz_de_crimen_con_calidad_32(entorno):
    pipeline._generate_audio("guion-tierra-blanca-veracruz", voz="am_adam")
    assert entorno["env"]["VOICESTUDIO_VOICE_ID"] == "81f929e4"
    assert entorno["env"]["VOICESTUDIO_NUM_STEP"] == "32"
    # Que no se coma frases: tts-kokoro verifica cada plano con Whisper.
    assert entorno["env"]["VOICESTUDIO_VERIFICAR"] == "1"
    assert "VOICESTUDIO_RECORTAR_COLAS" not in entorno["env"]


@pytest.mark.parametrize("slug", ["trivia-hongos-01", "mito-aluxes"])
def test_trivia_y_mitos_siguen_con_la_voz_de_siempre(entorno, slug):
    pipeline._generate_audio(slug, voz="am_adam")
    assert entorno["env"] is None  # hereda el entorno: VOICESTUDIO_VOICE_ID


def test_con_presentador_no_se_cambia_la_voz(entorno):
    """Es la cara de Javier moviendo los labios: con otra voz se ve doblado."""
    pipeline._generate_audio("guion-tierra-blanca-veracruz", voz="am_adam", avatar=True)
    assert entorno["env"] is None


def test_sin_la_variable_todo_queda_como_antes(entorno, monkeypatch):
    monkeypatch.delenv("VOICESTUDIO_VOICE_ID_CRIMEN")
    pipeline._generate_audio("guion-tierra-blanca-veracruz", voz="am_adam")
    assert entorno["env"] is None


def _env_del_narrador(monkeypatch, slug, avatar=False):
    capturado = {}

    def _fake_run(args, cwd=None, env=None, timeout=None):
        capturado["env"] = env
        return type("P", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(pipeline, "_run", _fake_run)
    pipeline._run_narrator_generate(slug, avatar)
    return capturado["env"]


def test_con_la_voz_de_true_crime_el_gato_no_habla_y_va_el_logo(entorno, monkeypatch):
    env = _env_del_narrador(monkeypatch, "guion-tierra-blanca-veracruz")
    assert env["NARR_NARRACION"] == "voz"
    assert "NARR_MASCOTA_PATH" not in env
    assert env["NARR_LOGO_ESQUINA"] == pipeline.EMBLEMA_ESQUINA


@pytest.mark.parametrize("slug", ["trivia-hongos-01", "mito-aluxes"])
def test_trivia_y_mitos_siguen_con_el_gato(entorno, monkeypatch, slug):
    env = _env_del_narrador(monkeypatch, slug)
    assert env["NARR_NARRACION"] == "mascota"
    assert "NARR_LOGO_ESQUINA" not in env


def test_el_emblema_existe():
    from pathlib import Path
    assert Path(pipeline.EMBLEMA_ESQUINA).exists()


def test_run_le_pasa_el_avatar_al_audio():
    """Sin esto, un video con presentador saldría con la voz de crimen."""
    import inspect
    fuente = inspect.getsource(pipeline.run)
    assert "_generate_audio(slug, voz, avatar=avatar)" in fuente
