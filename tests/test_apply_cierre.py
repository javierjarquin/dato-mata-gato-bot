from dato_mata_gato_bot import pipeline, sessions


def _guion(planos):
    return {"planos": planos}


def test_apply_cierre_escribe_elegido_en_el_plano_identidad_cierre(tmp_path, monkeypatch):
    # El id del plano de cierre varía según el guion (p09, p10, p11...) --
    # se identifica por seccion=="identidad_cierre" (estable en todos los
    # guiones, simétrico a identidad_apertura de p00), no por un id fijo.
    cierre_dir = tmp_path / "assets"
    cierre_dir.mkdir()
    cierre_file = cierre_dir / f"{sessions.CIERRE_STEM}.png"
    cierre_file.write_bytes(b"fake-cierre")
    monkeypatch.setattr(sessions, "LOGO_DIR", cierre_dir)

    guion = _guion([
        {"id": "p00", "seccion": "identidad_apertura"},
        {"id": "p01", "seccion": "cierre_caso"},
        {"id": "p02", "seccion": "identidad_cierre"},
    ])
    dest_dir = tmp_path / "proyecto"
    pipeline._apply_cierre(dest_dir, guion)

    p02_dir = dest_dir / "media" / "p02"
    assert (p02_dir / "elegido.png").exists()
    assert not (dest_dir / "media" / "p00").exists()
    assert not (dest_dir / "media" / "p01").exists()


def test_apply_cierre_sin_cierre_subido_no_hace_nada(tmp_path, monkeypatch):
    monkeypatch.setattr(sessions, "LOGO_DIR", tmp_path / "no_existe")
    guion = _guion([{"id": "p02", "seccion": "identidad_cierre"}])
    dest_dir = tmp_path / "proyecto"
    pipeline._apply_cierre(dest_dir, guion)
    assert not (dest_dir / "media").exists()


def test_apply_cierre_sin_plano_identidad_cierre_no_hace_nada(tmp_path, monkeypatch):
    cierre_dir = tmp_path / "assets"
    cierre_dir.mkdir()
    (cierre_dir / f"{sessions.CIERRE_STEM}.png").write_bytes(b"fake-cierre")
    monkeypatch.setattr(sessions, "LOGO_DIR", cierre_dir)

    guion = _guion([{"id": "p00", "seccion": "identidad_apertura"}])
    dest_dir = tmp_path / "proyecto"
    pipeline._apply_cierre(dest_dir, guion)
    assert not (dest_dir / "media").exists()
