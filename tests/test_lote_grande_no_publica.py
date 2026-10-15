"""Un lote grande NO se publica. Eso tiene que estar fijado por un test.

Son treinta videos sin revisar: si se subieran solos a Drive entrarían al
calendario de publicación del canal, que es exactamente lo contrario de lo que
este modo es. El costo de equivocarse acá es publicar material sin verificar.
"""

import json

import pytest

from dato_mata_gato_bot import pipeline


def _proyecto(tmp_path, slug="guion-x", titulo="Caso Durazno"):
    p = tmp_path / "proyectos" / slug
    p.mkdir(parents=True)
    (p / "guion.json").write_text(json.dumps({"titulo": titulo}), encoding="utf-8")
    (p / "final.mp4").write_bytes(b"video")
    return p


def test_con_destino_local_no_sube_a_drive(tmp_path, monkeypatch):
    _proyecto(tmp_path)
    monkeypatch.setattr(pipeline, "NARRATOR_PROJECTS", tmp_path / "proyectos")

    def _no_deberia(*a, **k):
        raise AssertionError("el lote grande NO debe subir a Drive")

    monkeypatch.setattr(pipeline, "_upload_to_drive", _no_deberia)
    monkeypatch.setattr(pipeline, "_stage_guion_for_tts", lambda s, avatar=False: None)
    monkeypatch.setattr(pipeline, "_kick_off_a1111_if_needed", lambda: None)
    monkeypatch.setattr(pipeline, "_generate_audio", lambda s, v, avatar=False: (True, ""))
    monkeypatch.setattr(pipeline, "_setup_narrator_project", lambda s: None)
    monkeypatch.setattr(pipeline, "_run_narrator_generate",
                        lambda s, a=False, sin_ia=False: (True, ""))
    monkeypatch.setattr(pipeline.media_check, "check_manifest", lambda p, s: [])
    monkeypatch.setattr(pipeline, "ANDROID_IN", tmp_path / "entrada")
    (tmp_path / "entrada" / "guion-x").mkdir(parents=True)
    (tmp_path / "entrada" / "guion-x" / "guion.json").write_text("{}", encoding="utf-8")

    carpeta = tmp_path / "lotes" / "2026-09-18"
    res = pipeline.run("guion-x", "am_adam", None, False, None, carpeta)

    assert res.ok, res.mensaje
    assert (carpeta / "casodurazno.mp4").exists()
    assert str(carpeta) in res.mensaje


def test_sin_destino_local_sigue_subiendo_a_drive(tmp_path, monkeypatch):
    """El flujo normal no cambia: /generarlote sigue publicando."""
    _proyecto(tmp_path)
    monkeypatch.setattr(pipeline, "NARRATOR_PROJECTS", tmp_path / "proyectos")
    llamadas = []
    monkeypatch.setattr(pipeline, "_upload_to_drive",
                        lambda s: llamadas.append(s) or "link")
    monkeypatch.setattr(pipeline, "_stage_guion_for_tts", lambda s, avatar=False: None)
    monkeypatch.setattr(pipeline, "_kick_off_a1111_if_needed", lambda: None)
    monkeypatch.setattr(pipeline, "_generate_audio", lambda s, v, avatar=False: (True, ""))
    monkeypatch.setattr(pipeline, "_setup_narrator_project", lambda s: None)
    monkeypatch.setattr(pipeline, "_run_narrator_generate",
                        lambda s, a=False, sin_ia=False: (True, ""))
    monkeypatch.setattr(pipeline.media_check, "check_manifest", lambda p, s: [])
    monkeypatch.setattr(pipeline, "ANDROID_IN", tmp_path / "entrada")
    (tmp_path / "entrada" / "guion-x").mkdir(parents=True)
    (tmp_path / "entrada" / "guion-x" / "guion.json").write_text("{}", encoding="utf-8")

    res = pipeline.run("guion-x", "am_adam")
    assert res.ok
    assert llamadas == ["guion-x"]
