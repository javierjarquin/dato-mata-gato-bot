"""Una toma generada con IA NO está "sin medio".

El 20/09/2026, al apagar el stock genérico, este chequeo quedó viejo: marcaba
como sin medio toda toma que no encontrara archivo, sin mirar si la imagen
existía en disco. Como ahora esas tomas se generan con IA, un video entero
salía con TODAS sus tomas marcadas y el pipeline entraba en sus 10 reintentos
de ~17 minutos. Costó 24 reintentos inútiles antes de notarlo -- casi tres
horas por video, y ninguno arreglaba nada porque no había nada roto.
"""

import json

from dato_mata_gato_bot import media_check


def _proyecto(tmp_path, slug="guion-x", manifest=None):
    p = tmp_path / slug
    (p / "media").mkdir(parents=True)
    (p / "images").mkdir()
    (p / "media" / "manifest.json").write_text(
        json.dumps(manifest or {}), encoding="utf-8")
    return p


def test_una_toma_generada_con_ia_no_se_marca(tmp_path):
    proyecto = _proyecto(tmp_path, manifest={"p00": {"chosen": None, "query": "x"}})
    (proyecto / "images" / "p00.png").write_bytes(b"imagen generada")
    assert media_check.check_manifest(tmp_path, "guion-x") == []


def test_una_toma_realmente_sin_medio_si_se_marca(tmp_path):
    """El chequeo tiene que seguir sirviendo para lo que fue hecho."""
    _proyecto(tmp_path, manifest={"p00": {"chosen": None, "query": "x"}})
    marcadas = media_check.check_manifest(tmp_path, "guion-x")
    assert [m.reason for m in marcadas] == ["sin_medio"]


def test_reconoce_el_video_ademas_de_la_imagen(tmp_path):
    proyecto = _proyecto(tmp_path, manifest={"p03_2": {"chosen": None, "query": "x"}})
    (proyecto / "media" / "p03").mkdir(parents=True)
    (proyecto / "media" / "p03" / "p03_2.mp4").write_bytes(b"clip")
    assert media_check.check_manifest(tmp_path, "guion-x") == []


def test_el_pais_incoherente_se_sigue_marcando(tmp_path):
    """Lo que sí es un problema real no debe dejar de detectarse."""
    _proyecto(tmp_path, manifest={
        "p00": {"chosen": {"title": "Police station in Taiwan"}, "query": "x"}})
    marcadas = media_check.check_manifest(tmp_path, "guion-x")
    assert [m.reason for m in marcadas] == ["pais_incoherente"]
