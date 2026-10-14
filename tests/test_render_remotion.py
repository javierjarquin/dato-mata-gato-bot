import json

from dato_mata_gato_bot import pipeline


def _guion(tmp_path, monkeypatch, slug, extra=None):
    monkeypatch.setattr(pipeline, "ANDROID_IN", tmp_path)
    monkeypatch.setattr(pipeline, "motor_tts", lambda: "voicestudio")
    monkeypatch.setenv("VOICESTUDIO_VOICE_ID_CRIMEN", "fish")
    monkeypatch.delenv("VOICESTUDIO_VOICE_ID_CRIMEN_JAVIER", raising=False)
    (tmp_path / slug).mkdir(exist_ok=True)
    (tmp_path / slug / "guion.json").write_text(json.dumps({"planos": [], **(extra or {})}), encoding="utf-8")


def test_por_defecto_sigue_ffmpeg(tmp_path, monkeypatch):
    _guion(tmp_path, monkeypatch, "guion-a")
    monkeypatch.delenv("RENDER_VIDEO", raising=False)
    assert pipeline.modo_render("guion-a") == "ffmpeg"


def test_remotion_solo_para_true_crime_sin_presentador(tmp_path, monkeypatch):
    _guion(tmp_path, monkeypatch, "guion-a")
    _guion(tmp_path, monkeypatch, "trivia-x")
    monkeypatch.setenv("RENDER_VIDEO", "remotion")
    assert pipeline.modo_render("guion-a") == "remotion"
    assert pipeline.modo_render("guion-a", avatar=True) == "ffmpeg"
    assert pipeline.modo_render("trivia-x") == "ffmpeg"


def test_mitad_alterna_estable_y_el_guion_manda(tmp_path, monkeypatch):
    monkeypatch.setenv("RENDER_VIDEO", "mitad")
    slugs = [f"guion-caso-{i}" for i in range(40)]
    for s in slugs:
        _guion(tmp_path, monkeypatch, s)
    modos = [pipeline.modo_render(s) for s in slugs]
    assert 10 < modos.count("remotion") < 30
    assert modos == [pipeline.modo_render(s) for s in slugs]
    _guion(tmp_path, monkeypatch, "guion-fijo", {"render": "ffmpeg"})
    assert pipeline.modo_render("guion-fijo") == "ffmpeg"


def test_si_remotion_falla_queda_el_final_de_ffmpeg(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "NARRATOR_PROJECTS", tmp_path / "proj")
    monkeypatch.setattr(pipeline, "REMOTION_DIR", tmp_path / "rem")
    (tmp_path / "proj" / "guion-a").mkdir(parents=True)
    (tmp_path / "proj" / "guion-a" / "final.mp4").write_bytes(b"ffmpeg")

    class Proc:
        returncode, stdout, stderr = 1, "", "chrome no arrancó"
    monkeypatch.setattr(pipeline.subprocess, "run", lambda *a, **k: Proc())
    ok, detalle = pipeline.render_remotion("guion-a")
    assert not ok and "chrome" in detalle
    assert (tmp_path / "proj" / "guion-a" / "final.mp4").read_bytes() == b"ffmpeg"


def test_si_remotion_sale_bien_reemplaza_y_guarda_respaldo(tmp_path, monkeypatch):
    monkeypatch.setenv("RENDER_PLUS", "0")
    monkeypatch.setattr(pipeline, "NARRATOR_PROJECTS", tmp_path / "proj")
    monkeypatch.setattr(pipeline, "REMOTION_DIR", tmp_path / "rem")
    (tmp_path / "proj" / "guion-a").mkdir(parents=True)
    (tmp_path / "proj" / "guion-a" / "final.mp4").write_bytes(b"ffmpeg")
    (tmp_path / "rem" / "out").mkdir(parents=True)

    class Proc:
        returncode, stdout, stderr = 0, "render ok", ""

    def correr(*a, **k):
        (tmp_path / "rem" / "out" / "guion-a.mp4").write_bytes(b"r" * 200_000)
        return Proc()
    monkeypatch.setattr(pipeline.subprocess, "run", correr)
    ok, _ = pipeline.render_remotion("guion-a")
    assert ok
    assert (tmp_path / "proj" / "guion-a" / "final.mp4").read_bytes()[:1] == b"r"
    assert (tmp_path / "proj" / "guion-a" / "final_ffmpeg.mp4").read_bytes() == b"ffmpeg"


def test_con_animaciones_usa_render_plus_y_devuelve_el_resumen(tmp_path, monkeypatch):
    monkeypatch.delenv("RENDER_PLUS", raising=False)
    monkeypatch.setattr(pipeline, "NARRATOR_PROJECTS", tmp_path / "proj")
    monkeypatch.setattr(pipeline, "REMOTION_DIR", tmp_path / "rem")
    (tmp_path / "proj" / "guion-a").mkdir(parents=True)
    (tmp_path / "rem" / "out").mkdir(parents=True)
    visto = {}

    class Proc:
        returncode, stderr = 0, ""
        stdout = "props: ...\nplus: 6 fichas animadas, 12 palabras en rojo, 2 destellos, mapa=sí\nrender: ok"

    def correr(args, **k):
        visto["script"] = args[1]
        (tmp_path / "rem" / "out" / "guion-a_plus.mp4").write_bytes(b"r" * 200_000)
        return Proc()
    monkeypatch.setattr(pipeline.subprocess, "run", correr)
    monkeypatch.setattr(pipeline, "_juntar_multimedia", lambda slug: "")
    monkeypatch.setattr(pipeline, "_portadas", lambda slug, final: "portada A (la nota) en el primer cuadro")
    ok, detalle = pipeline.render_remotion("guion-a")
    assert ok and visto["script"].endswith("render_plus.py")
    assert detalle.startswith("plus: 6 fichas") and "portada A (la nota)" in detalle
    assert (tmp_path / "proj" / "guion-a" / "final.mp4").exists()


def test_portada_por_defecto_es_la_nota(monkeypatch):
    monkeypatch.delenv("PORTADA_VARIANTE", raising=False)
    assert {pipeline.variante_portada(f"guion-cancun-caso-{i}") for i in range(10)} == {"nota"}
    monkeypatch.setenv("PORTADA_VARIANTE", "dato")
    assert pipeline.variante_portada("guion-x") == "dato"


def test_archivar_copia_las_portadas(tmp_path, monkeypatch):
    proyecto = tmp_path / "proj" / "guion-a"
    proyecto.mkdir(parents=True)
    (proyecto / "guion.json").write_text('{"titulo": "Playas públicas"}', encoding="utf-8")
    (proyecto / "final.mp4").write_bytes(b"v")
    (proyecto / "portada_nota.jpg").write_bytes(b"a")
    (proyecto / "portada_dato.jpg").write_bytes(b"b")
    monkeypatch.setattr(pipeline, "NARRATOR_PROJECTS", tmp_path / "proj")
    destino = pipeline._archivar_local("guion-a", proyecto / "final.mp4", tmp_path / "lote")
    assert destino.exists()
    assert (destino.with_name(f"{destino.stem}_portada_nota.jpg")).read_bytes() == b"a"
    assert (destino.with_name(f"{destino.stem}_portada_dato.jpg")).read_bytes() == b"b"
