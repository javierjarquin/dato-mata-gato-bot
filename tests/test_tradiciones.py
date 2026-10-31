"""Nicho "el porqué de las tradiciones" (30/10/2026): revisión del guion con
escenas 3D, expediente con IA gratis y el desvío del pipeline al render 3D."""

import json
import subprocess
from pathlib import Path

from dato_mata_gato_bot import (expediente, expediente_tradiciones, fabrica, ia_gratis, instruccion_tradiciones,
                                pipeline)

RELLENO = " Y fíjate que esto se cuenta en todo el país desde hace mucho tiempo."


def _escena(eid, tiempo, texto, respaldo="hecho", **extra):
    claves = [w.strip("¿?.,:") for w in texto.split()[:2]]
    return {"id": eid, "tiempo": tiempo, "respaldo": respaldo, "texto": texto, "camara": "frente",
            "visual": [{"objeto": "Flor", "gira": 0.3}], "claves": claves, **extra}


def _guion() -> dict:
    escenas = [
        _escena("pregunta", "pregunta", "¿Por qué el pan de muerto lleva huesitos encima?", "sin_dato"),
        _escena("respuesta", "respuesta", "Porque te estás comiendo un esqueleto: las tiras son huesos y la bolita es el cráneo." + RELLENO),
        _escena("origen", "giro_origen", "Pero el pan no es de aquí: el trigo llegó con los españoles." + RELLENO),
        _escena("mito", "giro_historia", "Cuenta la leyenda que Quetzalcóatl bajó al Mictlán por los huesos." + RELLENO, "cuento"),
        _escena("idea", "idea", "Un hueso no era el final, era una semilla." + RELLENO),
        _escena("rasgos", "rasgos", "Dicen que la cruz son los cuatro rumbos del mundo." + RELLENO, "saber_popular"),
        _escena("redondo", "cierre_redondo", "El pan de muerto cuenta el mito al revés." + RELLENO, "sin_dato"),
        _escena("presente", "presente", "Por eso cada noviembre los invitas a cenar a tu casa." + RELLENO, "sin_dato"),
        _escena("mandar", "mandar", "Mándaselo a quien siempre se come los huesitos primero.", "sin_dato"),
    ]
    return {"formato": "tradiciones", "titulo": "¿Por qué el pan de muerto lleva huesitos?", "objeto": "pan de muerto",
            "protagonista": {"objeto": "Flor"},
            "descripcion": "Por qué el pan de muerto lleva huesitos y una bolita encima, de dónde viene y qué mito "
                           "mexica cuenta. ¿Tú te comes los huesitos primero?",
            "hashtags": ["#DiaDeMuertos", "#PanDeMuerto", "#TradicionesMexicanas", "#DatoMataGato"],
            "plus": {"portada": {"texto": "TE COMES UN ESQUELETO", "resalta": "ESQUELETO"}},
            "escenas": escenas,
            "_schema": {"fuentes": {e["id"]: "fuente" for e in escenas if e["respaldo"] != "sin_dato"}}}


def test_un_guion_completo_pasa():
    assert instruccion_tradiciones.problemas(_guion()) == []


def test_objetos_y_props_que_el_render_no_sabe_dibujar():
    g = _guion()
    g["escenas"][1]["visual"] = [{"objeto": "Calavera"}, {"objeto": "Flor", "color": "#fff", "gira": 0.2},
                                 {"objeto": "Sol", "fuerza": {"de": 0, "a": 1, "desde": 0.5, "hasta": 1.4}}]
    g["escenas"][2]["camara"] = "dron"
    out = "\n".join(instruccion_tradiciones.problemas(g))
    assert "Calavera" in out and "no tiene color" in out and "Sol.fuerza" in out and "camara" in out


def test_saber_popular_va_atribuido_y_todo_dato_con_fuente():
    g = _guion()
    g["escenas"][5]["texto"] = "La cruz son los cuatro rumbos del mundo." + RELLENO
    g["escenas"][5]["claves"] = ["cruz"]
    del g["_schema"]["fuentes"]["mito"]
    out = "\n".join(instruccion_tradiciones.problemas(g))
    assert "rasgos: es saber_popular y la voz lo dice como hecho" in out
    assert 'mito: es "cuento" y no tiene fuente' in out


def test_los_nueve_tiempos_en_orden_y_el_mandar():
    g = _guion()
    g["escenas"][1], g["escenas"][2] = g["escenas"][2], g["escenas"][1]
    g["escenas"][-1]["texto"] = "Y ya sabes por qué."
    g["escenas"][-1]["claves"] = ["sabes"]
    out = "\n".join(instruccion_tradiciones.problemas(g))
    assert "orden de la fórmula" in out and "Mándaselo" in out


def _biblioteca(tmp_path, monkeypatch):
    indice = tmp_path / "indice.json"
    indice.write_text(json.dumps({"food/corn": "elote", "graveyard/candle": "vela"}), encoding="utf-8")
    monkeypatch.setattr(instruccion_tradiciones, "MODELOS_INDICE", indice)


