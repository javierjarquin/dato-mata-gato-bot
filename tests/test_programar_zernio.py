"""Calendario de Zernio (tools/programar_zernio.py), 22/11/2026."""
import importlib.util
from collections import Counter
from datetime import date, datetime
from pathlib import Path

_RUTA = Path(__file__).resolve().parents[1] / "tools" / "programar_zernio.py"
_spec = importlib.util.spec_from_file_location("programar_zernio", _RUTA)
pz = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pz)


def _por_dia(lugares):
    return list(Counter(l["fecha"][:10] for l in lugares).values())


def test_lo_que_sobra_va_en_los_ultimos_dias():
    # Javier: "10 videos entre 3 días son dos días de a 3 y el último de 4".
    assert _por_dia(pz.armar_calendario(10, 3, date(2026, 11, 23), (10, 22), None)) == [3, 3, 4]
    assert _por_dia(pz.armar_calendario(20, 10, date(2026, 11, 23), (10, 22), None)) == [2] * 10
    assert _por_dia(pz.armar_calendario(11, 3, date(2026, 11, 23), (10, 22), None)) == [3, 4, 4]


def test_horas_parejas_en_la_ventana():
    lugares = pz.armar_calendario(3, 1, date(2026, 11, 23), (10, 22), None)
    assert [l["fecha"][11:16] for l in lugares] == ["12:00", "16:00", "20:00"]


def test_calendario_nuevo_no_se_encima_con_lo_ya_programado():
    ahora = datetime(2026, 11, 22, 21, 0)
    viejo = {"lugares": [
        {"fecha": "2026-11-23T13:00:00", "video": "temblores", "postId": "x"},
        {"fecha": "2026-11-24T13:00:00", "video": None, "postId": None},  # libre: no cuenta
    ]}
    assert pz.primer_dia_libre(viejo, ahora) == date(2026, 11, 24)
    assert pz.primer_dia_libre(None, ahora) == date(2026, 11, 23)
    ya_salio = {"lugares": [{"fecha": "2026-11-22T13:00:00", "video": "a", "postId": "x"}]}
    assert pz.primer_dia_libre(ya_salio, ahora) == date(2026, 11, 23)


def test_lugar_vencido_se_repone_al_final_a_la_misma_hora():
    cal = {"lugares": pz.armar_calendario(4, 2, date(2026, 11, 23), (10, 22), None)}
    cal["lugares"][1]["video"] = "listo"  # el de las 19:00 sí llegó
    ahora = datetime(2026, 11, 23, 15, 0)  # el de las 13:00 pasó sin video
    assert pz.reponer_vencidos(cal, ahora) == 1
    assert cal["lugares"][0]["vencido"] is True
    assert cal["lugares"][-1]["fecha"] == "2026-11-25T13:00:00"
    vivos = [l for l in cal["lugares"] if not l.get("vencido")]
    assert len(vivos) == 4  # siguen siendo 4 lugares para los 4 videos
    assert pz.reponer_vencidos(cal, ahora) == 0  # no lo repone dos veces


def test_videos_de_un_lote_que_aun_no_existe(tmp_path, monkeypatch):
    monkeypatch.setattr(pz, "ENTRADA_BASE", tmp_path)
    c = pz.Canal("datomatagato")
    (c.lotes / "viejo").mkdir(parents=True)
    (c.lotes / "viejo" / "a.mp4").write_bytes(b"x")
    assert [p.name for p in pz.videos_archivados(c)] == ["a.mp4"]
    assert pz.videos_archivados(c, "todos-20261122-2100") == []
