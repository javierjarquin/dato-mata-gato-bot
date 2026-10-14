"""El paso del presentador, sin correr MuseTalk.

Lo que importa probar acá no es la sincronización de labios (eso son dos horas
y media de GPU) sino el manejo de archivos: el video del pipeline cuesta
quince minutos y el compuesto dos horas y media, así que un intercambio mal
hecho borra trabajo caro.
"""

import pytest

from dato_mata_gato_bot import avatar_presentador


def test_disponible_avisa_que_falta_la_placa(tmp_path, monkeypatch):
    monkeypatch.setattr(avatar_presentador, "PLACAS", {0: tmp_path / "no_existe.mp4"})
    motivo = avatar_presentador.disponible()
    assert "placa" in motivo.lower()
    assert "no_existe.mp4" in motivo


def test_disponible_avisa_que_falta_una_herramienta(tmp_path, monkeypatch):
    monkeypatch.setattr(avatar_presentador, "PLACAS", {0: tmp_path / "placa.mp4"})
    (tmp_path / "placa.mp4").write_bytes(b"x")
    monkeypatch.setattr(avatar_presentador, "HERRAMIENTAS", tmp_path / "vacio")
    motivo = avatar_presentador.disponible()
    assert "poc_avatar.py" in motivo


def test_disponible_rechaza_un_avatar_que_no_existe(tmp_path, monkeypatch):
    """Pedir /vacamorada 7 tiene que decir cuáles hay, no fallar opaco."""
    placa = tmp_path / "placa.mp4"
    placa.write_bytes(b"x")
    monkeypatch.setattr(avatar_presentador, "PLACAS", {0: placa, 1: placa})
    motivo = avatar_presentador.disponible(7)
    assert "avatar 7" in motivo
    assert "0, 1" in motivo


def test_cada_avatar_usa_su_propia_placa(tmp_path, monkeypatch):
    monkeypatch.setattr(avatar_presentador, "PLACAS",
                        {0: tmp_path / "cero.mp4", 1: tmp_path / "uno.mp4"})
    assert avatar_presentador.placa_de(None).name == "cero.mp4"
    assert avatar_presentador.placa_de(0).name == "cero.mp4"
    assert avatar_presentador.placa_de(1).name == "uno.mp4"


def test_componer_falla_si_no_existe_el_video(tmp_path, monkeypatch):
    monkeypatch.setattr(avatar_presentador, "disponible", lambda a=None: "")
    with pytest.raises(avatar_presentador.AvatarError, match="No existe"):
        avatar_presentador.componer(tmp_path / "final.mp4")


def test_componer_no_toca_nada_si_falla_un_paso(tmp_path, monkeypatch):
    """El video del pipeline tiene que quedar intacto y publicable."""
    proyecto = tmp_path / "proyectos" / "guion-x"
    proyecto.mkdir(parents=True)
    final = proyecto / "final.mp4"
    final.write_bytes(b"video original")

    monkeypatch.setattr(avatar_presentador, "disponible", lambda a=None: "")
    monkeypatch.setattr(avatar_presentador, "SALIDAS", tmp_path / "salidas")

    def explota(args, paso, timeout):
        raise avatar_presentador.AvatarError(f"{paso} se cayó")

    monkeypatch.setattr(avatar_presentador, "_correr", explota)

    with pytest.raises(avatar_presentador.AvatarError):
        avatar_presentador.componer(final)

    assert final.read_bytes() == b"video original"
    assert not (proyecto / "final_sin_avatar.mp4").exists()


def test_componer_intercambia_y_guarda_el_original(tmp_path, monkeypatch):
    proyecto = tmp_path / "proyectos" / "guion-x"
    proyecto.mkdir(parents=True)
    final = proyecto / "final.mp4"
    final.write_bytes(b"video original")

    monkeypatch.setattr(avatar_presentador, "disponible", lambda a=None: "")
    monkeypatch.setattr(avatar_presentador, "SALIDAS", tmp_path / "salidas")

    pasos = []

    def fingir(args, paso, timeout):
        pasos.append(paso)
        # El último paso es el que escribe el compuesto.
        if paso == "composición":
            (proyecto / "final_con_avatar.mp4").write_bytes(b"video con avatar")
        return ""

    monkeypatch.setattr(avatar_presentador, "_correr", fingir)

    resultado = avatar_presentador.componer(final)

    assert resultado == final
    assert final.read_bytes() == b"video con avatar"
    assert (proyecto / "final_sin_avatar.mp4").read_bytes() == b"video original"
    # Y que no haya quedado el intermedio dando vueltas con el nombre viejo.
    assert not (proyecto / "final_con_avatar.mp4").exists()
    assert pasos == ["extracción de audio", "MuseTalk", "recorte de fondo", "composición"]


def test_componer_falla_si_la_composicion_no_escribio_nada(tmp_path, monkeypatch):
    """Un subproceso puede terminar con código 0 y no dejar archivo."""
    proyecto = tmp_path / "proyectos" / "guion-x"
    proyecto.mkdir(parents=True)
    final = proyecto / "final.mp4"
    final.write_bytes(b"video original")

    monkeypatch.setattr(avatar_presentador, "disponible", lambda a=None: "")
    monkeypatch.setattr(avatar_presentador, "SALIDAS", tmp_path / "salidas")
    monkeypatch.setattr(avatar_presentador, "_correr", lambda args, paso, timeout: "")

    with pytest.raises(avatar_presentador.AvatarError, match="sin escribir"):
        avatar_presentador.componer(final)
    assert final.read_bytes() == b"video original"
