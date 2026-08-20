import dato_mata_gato_bot.sessions as sessions


def test_ensure_session_id_es_nueva_la_primera_vez(tmp_path, monkeypatch):
    monkeypatch.setattr(sessions, "DATA_DIR", tmp_path)
    monkeypatch.setattr(sessions, "SESSIONS_PATH", tmp_path / "sessions.json")

    session_id, es_nueva = sessions.ensure_session_id(123)
    assert es_nueva is True

    session_id_2, es_nueva_2 = sessions.ensure_session_id(123)
    assert es_nueva_2 is False
    assert session_id_2 == session_id


def test_reset_session_fuerza_una_nueva(tmp_path, monkeypatch):
    monkeypatch.setattr(sessions, "DATA_DIR", tmp_path)
    monkeypatch.setattr(sessions, "SESSIONS_PATH", tmp_path / "sessions.json")

    session_id, _ = sessions.ensure_session_id(123)
    sessions.reset_session(123)
    new_session_id, es_nueva = sessions.ensure_session_id(123)

    assert es_nueva is True
    assert new_session_id != session_id


def test_slug_por_chat(tmp_path, monkeypatch):
    monkeypatch.setattr(sessions, "DATA_DIR", tmp_path)
    monkeypatch.setattr(sessions, "SESSIONS_PATH", tmp_path / "sessions.json")

    assert sessions.get_slug(456) is None
    sessions.set_slug(456, "mataviejitas")
    assert sessions.get_slug(456) == "mataviejitas"


def test_staging_dir_for_crea_carpeta_por_chat(tmp_path, monkeypatch):
    monkeypatch.setattr(sessions, "STAGING_DIR", tmp_path / "staging")

    d = sessions.staging_dir_for(789)
    assert d.exists()
    assert d.name == "789"


def test_get_voice_default_am_adam(tmp_path, monkeypatch):
    monkeypatch.setattr(sessions, "DATA_DIR", tmp_path)
    monkeypatch.setattr(sessions, "SESSIONS_PATH", tmp_path / "sessions.json")

    assert sessions.get_voice(111) == "am_adam"
    sessions.set_voice(111, "pm_santa")
    assert sessions.get_voice(111) == "pm_santa"


def test_awaiting_logo_flag(tmp_path, monkeypatch):
    monkeypatch.setattr(sessions, "DATA_DIR", tmp_path)
    monkeypatch.setattr(sessions, "SESSIONS_PATH", tmp_path / "sessions.json")

    assert sessions.is_awaiting_logo(222) is False
    sessions.set_awaiting_logo(222, True)
    assert sessions.is_awaiting_logo(222) is True
    sessions.set_awaiting_logo(222, False)
    assert sessions.is_awaiting_logo(222) is False


def test_logo_path_encuentra_cualquier_extension(tmp_path, monkeypatch):
    monkeypatch.setattr(sessions, "LOGO_DIR", tmp_path / "assets")
    assert sessions.logo_path() is None

    sessions.LOGO_DIR.mkdir(parents=True)
    logo_file = sessions.LOGO_DIR / f"{sessions.LOGO_STEM}.png"
    logo_file.write_bytes(b"fake-png")

    assert sessions.logo_path() == logo_file
