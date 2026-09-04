import json
from datetime import date

from dato_mata_gato_bot import daily_publish, publish_schedule


def _preparar(tmp_path, monkeypatch, schedule: dict, guiones: dict | None = None):
    sched_path = tmp_path / "publish_schedule.json"
    sched_path.write_text(json.dumps(schedule), encoding="utf-8")
    monkeypatch.setattr(publish_schedule, "SCHEDULE_PATH", sched_path)

    projects = tmp_path / "projects"
    projects.mkdir()
    for slug, guion in (guiones or {}).items():
        proj = projects / slug
        proj.mkdir()
        (proj / "guion.json").write_text(json.dumps(guion, ensure_ascii=False), encoding="utf-8")
        (proj / "final.mp4").write_bytes(b"fake-video")
    monkeypatch.setattr(daily_publish, "NARRATOR_PROJECTS", projects)
    return projects


def test_devuelve_el_video_agendado_para_hoy(tmp_path, monkeypatch):
    _preparar(
        tmp_path,
        monkeypatch,
        {"guion-uno": {"fecha": "01092026", "drive_link": "https://drive/x"}},
        {"guion-uno": {"titulo": "Título real", "hashtags": ["#A", "#B"]}},
    )

    video = daily_publish.video_del_dia(date(2026, 9, 1))

    assert video is not None
    assert video.slug == "guion-uno"
    assert video.titulo == "Título real"
    assert video.caption_tiktok == "Título real\n\n#A #B"
    assert video.drive_link == "https://drive/x"


def test_sin_video_agendado_para_hoy(tmp_path, monkeypatch):
    _preparar(tmp_path, monkeypatch, {"guion-uno": {"fecha": "01092026"}})
    assert daily_publish.video_del_dia(date(2026, 9, 2)) is None


def test_no_republica_lo_ya_publicado(tmp_path, monkeypatch):
    # Idempotencia: el bot se relanza solo al iniciar sesión de Windows, así
    # que el job diario puede volver a dispararse el mismo día.
    _preparar(
        tmp_path,
        monkeypatch,
        {"guion-uno": {"fecha": "01092026", "publicado_fb_en": "2026-09-01T20:00:03"}},
    )
    assert daily_publish.video_del_dia(date(2026, 9, 1)) is None


def test_avisa_si_falta_el_video_y_no_publica(tmp_path, monkeypatch):
    _preparar(
        tmp_path,
        monkeypatch,
        {"guion-uno": {"fecha": "01092026"}},
        {"guion-uno": {"titulo": "Sin archivo"}},
    )
    video = daily_publish.video_del_dia(date(2026, 9, 1))
    video.final_mp4.unlink()

    llamado = False

    def _no_deberia_llamarse(slug):  # pragma: no cover
        nonlocal llamado
        llamado = True
        return True, ""

    monkeypatch.setattr(daily_publish.pipeline, "publish_to_facebook", _no_deberia_llamarse)

    ok, msg = daily_publish.publicar_en_facebook(video)

    assert ok is False
    assert llamado is False
    assert "no existe el video" in msg


def test_publica_y_registra_el_post(tmp_path, monkeypatch):
    _preparar(
        tmp_path,
        monkeypatch,
        {"guion-uno": {"fecha": "01092026"}},
        {"guion-uno": {"titulo": "Caso real"}},
    )
    monkeypatch.setattr(
        daily_publish.pipeline,
        "publish_to_facebook",
        lambda slug: (True, "Publicando…\nPublicado. ID: 12345\nURL: https://fb.com/p/12345\n"),
    )

    video = daily_publish.video_del_dia(date(2026, 9, 1))
    ok, msg = daily_publish.publicar_en_facebook(video)

    assert ok is True
    assert "Caso real" in msg
    assert "https://fb.com/p/12345" in msg

    entry = publish_schedule.all_entries()["guion-uno"]
    assert entry["facebook_post_id"] == "12345"
    assert entry["publicado_fb_en"]
    # Y ya no se vuelve a ofrecer para publicar.
    assert daily_publish.video_del_dia(date(2026, 9, 1)) is None


def test_publicacion_fallida_no_marca_como_publicado(tmp_path, monkeypatch):
    _preparar(
        tmp_path,
        monkeypatch,
        {"guion-uno": {"fecha": "01092026"}},
        {"guion-uno": {"titulo": "Caso real"}},
    )
    monkeypatch.setattr(
        daily_publish.pipeline,
        "publish_to_facebook",
        lambda slug: (False, "FALLÓ: token vencido"),
    )

    video = daily_publish.video_del_dia(date(2026, 9, 1))
    ok, msg = daily_publish.publicar_en_facebook(video)

    assert ok is False
    assert "token vencido" in msg
    assert not publish_schedule.ya_publicado_en_facebook("guion-uno")
    # Sigue pendiente, para poder reintentar.
    assert daily_publish.video_del_dia(date(2026, 9, 1)) is not None


def test_mensaje_tiktok_incluye_caption_y_link(tmp_path, monkeypatch):
    _preparar(
        tmp_path,
        monkeypatch,
        {"guion-uno": {"fecha": "01092026", "drive_link": "https://drive/abc"}},
        {"guion-uno": {"titulo": "Un caso", "hashtags": ["#DatoMataGato"]}},
    )
    video = daily_publish.video_del_dia(date(2026, 9, 1))

    msg = daily_publish.mensaje_tiktok(video)

    assert "Un caso" in msg
    assert "#DatoMataGato" in msg
    assert "https://drive/abc" in msg