def test_el_protagonista_tiene_que_existir(tmp_path, monkeypatch):
    """30/10/2026: la calaverita armada con esferas se veía como figuras geométricas."""
    _biblioteca(tmp_path, monkeypatch)
    g = _guion()
    g["protagonista"] = {"objeto": "Forma", "forma": "esfera"}
    assert any("no existe" in p for p in instruccion_tradiciones.problemas(g))

    g["protagonista"] = {"objeto": "Modelo", "modelo": "food/corn"}
    elote = {"objeto": "Modelo", "modelo": "food/corn", "alto": 0.4}
    out = "\n".join(instruccion_tradiciones.problemas(g))
    assert "primera escena" in out and "tres últimas" in out
    g["escenas"][0]["visual"].append(elote)
    g["escenas"][-1]["visual"].append(elote)
    assert instruccion_tradiciones.problemas(g) == []


def test_modelos_que_no_hay_y_demasiadas_formas(tmp_path, monkeypatch):
    _biblioteca(tmp_path, monkeypatch)
    g = _guion()
    g["escenas"][2]["visual"] = [{"objeto": "Modelo", "modelo": "food/corm"}] + [
        {"objeto": "Forma", "forma": "esfera"} for _ in range(3)]
    out = "\n".join(instruccion_tradiciones.problemas(g))
    assert '"food/corm" no está en la biblioteca (¿food/corn?)' in out
    assert "más de 2 Forma" in out


def test_la_instruccion_lista_la_biblioteca(tmp_path, monkeypatch):
    _biblioteca(tmp_path, monkeypatch)
    texto = instruccion_tradiciones.instruccion(1, None, "")
    assert "food/corn (elote)" in texto and "graveyard/candle (vela)" in texto


def test_solo_se_proponen_temas_con_protagonista(tmp_path, monkeypatch):
    _biblioteca(tmp_path, monkeypatch)
    monkeypatch.setattr(ia_gratis, "pedir", lambda *a, **k: {"temas": [
        {"pregunta": "¿Por qué el elote…?", "objeto": "elote", "protagonista": "Modelo:food/corn", "busqueda": "maíz"},
        {"pregunta": "¿Por qué la calaverita…?", "objeto": "calaverita", "protagonista": "Forma", "busqueda": "x"}]})
    temas = expediente_tradiciones.proponer(None, 2, "")
    assert [t["protagonista"] for t in temas] == ["Modelo:food/corn"]


def test_el_presente_va_de_tu():
    g = _guion()
    g["escenas"][7]["texto"] = "Por eso cada noviembre lo primero que cuelgo es el papel." + RELLENO
    assert any("de tú" in p for p in instruccion_tradiciones.problemas(g))


def test_claves_que_la_voz_no_dice():
    g = _guion()
    g["escenas"][2]["claves"] = ["trigo", "Mictlán"]
    assert any("Mictlán" in p for p in instruccion_tradiciones.problemas(g))


def test_la_instruccion_trae_todo_el_catalogo_y_las_camaras():
    texto = instruccion_tradiciones.instruccion(2, None, "Caso X", ligera=True)
    assert all(nombre in texto for nombre in instruccion_tradiciones.CATALOGO)
    assert all(c in texto for c in instruccion_tradiciones.CAMARAS)
    assert "herramientas_guion revisar" in texto and "expediente buscar" in texto
    assert texto.endswith("Caso X")


def test_revisar_usa_la_revision_de_tradiciones(tmp_path, monkeypatch):
    """Sin planos ni evidencia, las reglas de cercanía lo tumbarían entero."""
    from dato_mata_gato_bot import herramientas_guion

    monkeypatch.setattr(fabrica.pipeline, "ANDROID_IN", tmp_path)
    (tmp_path / "guion-tradicion-pan").mkdir()
    (tmp_path / "guion-tradicion-pan" / "guion.json").write_text(json.dumps(_guion(), ensure_ascii=False),
                                                                encoding="utf-8")
    assert herramientas_guion.revisar("guion-tradicion-pan").startswith("OK")


def test_la_fabrica_conoce_el_formato():
    from dato_mata_gato_bot import bot

    funcion, vigencia = fabrica.FORMULAS_REDES["tradiciones"]
    assert callable(getattr(fabrica, funcion)) and vigencia == "perenne"
    assert "tradiciones" not in fabrica.MEZCLA_REDES  # /lotegrande sin formato no lo mezcla
    assert bot._FORMULAS_VIRALES["tradiciones"]["comando"] == "tradicion"


