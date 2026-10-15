"""Lectura de la lista de guiones que devuelve Claude.

El 12/09/2026 un lote real se dio por fallido con los guiones YA escritos en
disco: Claude respondió el JSON pedido pero con texto alrededor, y el parser
exigía que la respuesta ENTERA fuera JSON.
"""

from dato_mata_gato_bot.bot import _parse_lote_response

BLOQUE = '{"guiones": [{"slug": "guion-a", "titulo": "A"}, {"slug": "guion-b", "titulo": "B"}]}'


def _slugs(texto):
    guiones = _parse_lote_response(texto)
    return [g["slug"] for g in guiones] if guiones else None


def test_json_pelado():
    assert _slugs(BLOQUE) == ["guion-a", "guion-b"]


def test_envuelto_en_fence():
    assert _slugs(f"```json\n{BLOQUE}\n```") == ["guion-a", "guion-b"]


def test_con_texto_antes():
    # El caso real: Claude explica lo que hizo y despues pone el bloque.
    texto = f"Listo, escribi los dos guiones en C:\Android_in.\n\n{BLOQUE}"
    assert _slugs(texto) == ["guion-a", "guion-b"]


def test_con_texto_antes_y_despues():
    assert _slugs(f"Ahi van:\n{BLOQUE}\n\nAvisame si querés cambios.") == ["guion-a", "guion-b"]


def test_fence_con_texto_alrededor():
    texto = f"Resumen del lote.\n\n```json\n{BLOQUE}\n```\n\nQuedaron listos."
    assert _slugs(texto) == ["guion-a", "guion-b"]


def test_se_queda_con_el_ultimo_bloque():
    # Si menciona un ejemplo antes, el bloque pedido es el del final.
    ejemplo = '{"guiones": [{"slug": "ejemplo"}]}'
    assert _slugs(f"Por ejemplo {ejemplo} ... y el resultado:\n{BLOQUE}") == ["guion-a", "guion-b"]


def test_ignora_json_que_no_es_la_lista():
    # Un objeto JSON cualquiera en el texto no debe hacerlo pasar por bueno.
    texto = f'Config: {{"modo": "crimen"}}\n\n{BLOQUE}'
    assert _slugs(texto) == ["guion-a", "guion-b"]


def test_sin_json_devuelve_none():
    assert _parse_lote_response("No pude generar los guiones, falta contexto.") is None


def test_json_roto_devuelve_none():
    assert _parse_lote_response('{"guiones": [{"slug": roto}]}') is None


def test_guiones_que_no_es_lista_devuelve_none():
    assert _parse_lote_response('{"guiones": "guion-a"}') is None


def test_anidado_no_rompe_el_balanceo():
    # Las llaves internas no deben cortar el objeto de nivel superior.
    anidado = '{"guiones": [{"slug": "g1", "meta": {"k": {"j": 1}}}]}'
    assert _slugs(f"texto\n{anidado}\ncola") == ["g1"]
