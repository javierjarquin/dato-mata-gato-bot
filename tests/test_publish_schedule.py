from datetime import date

from dato_mata_gato_bot import publish_schedule


def test_primer_slug_toma_la_fecha_ancla(tmp_path, monkeypatch):
    monkeypatch.setattr(publish_schedule, "SCHEDULE_PATH", tmp_path / "publish_schedule.json")
    assert publish_schedule.assign_date("criptografia") == "12092026"


def test_el_lote_entero_cae_el_mismo_dia(tmp_path, monkeypatch):
    # Modalidad de 5 por día: un lote completo comparte fecha, no ocupa 5 días.
    monkeypatch.setattr(publish_schedule, "SCHEDULE_PATH", tmp_path / "publish_schedule.json")
    fechas = [publish_schedule.assign_date(f"caso{i}") for i in range(publish_schedule.POR_DIA)]
    assert fechas == ["12092026"] * publish_schedule.POR_DIA


def test_el_sexto_pasa_al_dia_siguiente(tmp_path, monkeypatch):
    monkeypatch.setattr(publish_schedule, "SCHEDULE_PATH", tmp_path / "publish_schedule.json")
    for i in range(publish_schedule.POR_DIA):
        publish_schedule.assign_date(f"caso{i}")
    assert publish_schedule.assign_date("caso-extra") == "13092026"


def test_mismo_slug_es_idempotente_no_consume_otro_cupo(tmp_path, monkeypatch):
    monkeypatch.setattr(publish_schedule, "SCHEDULE_PATH", tmp_path / "publish_schedule.json")
    primera = publish_schedule.assign_date("elchalequero")
    for i in range(publish_schedule.POR_DIA + 2):
        publish_schedule.assign_date(f"otro{i}")
    assert publish_schedule.assign_date("elchalequero") == primera == "12092026"


def test_el_calendario_viejo_no_ocupa_cupo(tmp_path, monkeypatch):
    # Las entradas de la modalidad de uno-por-día (sin campo `modalidad`) ya se
    # publicaron. Si contaran para el cupo, un slug nuevo caería en los días
    # sueltos que dejaron, mezclando los dos calendarios.
    ruta = tmp_path / "publish_schedule.json"
    monkeypatch.setattr(publish_schedule, "SCHEDULE_PATH", ruta)
    ruta.write_text(
        '{"viejo-1": {"fecha": "12092026"}, "viejo-2": {"fecha": "13092026"}}',
        encoding="utf-8",
    )
    assert publish_schedule.assign_date("nuevo") == "12092026"


def test_las_entradas_nuevas_quedan_marcadas(tmp_path, monkeypatch):
    monkeypatch.setattr(publish_schedule, "SCHEDULE_PATH", tmp_path / "publish_schedule.json")
    publish_schedule.assign_date("caso1")
    assert publish_schedule.all_entries()["caso1"]["modalidad"] == publish_schedule.MODALIDAD


def test_slugs_para_fecha_devuelve_todo_el_lote(tmp_path, monkeypatch):
    monkeypatch.setattr(publish_schedule, "SCHEDULE_PATH", tmp_path / "publish_schedule.json")
    esperados = [f"caso{i}" for i in range(publish_schedule.POR_DIA)]
    for slug in esperados:
        publish_schedule.assign_date(slug)

    assert sorted(publish_schedule.slugs_para_fecha("12092026")) == sorted(esperados)
    # El singular sigue devolviendo uno solo, para el job diario.
    assert publish_schedule.slug_para_fecha("12092026") in esperados
    assert publish_schedule.slug_para_fecha("11092026") is None


def test_record_upload_guarda_nombre_y_link(tmp_path, monkeypatch):
    monkeypatch.setattr(publish_schedule, "SCHEDULE_PATH", tmp_path / "publish_schedule.json")
    publish_schedule.assign_date("caso1")
    publish_schedule.record_upload("caso1", "criptografia_12092026.mp4", "https://drive.google.com/x")

    entries = publish_schedule.all_entries()
    assert entries["caso1"]["nombre_archivo"] == "criptografia_12092026.mp4"
    assert entries["caso1"]["drive_link"] == "https://drive.google.com/x"
    assert entries["caso1"]["fecha"] == "12092026"


def test_parse_fecha() -> None:
    assert publish_schedule.parse_fecha("12092026") == date(2026, 9, 12)
