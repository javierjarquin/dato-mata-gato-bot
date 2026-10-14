"""Generador de trivias: plantilla determinista sobre el banco de preguntas."""

import json

import pytest

from dato_mata_gato_bot import trivia_generator as tg


def _pregunta(qid, dificultad):
    return {
        "id": qid, "dificultad": dificultad,
        "pregunta": f"¿Pregunta {qid}?", "respuesta": f"Respuesta {qid}",
        "dato_extra": "", "texto_pregunta": f"¿P {qid}?", "texto_respuesta": f"R {qid}",
        "verificacion": f"fuente de {qid}",
        "pregunta_visual": {"busqueda_medios": "algo"}, "respuesta_visual": {},
    }


def _banco(tmp_path, por_dificultad=2, temas=("forense",)):
    datos = {"temas": {}}
    for t in temas:
        qs = [_pregunta(f"{t}-{d}-{i}", d)
              for d in tg.DIFICULTADES for i in range(por_dificultad)]
        datos["temas"][t] = {"nombre": t, "preguntas": qs}
    ruta = tmp_path / "banco.json"
    ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return ruta


def _generar(tmp_path, cantidad=1, preguntas=6, temas=("forense",), por_dificultad=2):
    return tg.generar(
        cantidad, tmp_path / "out",
        banco_path=_banco(tmp_path, por_dificultad, temas),
        usadas_path=tmp_path / "usadas.json",
        semilla=1, preguntas=preguntas,
    )


def _guion(tmp_path, slug):
    return json.loads((tmp_path / "out" / slug / "guion.json").read_text(encoding="utf-8"))


def test_seis_preguntas_dan_quince_planos(tmp_path):
    # hook + 6x(pregunta+respuesta) + cierre + identidad
    g = _guion(tmp_path, _generar(tmp_path)[0])
    assert len(g["planos"]) == 15
    secciones = [p["seccion"] for p in g["planos"]]
    assert secciones.count("pregunta") == 6
    assert secciones.count("respuesta") == 6


def test_la_dificultad_sube(tmp_path):
    g = _guion(tmp_path, _generar(tmp_path)[0])
    marcas = [p["texto_en_pantalla"] for p in g["planos"] if p["seccion"] == "pregunta"]
    assert marcas == [
        "1 DE 6 · FÁCIL", "2 DE 6 · FÁCIL", "3 DE 6 · MEDIA",
        "4 DE 6 · MEDIA", "5 DE 6 · DIFÍCIL", "6 DE 6 · DIFÍCIL",
    ]


def test_ninguna_pregunta_se_repite_dentro_del_video(tmp_path):
    # Con dos 'facil' en la rampa hacen falta DOS preguntas faciles distintas.
    g = _guion(tmp_path, _generar(tmp_path)[0])
    textos = [p["narracion"] for p in g["planos"] if p["seccion"] == "pregunta"]
    assert len(set(textos)) == 6


def test_un_tema_sin_suficientes_no_se_ofrece(tmp_path):
    # Una sola pregunta por dificultad no alcanza para la rampa de 6.
    with pytest.raises(tg.BancoInsuficiente):
        _generar(tmp_path, preguntas=6, por_dificultad=1)


def test_con_tres_preguntas_el_mismo_banco_si_alcanza(tmp_path):
    slugs = _generar(tmp_path, preguntas=3, por_dificultad=1)
    assert len(_guion(tmp_path, slugs[0])["planos"]) == 9


def test_el_marcador_hablado_acumula(tmp_path):
    g = _guion(tmp_path, _generar(tmp_path)[0])
    respuestas = [p["narracion"] for p in g["planos"] if p["seccion"] == "respuesta"]
    assert "Vas 1 de 6." in respuestas[0]
    assert "Vas 4 de 6." in respuestas[3]
    # La penultima empuja fuerte y la ultima no lleva marcador: ya terminó.
    assert "la que sigue duele" in respuestas[4]
    assert "Vas" not in respuestas[5]


def test_el_cierre_vuelve_a_la_apertura(tmp_path):
    # El bucle es lo que hace que el video se re-mire, que es de las señales
    # de distribución más fuertes en Shorts.
    g = _guion(tmp_path, _generar(tmp_path)[0])
    cierre = next(p for p in g["planos"] if p["seccion"] == "cierre_interaccion")
    assert "la primera" in cierre["narracion"]


def test_el_gancho_adelanta_la_ultima_sin_responderla(tmp_path):
    # La promesa es lo que sostiene la permanencia: el gancho tiene que decir
    # CUAL es la ultima pregunta, y no puede filtrar su respuesta.
    g = _guion(tmp_path, _generar(tmp_path)[0])
    hook = g["planos"][0]["narracion"].lower()
    ultima_pregunta = g["planos"][11]["narracion"]
    ultima_respuesta = g["planos"][12]["narracion"].split(".")[0]

    assert "seis preguntas" in hook
    assert ultima_pregunta.strip("¿? .").split("saca. ")[-1].lower().strip("¿?") in hook
    assert ultima_respuesta.lower() not in hook


