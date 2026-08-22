from dato_mata_gato_bot import pipeline, sessions


def test_apply_logo_escribe_elegido_sin_indice_cubre_todas_las_tomas(tmp_path, monkeypatch):
    # "elegido" (sin "_1"): _manual_override en research_plano_media.py
    # prueba primero "elegido_<N>.*" por toma y cae a "elegido.*" si no
    # hay uno específico -- con "elegido_1" fijo, si p00 termina partido
    # en más de una toma (duración real > 4s), la 2da+ toma no tenía
    # ninguna cobertura y caía en la búsqueda real (caso confirmado: eligió
    # una foto de una moneda de bitcoin para el logo).
    logo_dir = tmp_path / "assets"
    logo_dir.mkdir()
    logo_file = logo_dir / f"{sessions.LOGO_STEM}.png"
    logo_file.write_bytes(b"fake-logo")
    monkeypatch.setattr(sessions, "LOGO_DIR", logo_dir)

    dest_dir = tmp_path / "proyecto"
    pipeline._apply_logo(dest_dir)

    p00_dir = dest_dir / "media" / "p00"
    assert (p00_dir / "elegido.png").exists()
    assert not (p00_dir / "elegido_1.png").exists()


def test_apply_logo_sin_logo_no_hace_nada(tmp_path, monkeypatch):
    monkeypatch.setattr(sessions, "LOGO_DIR", tmp_path / "no_existe")
    dest_dir = tmp_path / "proyecto"
    pipeline._apply_logo(dest_dir)
    assert not (dest_dir / "media").exists()
