from dato_mata_gato_bot import generated_videos, publish_schedule


def test_sin_entradas_devuelve_lista_vacia(tmp_path, monkeypatch):
    monkeypatch.setattr(publish_schedule, "SCHEDULE_PATH", tmp_path / "publish_schedule.json")
    assert generated_videos.list_generated_videos() == []


def test_lista_ordenada_por_fecha_de_publicacion(tmp_path, monkeypatch):
    monkeypatch.setattr(publish_schedule, "SCHEDULE_PATH", tmp_path / "publish_schedule.json")
    publish_schedule.assign_date("primero")  # 25082026
    publish_schedule.assign_date("segundo")  # 26082026
    publish_schedule.record_upload("primero", "criptografia_25082026.mp4", "https://drive/1")

    videos = generated_videos.list_generated_videos()

    assert [v.slug for v in videos] == ["primero", "segundo"]
    assert videos[0].subido is True
    assert videos[0].nombre_archivo == "criptografia_25082026.mp4"
    assert videos[1].subido is False
    assert videos[1].nombre_archivo is None


def test_format_video_list_vacio():
    assert "Todavía no hay" in generated_videos.format_video_list([])


def test_format_video_list_con_datos(tmp_path, monkeypatch):
    monkeypatch.setattr(publish_schedule, "SCHEDULE_PATH", tmp_path / "publish_schedule.json")
    publish_schedule.assign_date("elchalequero")
    publish_schedule.record_upload("elchalequero", "elchalequero_25082026.mp4", "https://drive/x")

    texto = generated_videos.format_video_list(generated_videos.list_generated_videos())
    assert "1 video(s)" in texto
    assert "elchalequero_25082026.mp4" in texto
    assert "25/08/2026" in texto
    assert "subido" in texto
