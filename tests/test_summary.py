import json

from dato_mata_gato_bot import summary


def _guion(planos):
    return {"titulo": "Caso de prueba", "planos": planos}


def test_sin_guion_avisa(tmp_path, monkeypatch):
    monkeypatch.setattr(summary, "ANDROID_IN", tmp_path / "in")
    monkeypatch.setattr(summary, "NARRATOR_PROJECTS", tmp_path / "narrator")

    assert "No encontré" in summary.build_summary("inexistente")


def test_resumen_basico(tmp_path, monkeypatch):
    android_in = tmp_path / "in"
    monkeypatch.setattr(summary, "ANDROID_IN", android_in)
    monkeypatch.setattr(summary, "NARRATOR_PROJECTS", tmp_path / "narrator")

    slug_dir = android_in / "caso1"
    slug_dir.mkdir(parents=True)
    guion = _guion([
        {"id": "p00", "seccion": "apertura", "duracion_seg": 5, "narracion": "Aquí no contamos historias."},
        {"id": "p01", "seccion": "hook", "duracion_seg": 20, "narracion": "x" * 200},
    ])
    (slug_dir / "guion.json").write_text(json.dumps(guion), encoding="utf-8")

    texto = summary.build_summary("caso1")
    assert "Caso de prueba" in texto
    assert "2 planos" in texto
    assert "p00 (apertura, 5s)" in texto
    assert "p01 (hook, 20s)" in texto
    assert "…" in texto  # narracion larga truncada


def test_resumen_incluye_estado_de_medios_si_hay_manifest(tmp_path, monkeypatch):
    android_in = tmp_path / "in"
    narrator = tmp_path / "narrator"
    monkeypatch.setattr(summary, "ANDROID_IN", android_in)
    monkeypatch.setattr(summary, "NARRATOR_PROJECTS", narrator)

    proj_dir = narrator / "caso2"
    proj_dir.mkdir(parents=True)
    guion = _guion([{"id": "p01", "seccion": "hook", "duracion_seg": 10, "narracion": "algo"}])
    (proj_dir / "guion.json").write_text(json.dumps(guion), encoding="utf-8")

    media_dir = proj_dir / "media"
    media_dir.mkdir()
    manifest = {
        "p01_1": {"chosen": {"title": "algo"}},
        "p01_2": {"chosen": None},
    }
    (media_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    texto = summary.build_summary("caso2")
    assert "[medios: 1/2]" in texto


def test_load_guion_dict_lee_y_find_plano_es_case_insensitive(tmp_path, monkeypatch):
    android_in = tmp_path / "in"
    monkeypatch.setattr(summary, "ANDROID_IN", android_in)
    monkeypatch.setattr(summary, "NARRATOR_PROJECTS", tmp_path / "narrator")

    slug_dir = android_in / "caso3"
    slug_dir.mkdir(parents=True)
    guion = _guion([{"id": "p02", "seccion": "hook", "duracion_seg": 10, "narracion": "algo"}])
    (slug_dir / "guion.json").write_text(json.dumps(guion), encoding="utf-8")

    cargado = summary.load_guion_dict("caso3")
    assert cargado["titulo"] == "Caso de prueba"

    plano = summary.find_plano(cargado, "P02")
    assert plano is not None
    assert plano["id"] == "p02"

    assert summary.find_plano(cargado, "p99") is None


def test_load_guion_dict_inexistente_devuelve_none(tmp_path, monkeypatch):
    monkeypatch.setattr(summary, "ANDROID_IN", tmp_path / "in")
    monkeypatch.setattr(summary, "NARRATOR_PROJECTS", tmp_path / "narrator")
    assert summary.load_guion_dict("no-existe") is None
