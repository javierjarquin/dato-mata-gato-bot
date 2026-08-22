from datetime import date

from dato_mata_gato_bot import publish_schedule


def test_primer_slug_toma_la_fecha_ancla(tmp_path, monkeypatch):
    monkeypatch.setattr(publish_schedule, "SCHEDULE_PATH", tmp_path / "publish_schedule.json")
    assert publish_schedule.assign_date("criptografia") == "25082026"


def test_segundo_slug_toma_el_dia_siguiente_al_ultimo(tmp_path, monkeypatch):
    monkeypatch.setattr(publish_schedule, "SCHEDULE_PATH", tmp_path / "publish_schedule.json")
    publish_schedule.assign_date("primero")
    assert publish_schedule.assign_date("segundo") == "26082026"


def test_mismo_slug_es_idempotente_no_avanza_la_fecha(tmp_path, monkeypatch):
    monkeypatch.setattr(publish_schedule, "SCHEDULE_PATH", tmp_path / "publish_schedule.json")
    primera = publish_schedule.assign_date("elchalequero")
    publish_schedule.assign_date("otro")  # consume la siguiente
    # Reintento del primer slug: NO debe pisar su fecha ya asignada.
    assert publish_schedule.assign_date("elchalequero") == primera == "25082026"


def test_record_upload_guarda_nombre_y_link(tmp_path, monkeypatch):
    monkeypatch.setattr(publish_schedule, "SCHEDULE_PATH", tmp_path / "publish_schedule.json")
    publish_schedule.assign_date("caso1")
    publish_schedule.record_upload("caso1", "criptografia_25082026.mp4", "https://drive.google.com/x")

    entries = publish_schedule.all_entries()
    assert entries["caso1"]["nombre_archivo"] == "criptografia_25082026.mp4"
    assert entries["caso1"]["drive_link"] == "https://drive.google.com/x"
    assert entries["caso1"]["fecha"] == "25082026"


def test_parse_fecha() -> None:
    assert publish_schedule.parse_fecha("25082026") == date(2026, 8, 25)
