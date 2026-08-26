"""_parse_lote_response: la respuesta de Claude a /nuevolote debería ser
SOLO el bloque JSON pedido, pero en la práctica a veces lo envuelve en
```json ... ``` pese a la instrucción -- hay que tolerar eso."""

import json

from dato_mata_gato_bot.bot import _parse_lote_response


def test_parsea_json_limpio():
    texto = json.dumps({"guiones": [{"slug": "guion-x", "titulo": "X", "resumen_hechos": "..."}]})
    guiones = _parse_lote_response(texto)
    assert guiones == [{"slug": "guion-x", "titulo": "X", "resumen_hechos": "..."}]


def test_parsea_json_envuelto_en_fence_markdown():
    payload = json.dumps({"guiones": [{"slug": "guion-y", "titulo": "Y", "resumen_hechos": "..."}]})
    texto = f"```json\n{payload}\n```"
    guiones = _parse_lote_response(texto)
    assert guiones == [{"slug": "guion-y", "titulo": "Y", "resumen_hechos": "..."}]


def test_texto_no_parseable_devuelve_none():
    assert _parse_lote_response("esto no es json") is None


def test_json_sin_clave_guiones_devuelve_none():
    assert _parse_lote_response(json.dumps({"otracosa": []})) is None