def test_el_pipeline_desvia_al_render_3d(tmp_path, monkeypatch):
    """Voz, Whisper y render los hace render.py; aquí: portada, proyecto y archivo."""
    monkeypatch.setattr(pipeline, "ANDROID_IN", tmp_path / "in")
    monkeypatch.setattr(pipeline, "NARRATOR_PROJECTS", tmp_path / "proyectos")
    monkeypatch.setattr(pipeline, "TRADICIONES_DIR", tmp_path / "3d")
    monkeypatch.setattr(fabrica, "asegurar_infra", lambda: None)
    monkeypatch.setattr(pipeline, "_portadas", lambda slug, final: "portada C (el gancho) en el primer cuadro")
    slug = "guion-tradicion-pan"
    (tmp_path / "in" / slug).mkdir(parents=True)
    (tmp_path / "in" / slug / "guion.json").write_text(json.dumps(_guion(), ensure_ascii=False), encoding="utf-8")
    llamadas = []

    def falso_run(args, **kw):
        llamadas.append(args)
        salida = tmp_path / "3d" / "out" / f"{slug}.mp4"
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_bytes(b"0" * 200_000)
        return subprocess.CompletedProcess(args, 0, "voz lista: 70.0 s de audio, en 900 s\nrender: 60 s\nRENDER x", "")

    monkeypatch.setattr(pipeline.subprocess, "run", falso_run)
    monkeypatch.setattr(pipeline, "_kick_off_a1111_if_needed", lambda: (_ for _ in ()).throw(AssertionError("A1111")))
    r = pipeline.run(slug, "am_adam", destino_local=tmp_path / "lote")

    assert r.ok, r.mensaje
    assert Path(llamadas[0][1]).name == "render.py" and llamadas[0][2] == slug
    archivados = list((tmp_path / "lote").glob("*.mp4"))
    assert len(archivados) == 1 and "pan" in archivados[0].name.lower()
    assert "render: 3D de tradiciones" in r.mensaje and "gancho" in r.mensaje
    assert (tmp_path / "proyectos" / slug / "guion.json").exists()


def test_un_guion_roto_no_llega_a_la_voz(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "ANDROID_IN", tmp_path)
    g = _guion()
    g["escenas"][0]["visual"] = [{"objeto": "Dron"}]
    (tmp_path / "guion-tradicion-x").mkdir()
    (tmp_path / "guion-tradicion-x" / "guion.json").write_text(json.dumps(g), encoding="utf-8")
    monkeypatch.setattr(fabrica, "asegurar_infra", lambda: (_ for _ in ()).throw(AssertionError("no debía pedir voz")))
    r = pipeline.run("guion-tradicion-x", "am_adam")
    assert not r.ok and "Dron" in r.mensaje


TEXTO_WIKI = ("El pan de muerto es un pan dulce que se elabora en México durante el Día de Muertos. "
              "Las tiras de la superficie representan los huesos y la bolita el cráneo del difunto. "
              "Se dice que la cruz representa los cuatro rumbos del universo. ") * 4


def test_datos_marcados_y_el_bloque(monkeypatch):
    monkeypatch.setattr(ia_gratis, "pedir", lambda *a, **k: {"datos": [
        {"dato": "huesos", "cita": "Las tiras de la superficie representan los huesos", "nota": 0, "tipo": "hecho"},
        {"dato": "rumbos", "cita": "la cruz representa los cuatro rumbos del universo", "nota": 0, "tipo": "saber_popular"},
        {"dato": "sin tipo", "cita": "se elabora en México durante el Día de Muertos", "nota": 0}]})
    notas = [{"medio": "es.wikipedia.org", "liga": "https://es.wikipedia.org/wiki/Pan_de_muerto", "texto": TEXTO_WIKI}]
    datos = expediente.datos("pan", notas, tipos=True)
    assert [d["tipo"] for d in datos] == ["hecho", "saber_popular", "saber_popular"]
    texto = expediente_tradiciones.bloque({"temas": [{"titulo": "¿Por qué el pan…?", "objeto": "pan de muerto",
                                                       "notas": notas, "datos": datos}]})
    assert "✔ HECHO" in texto and "🗣 SABER POPULAR" in texto and "Pan_de_muerto" in texto


def test_sin_ia_gratis_la_instruccion_va_igual(monkeypatch):
    monkeypatch.setenv("FABRICA_EXPEDIENTE", "1")

    def sin_ia(*a, **k):
        raise ia_gratis.SinIA("sin red")

    monkeypatch.setattr(ia_gratis, "pedir", sin_ia)
    assert expediente_tradiciones.agregar("INSTRUCCION", None, 2, "") == "INSTRUCCION"


def test_el_agente_de_wikipedia_es_ascii():
    """30/10/2026: con "investigación" en el User-Agent, httpx tronaba antes de
    salir a la red y la corrida real no trajo ni un artículo de Wikipedia."""
    expediente_tradiciones.AGENTE["User-Agent"].encode("ascii")


def test_solo_fuentes_de_confianza():
    assert expediente_tradiciones.confiable("https://www.inah.gob.mx/boletines/pan")
    assert expediente_tradiciones.confiable("https://historicas.unam.mx/x.pdf")
    assert not expediente_tradiciones.confiable("https://www.recetasgratis.net/pan")
