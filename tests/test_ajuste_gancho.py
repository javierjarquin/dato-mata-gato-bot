import json

from dato_mata_gato_bot import pipeline


def _preparar(tmp_path, monkeypatch, slug="guion-caso"):
    monkeypatch.setattr(pipeline, "ANDROID_IN", tmp_path / "in")
    monkeypatch.setattr(pipeline, "TTS_KOKORO_PROJECTS", tmp_path / "tts")
    (tmp_path / "in" / slug).mkdir(parents=True)
    (tmp_path / "in" / slug / "guion.json").write_text(json.dumps(
        {"planos": [{"id": "p00", "narracion": "Gancho"}, {"id": "p01", "narracion": "Resto"}]}),
        encoding="utf-8")
    monkeypatch.setattr(pipeline, "motor_tts", lambda: "voicestudio")
    monkeypatch.setenv("VOICESTUDIO_VOICE_ID_CRIMEN", "cbbc2aa7")
    monkeypatch.setenv("VOICESTUDIO_GANCHO_VELOCIDAD", "1.08")
    monkeypatch.setenv("VOICESTUDIO_GANCHO_GUIDANCE", "3.0")


def _planos(tmp_path, slug="guion-caso"):
    return json.loads((tmp_path / "tts" / slug / "guion.json").read_text(encoding="utf-8"))["planos"]


def test_el_gancho_de_true_crime_lleva_el_ajuste_b(tmp_path, monkeypatch):
    _preparar(tmp_path, monkeypatch)
    pipeline._stage_guion_for_tts("guion-caso")
    planos = _planos(tmp_path)
    assert planos[0]["voz"] == {"velocidad": 1.08, "guidance": 3.0}
    assert "voz" not in planos[1]


def test_con_presentador_no_se_toca(tmp_path, monkeypatch):
    _preparar(tmp_path, monkeypatch)
    pipeline._stage_guion_for_tts("guion-caso", avatar=True)
    assert "voz" not in _planos(tmp_path)[0]


def test_sin_variables_queda_como_antes(tmp_path, monkeypatch):
    _preparar(tmp_path, monkeypatch)
    monkeypatch.delenv("VOICESTUDIO_GANCHO_VELOCIDAD")
    monkeypatch.delenv("VOICESTUDIO_GANCHO_GUIDANCE")
    pipeline._stage_guion_for_tts("guion-caso")
    assert "voz" not in _planos(tmp_path)[0]
