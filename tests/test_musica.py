"""Música de fondo propia, rotando (22/11/2026)."""
import json
import shutil
import subprocess

import pytest

from dato_mata_gato_bot import musica


@pytest.fixture
def pistas(tmp_path, monkeypatch):
    monkeypatch.setattr(musica, "MUSICA_DIR", tmp_path / "musica")
    for c in ("dmg", "papasia"):
        (tmp_path / "musica" / c).mkdir(parents=True)
        for i in range(1, 6):
            (tmp_path / "musica" / c / f"{i}_{c}.m4a").write_bytes(b"x")
    return tmp_path / "musica"


def test_una_distinta_en_cada_video_y_vuelve_a_empezar(pistas):
    """Javier: "aplicar todas, uno en cada video, así damos percepción de variación"."""
    vistas = [musica.siguiente("").stem for _ in range(6)]
    assert vistas == ["1_dmg", "2_dmg", "3_dmg", "4_dmg", "5_dmg", "1_dmg"]


def test_cada_canal_lleva_su_turno(pistas):
    musica.siguiente("")
    musica.siguiente("")
    assert musica.siguiente("papasia").stem == "1_papasia"
    assert musica.siguiente("").stem == "3_dmg"


def test_apagada_o_sin_musica_en_el_guion(pistas, tmp_path, monkeypatch):
    video = tmp_path / "final.mp4"
    video.write_bytes(b"v")
    monkeypatch.setenv("MUSICA", "0")
    assert musica.poner({}, "", video) == ""
    monkeypatch.setenv("MUSICA", "1")
    assert musica.poner({"plus": {"sin_musica": True}}, "", video) == ""
    assert not (pistas / "dmg" / "turno.json").exists()


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="sin ffmpeg")
def test_mezcla_de_verdad_y_no_se_encima_dos_veces(tmp_path, monkeypatch):
    monkeypatch.setenv("MUSICA", "1")
    monkeypatch.setattr(musica, "MUSICA_DIR", tmp_path / "musica")
    (tmp_path / "musica" / "dmg").mkdir(parents=True)
    pista = tmp_path / "musica" / "dmg" / "1_prueba.m4a"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=f=330:d=3", "-c:a", "aac", str(pista)], check=True)
    video = tmp_path / "final.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=s=320x240:d=5", "-f", "lavfi",
                    "-i", "sine=f=220:d=5", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-b:v", "2M", "-shortest", str(video)], check=True)
    assert musica.poner({}, "", video) == "música: 1_prueba"
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                str(video)], capture_output=True, text=True).stdout)
    assert 4.8 < dur < 5.3  # la pista (3 s, en bucle) no alarga ni corta el video
    marca = json.loads((tmp_path / "musica.json").read_text(encoding="utf-8"))
    assert marca["pista"] == "1_prueba"
    # Un segundo intento con el mismo archivo no le pone otra encima ni avanza el turno.
    assert musica.poner({}, "", video) == "música: 1_prueba"
    assert json.loads((tmp_path / "musica" / "dmg" / "turno.json").read_text())["siguiente"] == 0
