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


def test_no_flagea_sin_medio_si_otra_toma_del_mismo_plano_resolvio(tmp_path):
    # Caso real: p03 con 5 tomas, la 5 sin medio -- las otras 4 ya cubren la
    # duración del plano (generate_plano_images.py las estira), así que no
    # hace falta reintento ni escalar a Claude por la que falta.
    _write_manifest(tmp_path, "caso4", {
        "p03_1": {"chosen": {"title": "Modern apartment building facade"}},
        "p03_2": {"chosen": {"title": "Apartment towers in urban landscape"}},
        "p03_3": {"chosen": {"title": "Residential complex overcast day"}},
        "p03_4": {"chosen": {"title": "Aerial view of apartment complex"}},
        "p03_5": {"chosen": None},
    })
    assert media_check.check_manifest(tmp_path, "caso4") == []


def test_flagea_sin_medio_si_ninguna_toma_del_plano_resolvio(tmp_path):
    _write_manifest(tmp_path, "caso5", {
        "p09_1": {"chosen": None},
        "p09_2": {"chosen": None},
    })
    flagged = media_check.check_manifest(tmp_path, "caso5")
    assert {f.shot_id for f in flagged} == {"p09_1", "p09_2"}
    assert all(f.reason == "sin_medio" for f in flagged)
