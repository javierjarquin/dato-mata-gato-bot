"""Variar el responsable y no meterse a lo electoral (Javier, 03/11/2026).

Hasta el 03/11 el 86% de los videos tenía un actor de gobierno (61% en viral) y
el canal se leía como de política local, lo que le achica el público. Medido en
`C:\\clip_assistance\\analisis\\que_tan_politico_2026-11-03.md`.

Lo electoral es aparte: es lo único político que las plataformas sí restringen
(la pauta política pagada no es elegible para "Para ti").
"""

from tests.test_aperturas_p01 import instrucciones


def test_cercania_pide_variar_el_responsable():
    texto = instrucciones()["cercania"]
    assert "VARÍA QUIÉN ES EL RESPONSABLE" in texto
    assert "NO tiene que ser gobierno" in texto


def test_cercania_da_ejemplos_de_responsable_privado():
    """Sin ejemplos concretos la regla no se ejecuta."""
    texto = instrucciones()["cercania"]
    for ejemplo in ("patrón", "concesionaria", "constructora"):
        assert ejemplo in texto, f"falta el ejemplo: {ejemplo}"


def test_viral_abre_la_opacidad_a_lo_privado():
    """El coraje de viral era "contra la OPACIDAD", que apunta a autoridades."""
    texto = instrucciones()["viral"]
    assert "LA OPACIDAD TAMBIÉN ES PRIVADA" in texto


def test_las_tres_formulas_prohiben_lo_electoral():
    """Cercanía, viral y polémica: nada de partidos, candidatos ni elecciones."""
    for nombre in ("cercania", "viral", "polemica"):
        texto = instrucciones()[nombre]
        assert "NADA ELECTORAL" in texto, f"{nombre} sin el candado electoral"
        assert "candidatos" in texto, f"{nombre} no nombra candidatos"


def test_el_candado_electoral_no_rompe_la_pieza_4():
    """La pieza 4 sigue pidiendo un responsable con nombre."""
    texto = instrucciones()["cercania"]
    assert "4. CORAJE" in texto
    assert "no se inventan culpables" in texto
    assert "un acusado sin sentencia" in texto
