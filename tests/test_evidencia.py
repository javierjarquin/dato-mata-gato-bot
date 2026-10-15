"""Evidencia real en vez de imágenes de IA (29/09/2026).

Nace del POC de Tierra Blanca: 16 de 18 true crime recientes tenían todas sus
imágenes hechas por IA. Estos tests fijan que un guion con evidencia no pase
nunca por la IA, y que una pieza caída no tire el video entero.
"""

import json

import pytest
from PIL import Image

from dato_mata_gato_bot import evidencia, pipeline


def _guion(tmp_path, evid, planos):
    base = tmp_path / "guion-x"
    base.mkdir(parents=True)
    (base / "guion.json").write_text(json.dumps({"evidencia": evid, "planos": planos}),
                                     encoding="utf-8")
    return base


def _ficha(pid, titulo="Dato"):
    return {"id": pid, "tipo": "ficha", "titulo": titulo, "renglones": ["uno"],
            "fuente": "Milenio"}


def test_la_ficha_deja_margen_para_el_zoom(tmp_path):
    """Con 40 px de margen el movimiento de cámara se comía el final de cada
    renglón (primer render de Tierra Blanca)."""
    ruta = evidencia.dibujar_ficha("Detenidos, sin sentencia", ["Un renglón largo " * 6],
                                   "Milenio", tmp_path / "f.jpg")
    im = Image.open(ruta).convert("L")
    assert im.size == (1080, 1920)
    borde = [im.getpixel((x, y)) for x in range(0, evidencia.MARGEN - 20)
             for y in range(0, 1920, 8)]
    assert max(borde) < 40, "hay texto dentro de la zona que recorta el zoom"


def test_prepara_y_asigna_las_piezas_de_cada_plano(tmp_path):
    base = _guion(tmp_path, [_ficha("e1"), _ficha("e2")], [
        {"id": "p00", "narracion": "a", "visual": {"evidencia": ["e1"]}},
        {"id": "p01", "narracion": "b", "visual": {"evidencia": ["e1", "e2"]}},
        {"id": "p02", "seccion": "identidad_cierre", "narracion": "c", "visual": {}},
    ])
    rep = evidencia.preparar("guion-x", entrada=tmp_path)
    manuales = sorted(p.name for p in (base / "imagenes_manuales").iterdir())
    assert manuales == [f"p0{i}_1_{n}.jpg" for i in (0, 1) for n in range(1, 6)]
    assert rep.piezas == {"e1": "ficha", "e2": "ficha"}
    guion = json.loads((base / "guion.json").read_text(encoding="utf-8"))
    # Piezas con texto: movimiento calmo, para que el zoom no se coma letras.
    assert guion["planos"][0]["visual"]["motion"] == "calm"
    # El cierre lo pone el bot con el cartel del canal.
    assert "motion" not in guion["planos"][2]["visual"]


def test_un_plano_sin_pieza_toma_prestada_la_del_anterior(tmp_path):
    """Repetir evidencia real es mejor que inventar."""
    base = _guion(tmp_path, [_ficha("e1"), {"id": "e9", "tipo": "raro"}], [
        {"id": "p00", "narracion": "a", "visual": {"evidencia": ["e1"]}},
        {"id": "p01", "narracion": "b", "visual": {"evidencia": ["e9"]}},
    ])
    rep = evidencia.preparar("guion-x", entrada=tmp_path)
    assert "e9" in rep.fallidas
    assert rep.planos_prestados == ["p01"]
    assert (base / "imagenes_manuales" / "p01_1_1.jpg").exists()


def test_las_fichas_solas_no_cuentan_como_evidencia_real(tmp_path):
    _guion(tmp_path, [_ficha("e1")], [{"id": "p00", "narracion": "a",
                                        "visual": {"evidencia": ["e1"]}}])
    assert evidencia.preparar("guion-x", entrada=tmp_path).reales == 0


def test_sin_evidencia_real_no_hay_video(tmp_path, monkeypatch):
    """Rellenarlo con IA es justo lo que esto vino a eliminar."""
    _guion(tmp_path, [_ficha("e1")], [{"id": "p00", "narracion": "a",
                                        "visual": {"evidencia": ["e1"]}}])
    monkeypatch.setattr(pipeline, "ANDROID_IN", tmp_path)
    monkeypatch.setattr(evidencia, "ENTRADA", tmp_path)
    monkeypatch.setattr(pipeline, "_generate_audio",
                        lambda *a, **k: pytest.fail("no debería llegar al audio"))
    r = pipeline.run("guion-x", "am_adam")
    assert not r.ok and not r.necesita_claude
    assert "No se genera con IA" in r.mensaje


def test_con_evidencia_el_narrador_corre_sin_ia(monkeypatch):
    capturado = {}

    def _fake_run(args, cwd=None, env=None, timeout=None):
        capturado["env"] = env
        return type("P", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(pipeline, "_run", _fake_run)
    pipeline._run_narrator_generate("guion-x", sin_ia=True)
    assert capturado["env"]["NARR_IMAGE_BACKEND"] == "none"
    assert capturado["env"]["NARR_VIDEO_FALLBACK_MAX_PLANOS"] == "0"
    pipeline._run_narrator_generate("guion-x")
    assert "NARR_IMAGE_BACKEND" not in capturado["env"] or \
        capturado["env"]["NARR_IMAGE_BACKEND"] != "none"


def test_un_guion_viejo_sin_evidencia_sigue_como_antes():
    assert not evidencia.tiene_evidencia({"planos": []})
    assert evidencia.tiene_evidencia({"evidencia": [{"id": "e1"}]})


def test_nombres_dudosos_marca_lo_que_no_se_oyo(tmp_path, monkeypatch):
    """En Tierra Blanca la voz se saltó "Tlalixcoyan" entero."""
    (tmp_path / "entrada" / "guion-x").mkdir(parents=True)
    (tmp_path / "entrada" / "guion-x" / "guion.json").write_text(json.dumps({"planos": [
        {"narracion": "Había restos en Tlalixcoyan, cerca de Veracruz."}]}), encoding="utf-8")
    (tmp_path / "proy" / "guion-x").mkdir(parents=True)
    oido = "Había restos en cerca de Veracruz".split()
    (tmp_path / "proy" / "guion-x" / "transcript.json").write_text(
        json.dumps({"words": [{"text": w} for w in oido]}), encoding="utf-8")
    monkeypatch.setattr(pipeline, "ANDROID_IN", tmp_path / "entrada")
    monkeypatch.setattr(pipeline, "NARRATOR_PROJECTS", tmp_path / "proy")
    assert pipeline.nombres_dudosos("guion-x") == ["Tlalixcoyan"]
