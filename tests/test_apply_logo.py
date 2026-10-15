from dato_mata_gato_bot import pipeline, sessions

GUION_CON_APERTURA = {
    "planos": [
        {"id": "p00", "seccion": "identidad_apertura"},
        {"id": "p01", "seccion": "hook_segunda_persona"},
    ]
}

# Guion del formato nuevo (27/08/2026): sin plano de identidad al arranque --
# el título del caso se narra al inicio de p01, sobre la imagen real.
GUION_SIN_APERTURA = {
    "planos": [
        {"id": "p00", "seccion": "hook_segunda_persona"},
        {"id": "p01", "seccion": "el_hecho"},
    ]
}


def _preparar_logo(tmp_path, monkeypatch):
    logo_dir = tmp_path / "assets"
    logo_dir.mkdir()
    (logo_dir / f"{sessions.LOGO_STEM}.png").write_bytes(b"fake-logo")
    monkeypatch.setattr(sessions, "LOGO_DIR", logo_dir)


def test_apply_logo_escribe_elegido_sin_indice_cubre_todas_las_tomas(tmp_path, monkeypatch):
    # "elegido" (sin "_1"): _manual_override en research_plano_media.py
    # prueba primero "elegido_<N>.*" por toma y cae a "elegido.*" si no
    # hay uno específico -- con "elegido_1" fijo, si el plano termina partido
    # en más de una toma (duración real > 4s), la 2da+ toma no tenía
    # ninguna cobertura y caía en la búsqueda real (caso confirmado: eligió
    # una foto de una moneda de bitcoin para el logo).
    _preparar_logo(tmp_path, monkeypatch)

    dest_dir = tmp_path / "proyecto"
    pipeline._apply_logo(dest_dir, GUION_CON_APERTURA)

    p00_dir = dest_dir / "media" / "p00"
    assert (p00_dir / "elegido.png").exists()
    assert not (p00_dir / "elegido_1.png").exists()


def test_apply_logo_sin_logo_no_hace_nada(tmp_path, monkeypatch):
    monkeypatch.setattr(sessions, "LOGO_DIR", tmp_path / "no_existe")
    dest_dir = tmp_path / "proyecto"
    pipeline._apply_logo(dest_dir, GUION_CON_APERTURA)
    assert not (dest_dir / "media").exists()


def test_apply_logo_sin_plano_de_apertura_no_pisa_el_primer_plano(tmp_path, monkeypatch):
    # Sin plano identidad_apertura, el id "p00" es el primer plano de
    # contenido real: copiarle el logo encima le taparía la imagen del caso.
    _preparar_logo(tmp_path, monkeypatch)

    dest_dir = tmp_path / "proyecto"
    pipeline._apply_logo(dest_dir, GUION_SIN_APERTURA)

    assert not (dest_dir / "media").exists()
