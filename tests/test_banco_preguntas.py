"""Alta de preguntas en el banco: solo entra lo que está completo."""

import json

from dato_mata_gato_bot import banco_preguntas as bp


def _q(**kw):
    base = {"tema": "forense", "dificultad": "media",
            "pregunta": "¿Cuánto tarda?", "respuesta": "Tres días"}
    base.update(kw)
    return base


def _agregar(tmp_path, preguntas):
    n = bp.agregar(preguntas, banco_path=tmp_path / "b.json", registro_path=tmp_path / "r.txt")
    banco = json.loads((tmp_path / "b.json").read_text(encoding="utf-8")) if n else {"temas": {}}
    return n, banco


def test_una_pregunta_completa_entra(tmp_path):
    n, banco = _agregar(tmp_path, [_q(verificacion="fuente X")])
    assert n == 1
    q = banco["temas"]["forense"]["preguntas"][0]
    assert q["pregunta"] == "¿Cuánto tarda?"
    assert q["verificacion"] == "fuente X"


def test_sin_respuesta_no_entra(tmp_path):
    # Media pregunta en el banco es un video roto mas adelante.
    n, _ = _agregar(tmp_path, [_q(respuesta="")])
    assert n == 0


def test_dificultad_invalida_no_entra(tmp_path):
    n, _ = _agregar(tmp_path, [_q(dificultad="imposible")])
    assert n == 0


def test_dificultad_con_acento_se_normaliza(tmp_path):
    n, banco = _agregar(tmp_path, [_q(dificultad="Difícil")])
    assert n == 1
    assert banco["temas"]["forense"]["preguntas"][0]["dificultad"] == "dificil"


def test_los_ids_no_se_pisan(tmp_path):
    n, banco = _agregar(tmp_path, [_q(pregunta="¿A?"), _q(pregunta="¿B?"), _q(pregunta="¿C?")])
    ids = [q["id"] for q in banco["temas"]["forense"]["preguntas"]]
    assert n == 3
    assert len(set(ids)) == 3


def test_una_segunda_tanda_no_pisa_a_la_primera(tmp_path):
    bp.agregar([_q(pregunta="¿A?")], banco_path=tmp_path / "b.json",
               registro_path=tmp_path / "r.txt")
    n, banco = _agregar(tmp_path, [_q(pregunta="¿B?")])
    preguntas = banco["temas"]["forense"]["preguntas"]
    assert n == 1
    assert len(preguntas) == 2
    assert len({q["id"] for q in preguntas}) == 2


def test_el_tema_se_normaliza_pero_guarda_el_nombre_legible(tmp_path):
    # La clave sin acentos arma el slug; el nombre con acentos lo dice el TTS.
    _, banco = _agregar(tmp_path, [_q(tema="Crímenes Históricos")])
    assert "crimenes-historicos" in banco["temas"]
    assert banco["temas"]["crimenes-historicos"]["nombre"] == "Crímenes Históricos"


def test_el_registro_txt_deja_rastro_de_la_verificacion(tmp_path):
    _agregar(tmp_path, [_q(verificacion="Consenso forense documentado")])
    registro = (tmp_path / "r.txt").read_text(encoding="utf-8")
    assert "Consenso forense documentado" in registro
    assert "¿Cuánto tarda?" in registro


def test_si_nada_entra_no_se_toca_el_banco(tmp_path):
    _agregar(tmp_path, [_q(dificultad="mal")])
    assert not (tmp_path / "b.json").exists()
    assert not (tmp_path / "r.txt").exists()
