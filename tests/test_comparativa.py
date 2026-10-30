"""Fórmula de la comparativa (20/10/2026): ahora contra antes, con la misma vara."""
from dato_mata_gato_bot import instruccion_comparativa as ic


def _guion(**cambios):
    g = {"_schema": {
            "comparacion": {"situacion": "El agua en Cancún",
                            "lado_a": {"quien": "Carlos Joaquín, gobernador", "periodo": "2016-2022", "como": "..."},
                            "lado_b": {"quien": "Mara Lezama, gobernadora", "periodo": "2022-2027", "como": "..."}},
            "indicador": {"nombre": "Horas con agua al día", "unidad": "horas", "fuente": "CONAGUA",
                          "a": "18 (2021)", "b": "20 (2025)"},
            "veredicto": {"mejor": "b", "por_que": "...", "lo_que_no_mide": "la calidad del agua"},
            "balance": {"bien_a": "...", "mal_a": "...", "bien_b": "...", "mal_b": "..."},
            "prueba_del_espejo": "..."},
         "evidencia": [{"id": "e2", "tipo": "documento"}],
         "plus": {"contradiccion": {"arriba": {"titulo": "ANTES"}}},
         "planos": [{"id": "p00", "narracion": "En Cancún el agua llegaba de una forma."}]}
    g.update(cambios)
    return g


def test_guion_completo_pasa():
    assert ic.problemas(_guion()) == []


def test_sin_misma_vara_ni_documento_no_pasa():
    g = _guion(evidencia=[])
    g["_schema"]["indicador"] = {"nombre": "agua"}
    p = ic.problemas(g)
    assert any("misma vara" in x for x in p) and any("documento" in x for x in p)


def test_lenguaje_de_campana_no_pasa():
    g = _guion(planos=[{"id": "p07", "narracion": "Eso hizo el mal gobierno."}])
    assert any("campaña" in x for x in ic.problemas(g))


def test_la_instruccion_lleva_publicar_y_busca_tema_sin_tema():
    t = ic.instruccion(2, None, "x", ligera=True)
    assert "PRIMERO, QUÉ COMPARAR" in t and "PARA PUBLICAR" in t and "<<" not in t
