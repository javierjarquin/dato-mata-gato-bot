"""Reparto de un lote mixto entre crimen y trivia.

La modalidad del canal (09/09/2026) es de 5 videos por día, variados: no todo
crimen ni todo trivia.
"""

import pytest

from dato_mata_gato_bot import bot, publish_schedule


@pytest.fixture
def calendario(tmp_path, monkeypatch):
    monkeypatch.setattr(publish_schedule, "SCHEDULE_PATH", tmp_path / "publish_schedule.json")
    return publish_schedule


def _reparto(n=5):
    return [(desc, cant) for _, desc, cant in bot._reparto_mixto(n)]


def test_un_lote_de_cinco_sale_mixto(calendario):
    reparto = _reparto()
    assert len(reparto) == 2
    assert sum(cant for _, cant in reparto) == 5
    assert all(cant > 0 for _, cant in reparto)


def test_los_lotes_alternan_la_parte_grande(calendario):
    # Sin esto el canal se iría llenando de un solo tipo.
    assert _reparto() == [("de true crime", 3), ("de trivia", 2)]

    for i in range(3):
        calendario.assign_date(f"guion-c{i}")
    for i in range(2):
        calendario.assign_date(f"trivia-t{i}")

    assert _reparto() == [("de true crime", 2), ("de trivia", 3)]


def test_se_corrige_solo_si_un_lote_salio_a_medias(calendario):
    # El reparto mira el CALENDARIO, no los lotes pedidos: si de un lote solo
    # se subieron los de crimen, el siguiente compensa con trivia.
    for i in range(4):
        calendario.assign_date(f"guion-c{i}")

    assert _reparto() == [("de true crime", 2), ("de trivia", 3)]


def test_el_calendario_viejo_no_desbalancea_el_reparto(calendario):
    # Las entradas de la modalidad anterior no llevan `modalidad` y no cuentan:
    # eran 21 de crimen contra 10 de trivia, y arrastrarlas sesgaría los lotes
    # nuevos durante semanas.
    calendario.SCHEDULE_PATH.write_text(
        '{"guion-viejo-1": {"fecha": "01092026"}, "guion-viejo-2": {"fecha": "02092026"}}',
        encoding="utf-8",
    )
    assert _reparto() == [("de true crime", 3), ("de trivia", 2)]


def test_un_lote_de_uno_no_se_parte(calendario):
    # Pedir /lote 1 y que salga "0 de trivia" sería un tramo vacío mandado a
    # Claude.
    assert _reparto(1) == [("de true crime", 1)]


@pytest.mark.parametrize("n", [2, 3, 4, 5, 6, 7])
def test_ningun_tramo_queda_en_cero(calendario, n):
    reparto = _reparto(n)
    assert sum(cant for _, cant in reparto) == n
    assert all(cant > 0 for _, cant in reparto)


def test_contar_por_tipo_separa_por_prefijo_de_slug(calendario):
    calendario.assign_date("guion-caso")
    calendario.assign_date("trivia-arte-02")
    assert calendario.contar_por_tipo() == {"crimen": 1, "trivia": 1}
