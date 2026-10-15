import json

from dato_mata_gato_bot import lote_grande, pipeline


def _guiones(tmp_path, monkeypatch, slugs):
    monkeypatch.setattr(pipeline, "ANDROID_IN", tmp_path)
    monkeypatch.setattr(pipeline, "motor_tts", lambda: "voicestudio")
    monkeypatch.setenv("VOICESTUDIO_VOICE_ID_CRIMEN", "fish")
    monkeypatch.setenv("VOICESTUDIO_VOICE_ID_CRIMEN_JAVIER", "javi")
    for s in slugs:
        (tmp_path / s).mkdir()
        (tmp_path / s / "guion.json").write_text(json.dumps({"planos": []}), encoding="utf-8")


def _plan(tmp_path, tareas):
    return lote_grande.Plan(carpeta=tmp_path, tareas=tareas)


def test_alterna_una_y_una_y_lo_escribe_en_el_guion(tmp_path, monkeypatch):
    slugs = ["guion-a", "guion-b", "guion-c", "guion-d"]
    _guiones(tmp_path, monkeypatch, slugs)
    lote_grande.repartir_voces(_plan(tmp_path, [(s, None) for s in slugs]))
    voces = [pipeline.voz_narrador(s) for s in slugs]
    assert voces == ["fish3", "javier", "fish3", "javier"]
    assert pipeline.voz_de_true_crime("guion-b")["VOICESTUDIO_VOICE_ID"] == "javi"
    assert pipeline.voz_de_true_crime("guion-a")["VOICESTUDIO_VOICE_ID"] == "fish"


def test_retomar_no_cambia_la_voz_ya_asignada(tmp_path, monkeypatch):
    slugs = ["guion-a", "guion-b"]
    _guiones(tmp_path, monkeypatch, slugs)
    lote_grande.repartir_voces(_plan(tmp_path, [(s, None) for s in slugs]))
    # Retomado sin el primero: el segundo conserva su voz.
    lote_grande.repartir_voces(_plan(tmp_path, [("guion-b", None)]))
    assert pipeline.voz_narrador("guion-b") == "javier"


def test_presentador_y_trivia_no_entran_en_el_reparto(tmp_path, monkeypatch):
    slugs = ["guion-a", "guion-b", "trivia-x"]
    _guiones(tmp_path, monkeypatch, slugs)
    lote_grande.repartir_voces(_plan(tmp_path, [("guion-a", 0), ("guion-b", None), ("trivia-x", None)]))
    assert "voz_narrador" not in json.loads((tmp_path / "guion-a" / "guion.json").read_text())
    assert "voz_narrador" not in json.loads((tmp_path / "trivia-x" / "guion.json").read_text())
    assert pipeline.voz_narrador("guion-b") == "fish3"


def test_sin_perfil_de_javier_todo_es_fish3(tmp_path, monkeypatch):
    _guiones(tmp_path, monkeypatch, ["guion-a", "guion-b"])
    monkeypatch.delenv("VOICESTUDIO_VOICE_ID_CRIMEN_JAVIER")
    assert lote_grande.repartir_voces(_plan(tmp_path, [("guion-a", None), ("guion-b", None)])) == {}
    assert pipeline.voz_narrador("guion-b") == "fish3"


def _staged(tmp_path, monkeypatch, slug):
    monkeypatch.setattr(pipeline, "TTS_KOKORO_PROJECTS", tmp_path / "tts")
    (tmp_path / slug / "guion.json").write_text(json.dumps(
        {"voz_narrador": "javier" if slug.endswith("j") else "fish3",
         "planos": [{"id": "p00"}, {"id": "p01"}]}), encoding="utf-8")
    pipeline._stage_guion_for_tts(slug)
    return json.loads((tmp_path / "tts" / slug / "guion.json").read_text(encoding="utf-8"))["planos"]


def test_la_voz_de_javier_va_mas_rapida_en_todo_el_video(tmp_path, monkeypatch):
    _guiones(tmp_path, monkeypatch, ["guion-j", "guion-f"])
    monkeypatch.setenv("VOICESTUDIO_VELOCIDAD_JAVIER", "1.2")
    monkeypatch.setenv("VOICESTUDIO_GANCHO_VELOCIDAD", "1.08")
    monkeypatch.setenv("VOICESTUDIO_GANCHO_GUIDANCE", "3.0")
    j = _staged(tmp_path, monkeypatch, "guion-j")
    assert j[0]["voz"] == {"velocidad": 1.2, "guidance": 3.0}
    assert j[1]["voz"] == {"velocidad": 1.2}
    f = _staged(tmp_path, monkeypatch, "guion-f")
    assert f[0]["voz"] == {"velocidad": 1.08, "guidance": 3.0}
    assert "voz" not in f[1]
