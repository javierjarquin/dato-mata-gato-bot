import json

from dato_mata_gato_bot import media_check


def _write_manifest(projects_dir, slug, data):
    d = projects_dir / slug / "media"
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps(data), encoding="utf-8")


def test_sin_manifest_no_flagea_nada(tmp_path):
    assert media_check.check_manifest(tmp_path, "inexistente") == []


def test_flagea_pais_incoherente(tmp_path):
    _write_manifest(tmp_path, "caso1", {
        "p01_1": {"chosen": {"title": "A polished courtroom interior in Wroclaw, Poland"}},
        "p01_2": {"chosen": {"title": "Aerial view of Mexico City highways at dawn"}},
    })
    flagged = media_check.check_manifest(tmp_path, "caso1")
    assert len(flagged) == 1
    assert flagged[0].shot_id == "p01_1"
    assert flagged[0].reason == "pais_incoherente"


def test_flagea_sin_medio(tmp_path):
    _write_manifest(tmp_path, "caso2", {
        "p02_1": {"chosen": None},
    })
    flagged = media_check.check_manifest(tmp_path, "caso2")
    assert flagged[0].reason == "sin_medio"


def test_no_confunde_new_mexico_con_mexico(tmp_path):
    _write_manifest(tmp_path, "caso3", {
        "p01_1": {"chosen": {"title": "Sunset in Mexico City downtown"}},
        "p01_2": {"chosen": {"title": "Desert landscape in New Mexico, USA"}},
    })
    flagged = media_check.check_manifest(tmp_path, "caso3")
    assert len(flagged) == 1
    assert flagged[0].shot_id == "p01_2"