def test_no_se_repiten_preguntas_entre_videos(tmp_path):
    slugs = _generar(tmp_path, cantidad=2, preguntas=3, temas=("forense", "venenos"))
    vistos = set()
    for s in slugs:
        for p in _guion(tmp_path, s)["planos"]:
            if p["seccion"] == "pregunta":
                assert p["narracion"] not in vistos
                vistos.add(p["narracion"])


def test_las_usadas_quedan_registradas(tmp_path):
    _generar(tmp_path, preguntas=6)
    assert len(tg.cargar_usadas(tmp_path / "usadas.json")) == 6


def test_arrastra_la_verificacion_de_cada_pregunta(tmp_path):
    # Es lo que permite re-chequear el dato sin volver a investigarlo.
    g = _guion(tmp_path, _generar(tmp_path)[0])
    assert len(g["verificar_antes_de_publicar"]) == 6
    assert all(v.startswith("fuente de") for v in g["verificar_antes_de_publicar"])


def test_una_cantidad_sin_rampa_se_rechaza(tmp_path):
    with pytest.raises(ValueError):
        tg.rampa_de(4)


def test_pedir_mas_videos_que_temas_avisa(tmp_path):
    with pytest.raises(tg.BancoInsuficiente, match="Cargá más"):
        _generar(tmp_path, cantidad=3, temas=("forense",))


def _con_extras(tmp_path, palabras_extra, palabras_pregunta=6):
    """Banco donde cada pregunta trae un dato extra de N palabras."""
    datos = {"temas": {"forense": {"nombre": "forense", "preguntas": []}}}
    for d in tg.DIFICULTADES:
        for i in range(2):
            datos["temas"]["forense"]["preguntas"].append({
                "id": f"{d}-{i}", "dificultad": d,
                "pregunta": "¿" + " ".join(["palabra"] * palabras_pregunta) + "?",
                "respuesta": "Corta",
                "dato_extra": " ".join(["extra"] * palabras_extra),
                "texto_pregunta": "¿P?", "texto_respuesta": "R",
                "verificacion": "fuente", "pregunta_visual": {}, "respuesta_visual": {},
            })
    ruta = tmp_path / "banco.json"
    ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    slugs = tg.generar(1, tmp_path / "out", banco_path=ruta,
                       usadas_path=tmp_path / "u.json", semilla=1, preguntas=6)
    g = _guion(tmp_path, slugs[0])
    return g, sum(len((p.get("narracion") or "").split()) for p in g["planos"])


def test_el_video_no_se_pasa_del_presupuesto(tmp_path):
    # Sin tope, un lote real dio 316 palabras = 124 segundos, más largo que
    # los videos de crimen que acabábamos de acortar.
    _, palabras = _con_extras(tmp_path, palabras_extra=30)
    assert palabras <= tg.PRESUPUESTO_PALABRAS + 20


def test_los_extras_que_entran_son_los_ultimos(tmp_path):
    # El dato extra remata mejor al final, donde el espectador ya invirtió
    # tiempo; si hay que recortar, se cae el del principio.
    # 20 palabras por extra: no entran los seis, tiene que elegir.
    g, _ = _con_extras(tmp_path, palabras_extra=20)
    respuestas = [p["narracion"] for p in g["planos"] if p["seccion"] == "respuesta"]
    con_extra = ["extra" in r for r in respuestas]
    assert con_extra[-1], "la última respuesta tendría que conservar su dato"
    assert not con_extra[0], "la primera tendría que haberlo cedido"


def test_si_todo_entra_no_se_recorta_nada(tmp_path):
    g, _ = _con_extras(tmp_path, palabras_extra=2, palabras_pregunta=4)
    respuestas = [p["narracion"] for p in g["planos"] if p["seccion"] == "respuesta"]
    assert all("extra" in r for r in respuestas)


def test_el_titulo_es_corto_y_nombra_el_tema(tmp_path):
    """Antes era la pregunta difícil entera: 49 caracteres, y el archivo
    salía 'queciudadsegunlaleyendaincendiounavaca.mp4'."""
    slugs = _generar(tmp_path, temas=("forense",))
    g = _guion(tmp_path, slugs[0])
    assert len(g["titulo"]) <= tg._TITULO_MAX, g["titulo"]
    assert "forense" in g["titulo"].lower()
    assert "?" not in g["titulo"], "el título nombra, no pregunta"


def test_la_trivia_trae_gancho_de_pantalla(tmp_path):
    """Sin gancho, el video muestra el título entero en los primeros segundos."""
    g = _guion(tmp_path, _generar(tmp_path)[0])
    assert g.get("gancho")
    assert len(g["gancho"]) <= 35, g["gancho"]


def test_el_cierre_pide_un_comentario(tmp_path):
    """Tres segundos de firma que no piden nada son tres segundos perdidos."""
    g = _guion(tmp_path, _generar(tmp_path)[0])
    cierre = g["planos"][-1]
    assert cierre["seccion"] == "identidad_cierre"
    assert "comentario" in cierre["narracion"].lower()
    assert cierre.get("frase_cierre")
