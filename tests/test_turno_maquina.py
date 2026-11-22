"""Dos lotes a la vez, uno por canal (22/11/2026): se turnan la voz y el render."""
import threading
import time

from dato_mata_gato_bot import fabrica


def test_libre_se_toma_y_se_suelta():
    assert fabrica.tomar_maquina("a")
    assert fabrica._maquina_ocupada()
    fabrica.soltar_maquina("a")
    assert not fabrica._maquina_ocupada()


def test_quien_acaba_de_usarla_cede_el_turno(monkeypatch):
    monkeypatch.setattr(fabrica, "ESPERA_MAQUINA", 0.05)
    orden = []

    def lote(nombre, videos):
        for _ in range(videos):
            assert fabrica.tomar_maquina(nombre)
            orden.append(nombre)
            time.sleep(0.3)  # "el video"
            fabrica.soltar_maquina(nombre)

    a = threading.Thread(target=lote, args=("dmg", 3))
    a.start()
    time.sleep(0.1)  # dmg ya tiene la máquina cuando llega papasia
    b = threading.Thread(target=lote, args=("papasia", 3))
    b.start()
    a.join()
    b.join()
    assert orden == ["dmg", "papasia", "dmg", "papasia", "dmg", "papasia"]


def test_sin_nadie_esperando_sigue_el_mismo(monkeypatch):
    for _ in range(2):
        assert fabrica.tomar_maquina("dmg")
        fabrica.soltar_maquina("dmg")


def test_un_pararfabrica_mientras_espera(monkeypatch):
    monkeypatch.setattr(fabrica, "ESPERA_MAQUINA", 0.05)
    assert fabrica.tomar_maquina("dmg")
    assert fabrica.tomar_maquina("papasia", rendirse=lambda: True) is False
    fabrica.soltar_maquina("dmg")


def test_la_de_un_proceso_muerto_se_libera(monkeypatch):
    assert fabrica.tomar_maquina("dmg")
    monkeypatch.setattr(fabrica, "_proceso_vivo", lambda pid: False)
    assert not fabrica._maquina_ocupada()
