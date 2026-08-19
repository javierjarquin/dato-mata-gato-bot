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
