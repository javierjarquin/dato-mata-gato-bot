import time

from dato_mata_gato_bot import generated_videos


def test_sin_carpeta_devuelve_lista_vacia(tmp_path, monkeypatch):
    monkeypatch.setattr(generated_videos, "ANDROID_OUT", tmp_path / "no_existe")
    assert generated_videos.list_generated_videos() == []


def test_lista_ordenada_mas_reciente_primero(tmp_path, monkeypatch):
    monkeypatch.setattr(generated_videos, "ANDROID_OUT", tmp_path)

    viejo = tmp_path / "viejo.mp4"
    viejo.write_bytes(b"x" * 1024 * 1024)
    time.sleep(0.05)
    nuevo = tmp_path / "nuevo.mp4"
    nuevo.write_bytes(b"x" * 2 * 1024 * 1024)

    videos = generated_videos.list_generated_videos()
    assert [v.slug for v in videos] == ["nuevo", "viejo"]
    assert videos[0].tamano_mb == 2.0


def test_format_video_list_vacio():
    assert "Todavía no hay" in generated_videos.format_video_list([])


def test_format_video_list_con_datos(tmp_path, monkeypatch):
    monkeypatch.setattr(generated_videos, "ANDROID_OUT", tmp_path)
    (tmp_path / "elchalequero.mp4").write_bytes(b"x" * 1024 * 1024)

    texto = generated_videos.format_video_list(generated_videos.list_generated_videos())
    assert "1 video(s)" in texto
    assert "elchalequero" in texto
