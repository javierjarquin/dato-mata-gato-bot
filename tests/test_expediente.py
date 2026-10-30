"""Expediente previo a Claude (27/10/2026): sin red, con RSS y Gemini falsos."""

from datetime import datetime, timedelta, timezone

from dato_mata_gato_bot import expediente, ia_gratis

NOTA = ("El alcalde dijo que «el agua no se va a cortar en ninguna colonia» durante la "
        "conferencia del lunes, aunque Aguakan reportó 14 colonias sin servicio.") * 3


def test_cita_literal_se_comprueba_y_la_inventada_no(monkeypatch):
    monkeypatch.setattr(ia_gratis, "pedir", lambda *a, **k: {"datos": [
        {"dato": "promesa", "cita": "“el agua no se va a cortar en ninguna colonia”", "nota": 0},
        {"dato": "inventado", "cita": "el agua se cortará en 30 colonias", "nota": 0},
        {"dato": "nota que no existe", "cita": "x", "nota": 5}]})
    datos = expediente.datos("agua", [{"medio": "PorEsto", "texto": NOTA}])
    assert [d["comprobada"] for d in datos] == [True, False]  # las comillas no cuentan


def test_acepta_lista_sola_de_gemini(monkeypatch):
    monkeypatch.setattr(ia_gratis, "pedir", lambda *a, **k: [{"dato": "d", "cita": "14 colonias sin servicio", "nota": 0}])
    assert expediente.datos("agua", [{"medio": "m", "texto": NOTA}])[0]["comprobada"]


def test_sin_red_la_instruccion_va_igual(monkeypatch):
    monkeypatch.setenv("FABRICA_EXPEDIENTE", "1")
    monkeypatch.setattr(expediente, "candidatos", lambda *a, **k: [])
    assert expediente.agregar("INSTRUCCION", "cancun", None, 2, "") == "INSTRUCCION"
    assert expediente.agregar("INSTRUCCION", "polemica", "un tema de Javier", 2, "") == "INSTRUCCION"
    # Polémica y viral sin tema: Claude no busca por su cuenta (29/10/2026).
    import pytest
    with pytest.raises(expediente.SinTemasFrescos):
        expediente.agregar("INSTRUCCION", "polemica", None, 2, "")


def test_apagado_o_formula_de_archivo_no_sale_a_la_red(monkeypatch):
    monkeypatch.setattr(expediente, "armar", lambda *a, **k: (_ for _ in ()).throw(AssertionError("red")))
    monkeypatch.setenv("FABRICA_EXPEDIENTE", "0")
    assert expediente.agregar("I", "polemica", None, 2, "") == "I"
    monkeypatch.setenv("FABRICA_EXPEDIENTE", "1")
    assert expediente.agregar("I", "terror", None, 2, "") == "I"


def test_bloque_marca_lo_comprobado(monkeypatch):
    monkeypatch.setenv("FABRICA_EXPEDIENTE", "1")
    tema = {"titulo": "Cortes de agua", "medio": "PorEsto", "liga": "https://x", "motivo": "no cuadra",
            "fecha": datetime(2026, 10, 27, tzinfo=timezone.utc), "busqueda": "agua cancun"}
    monkeypatch.setattr(expediente, "candidatos", lambda *a, **k: [tema])
    monkeypatch.setattr(expediente, "escoger", lambda *a, **k: [dict(tema)])

    def investigar(t):
        t["notas"] = [{"medio": "PorEsto", "liga": "https://x", "texto": NOTA}]
        t["datos"] = [{"dato": "14 colonias", "cita": "14 colonias sin servicio", "nota": 0, "comprobada": True},
                      {"dato": "malo", "cita": "30 colonias", "nota": 0, "comprobada": False}]
    monkeypatch.setattr(expediente, "_investigar", investigar)

    def oficial(t, formula):
        t["oficial"] = [{"medio": "inegi.org.mx", "liga": "https://inegi.org.mx/b.pdf",
                         "datos": [{"dato": "23.7 %", "cita": "23.7 % de la población", "cifras_fuera": []}]}]
    monkeypatch.setattr(expediente, "_oficial", oficial)
    monkeypatch.setattr(expediente, "CARPETA", expediente.Path(__file__).parent / "_no_existe" / "x")
    texto = expediente.agregar("INSTRUCCION", "cancun", None, 1, "")
    assert texto.startswith("IMPORTANTE") and "INSTRUCCION\n\nEXPEDIENTE YA INVESTIGADO" in texto
    assert "✔ 14 colonias" in texto and "✘ NO está literal" in texto
    assert "TEMA 1: Cortes de agua — PorEsto 27/10/2026" in texto
    assert "DATO OFICIAL — inegi.org.mx" in texto and "✔ 23.7 % — «23.7 % de la población»" in texto


def test_rss_de_bing_saca_la_liga_real(monkeypatch):
    xml = (b'<rss><channel><item><title>Titular</title><pubDate>Mon, 26 Oct 2026 11:11:00 GMT</pubDate>'
           b'<link>http://www.bing.com/news/apiclick.aspx?ref=FexRss&amp;url=https%3a%2f%2fwww.poresto.net%2fnota</link>'
           b'</item></channel></rss>')

    class R:
        content = xml
        def raise_for_status(self):
            pass
    monkeypatch.setattr(expediente.httpx, "get", lambda *a, **k: R())
    [n] = expediente.bing_news("agua")
    assert n["liga"] == "https://www.poresto.net/nota" and n["medio"] == "poresto.net"


def test_sin_cuota_de_gemini_pasa_al_respaldo_con_llave(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.setenv("GROQ_API_KEY", "q")
    monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    monkeypatch.setattr(ia_gratis.time, "sleep", lambda s: None)
    llamadas = []

    class R:
        def __init__(self, url):
            self.status_code = 429 if "googleapis" in url else 200
            self.text = "cuota"
        def json(self):
            return {"choices": [{"message": {"content": '{"ok": 1}'}}]}

    def post(url, **k):
        llamadas.append(url)
        return R(url)
    monkeypatch.setattr(ia_gratis.httpx, "post", post)
    assert ia_gratis.pedir("hola", local=False) == {"ok": 1}
    assert "groq.com" in llamadas[-1]
    assert not any("cerebras" in u or "openrouter" in u for u in llamadas)


def test_es_cuota_solo_si_todos_fueron_429():
    assert ia_gratis.es_cuota("Gemini a: HTTP 429: x | Gemini b: HTTP 429: y | falta GROQ_API_KEY")
    assert not ia_gratis.es_cuota("Gemini a: HTTP 429: x | Gemini b: ConnectError")
    assert not ia_gratis.es_cuota("falta GEMINI_API_KEY")


def test_sin_cuota_gratis_pregunta_o_deja_a_claude(monkeypatch):
    monkeypatch.setenv("FABRICA_EXPEDIENTE", "1")
    monkeypatch.setattr(expediente, "candidatos", lambda *a, **k: [{"titulo": "t", "medio": "m", "liga": ""}])

    def sin_cuota(*a, **k):
        raise ia_gratis.SinIA("Gemini a: HTTP 429: quota")
    monkeypatch.setattr(ia_gratis, "pedir", sin_cuota)
    monkeypatch.setattr(expediente, "SI_SE_ACABA", "preguntar")
    try:
        expediente.agregar("I", "polemica", None, 1, "")
        assert False, "debió preguntar"
    except expediente.SinCuotaGratis:
        pass
    avisos = []
    monkeypatch.setattr(expediente, "SI_SE_ACABA", "claude")
    assert expediente.agregar("I", "polemica", None, 1, "", avisar=avisos.append) == "I"
    assert "Claude investiga" in avisos[0]


def test_la_fabrica_espera_la_cuota_gratis_salvo_con_iaclaude():
    from datetime import datetime, timedelta

    from dato_mata_gato_bot import fabrica
    ahora = datetime(2026, 10, 27, 18, 0)
    estado = {"ia_gratis_agotada": (ahora - timedelta(minutes=10)).isoformat()}
    assert fabrica.esperando_ia_gratis(estado, ahora)
    assert not fabrica.esperando_ia_gratis(estado, ahora + timedelta(minutes=fabrica.ESPERA_IA_GRATIS_MIN))
    assert not fabrica.esperando_ia_gratis({**estado, "sin_ia_gratis": "claude"}, ahora)
    assert not fabrica.esperando_ia_gratis({}, ahora)


def test_lo_que_no_cuadra_pasa_a_la_hermana(monkeypatch, tmp_path):
    """27/10/2026: "si no entra en un tema se valida en el otro"."""
    monkeypatch.setattr(expediente, "CARPETA", tmp_path)
    titulares = [{"titulo": "Influencer se burla de madres buscadoras", "medio": "m", "liga": "", "fecha": None},
                 {"titulo": "Dicen que Komanche se quitó la vida", "medio": "m", "liga": "", "fecha": None}]
    monkeypatch.setattr(expediente, "candidatos", lambda *a, **k: list(titulares))
    monkeypatch.setattr(ia_gratis, "pedir", lambda *a, **k: {"elegidos": [
        {"i": 0, "motivo": "frase", "busqueda": "b", "formula": "polemica"},
        {"i": 1, "motivo": "hay dictamen", "busqueda": "b", "formula": "viral"}]})
    monkeypatch.setattr(expediente, "_investigar", lambda t: t.update(notas=[], datos=[]))
    monkeypatch.setattr(expediente, "_oficial", lambda t, f: None)
    exp = expediente.armar("polemica", None, 1, "")
    assert [t["titulo"] for t in exp["temas"]] == ["Influencer se burla de madres buscadoras"]
    bolsa = expediente.de_la_bolsa("viral")
    assert [t["titulo"] for t in bolsa] == ["Dicen que Komanche se quitó la vida"]
    assert "no cuadró en polemica" in bolsa[0]["tendencia"]
    assert expediente.de_la_bolsa("viral") == []  # ya tuvo su vuelta


def test_la_bolsa_aguanta_dos_vueltas(monkeypatch, tmp_path):
    """27/10/2026: la segunda escritura llevaba las fechas ya leídas como datetime."""
    from datetime import datetime
    monkeypatch.setattr(expediente, "CARPETA", tmp_path)
    tema = {"titulo": "uno", "medio": "m", "liga": "", "fecha": datetime.now() - timedelta(days=1), "motivo": "x"}
    expediente.a_la_bolsa("viral", [tema])
    expediente.a_la_bolsa("viral", [{**tema, "titulo": "dos"}])
    assert [t["titulo"] for t in expediente.de_la_bolsa("viral")] == ["dos", "uno"]


def test_la_bolsa_tira_las_notas_de_mas_de_3_dias(monkeypatch, tmp_path):
    """29/10/2026: guardado hace 3 días con nota de hace 3 = tema de 6 días."""
    from datetime import datetime
    monkeypatch.setattr(expediente, "CARPETA", tmp_path)
    expediente.a_la_bolsa("viral", [{"titulo": "viejo", "medio": "m", "liga": "", "motivo": "x",
                                     "fecha": datetime.now() - timedelta(days=expediente.DIAS_REDES + 1)}])
    assert expediente.de_la_bolsa("viral") == []


def test_la_busqueda_inventada_se_cambia_por_el_titular():
    t = {"titulo": "Mbappé se disculpa tras ser cancelado en China por llamar dictador a Mao",
         "busqueda": "Moreno Cárdenas maestros impiden aprender SNTE"}
    assert expediente.consulta_de(t).startswith("Mbappé se disculpa")
    t["busqueda"] = "Mbappé disculpa China Mao"
    assert expediente.consulta_de(t) == "Mbappé disculpa China Mao"


def test_un_caso_un_tema():
    temas = [{"titulo": "China suspende LaLiga tras polémico comentario de Mbappé sobre Mao"},
             {"titulo": "Mbappé se disculpa tras ser cancelado en China por llamar dictador a Mao"},
             {"titulo": "Envenenan a perros en Parque España"}]
    assert [t["titulo"][:9] for t in expediente.sin_repetir(temas)] == ["China sus", "Envenenan"]


def test_lo_ya_hecho_no_vuelve_al_expediente():
    """27/10/2026: el expediente volvió a traer a las madres buscadoras de Izcalli."""
    hechos = [expediente._palabras("guion polemica gato madres buscadoras Dijo que su gato vale más "
                                   "que sus desaparecidos Yuli Salgado colectivo Cuautitlán Izcalli")]
    assert expediente.ya_hecho("Funan a influencer tras burlarse de un colectivo de madres buscadoras "
                               "en Cuautitlán Izcalli", hechos)
    assert not expediente.ya_hecho("Dalas Review dijo que Komanche no tuvo depresión", hechos)


def test_buscar_regresa_solo_lo_comprobado_y_sin_cifras_inventadas(monkeypatch):
    texto = "Relleno sin nada. " * 600 + "\n\n" + NOTA
    monkeypatch.setattr(expediente, "leer", lambda liga, tope=None: texto if "porest" in liga else None)
    pedidos = []

    def pedir(prompt, **k):
        pedidos.append((prompt, k))
        return {"datos": [
            {"dato": "14 colonias", "cita": "14 colonias sin servicio", "nota": 0},
            {"dato": "21 millones sin agua", "cita": "Aguakan reportó 14 colonias", "nota": 0},
            {"dato": "inventado", "cita": "30 colonias sin agua", "nota": 0}]}
    monkeypatch.setattr(ia_gratis, "pedir", pedir)
    salida = expediente.buscar("cuántas colonias sin agua", ["https://www.porest.net/x", "https://cerrada.mx/y"])
    assert "✔ 14 colonias — «14 colonias sin servicio»" in salida
    assert "✔ «Aguakan reportó 14 colonias»" in salida and "21 millones" not in salida
    assert "30 colonias" not in salida and "1 dato(s) tirado(s)" in salida
    assert "no abrió: https://cerrada.mx/y" in salida
    prompt, k = pedidos[0]
    assert len(prompt) < 8000 and "14 colonias" in prompt  # solo el pedazo que toca la pregunta
    assert k["reintentos"] == 1 and k["local"] is False


def test_buscar_sin_ligas_usa_la_web_y_sin_ia_da_el_pedazo(monkeypatch):
    monkeypatch.setattr(expediente, "web", lambda q: [{"liga": f"https://m{i}.mx", "medio": f"m{i}.mx", "titulo": ""}
                                                      for i in range(5)])
    monkeypatch.setattr(expediente, "leer", lambda liga, tope=None: NOTA)
    monkeypatch.setattr(ia_gratis, "pedir", lambda *a, **k: (_ for _ in ()).throw(ia_gratis.SinIA("HTTP 429")))
    salida = expediente.buscar("colonias sin agua")
    assert salida.count("[m") == 3 and "sin IA gratis" in salida and "14 colonias" in salida


def test_lo_que_toca_deja_el_parrafo_de_la_pregunta():
    texto = "\n\n".join(["Párrafo de relleno sobre otra cosa."] * 400 + ["La ENADIS reporta 23.7 % discriminada."])
    corto = expediente.lo_que_toca(texto, "porcentaje discriminada ENADIS", tope=500)
    assert "23.7 %" in corto and len(corto) <= 600


def test_pdf_se_lee_con_pdftotext(monkeypatch):
    class R:
        content, headers, text = b"%PDF-1.7 ...", {"content-type": "application/pdf"}, ""

        def raise_for_status(self):
            pass
    monkeypatch.setattr(expediente.httpx, "get", lambda *a, **k: R())
    monkeypatch.setattr(expediente, "_de_pdf", lambda c: "texto del pdf " * 100)
    assert expediente.leer("https://inegi.org.mx/x.pdf", tope=None).startswith("texto del pdf")


def test_dato_oficial_solo_de_paginas_oficiales(monkeypatch):
    monkeypatch.setattr(expediente, "web", lambda q: [
        {"liga": "https://www.eleconomista.com.mx/n", "medio": "eleconomista.com.mx"},
        {"liga": "https://www.inegi.org.mx/b.pdf", "medio": "inegi.org.mx"},
        {"liga": "https://qroo.gob.mx/x", "medio": "qroo.gob.mx"}])
    leidas = []
    monkeypatch.setattr(expediente, "leer", lambda liga, tope=None: leidas.append(liga) or NOTA)
    monkeypatch.setattr(ia_gratis, "pedir", lambda *a, **k: {"datos": [
        {"dato": "14 colonias", "cita": "14 colonias sin servicio", "nota": 1}]})
    t = {"titulo": "Cortes de agua en Cancún", "busqueda": ""}
    expediente._oficial(t, "comparativa")
    assert leidas == ["https://www.inegi.org.mx/b.pdf", "https://qroo.gob.mx/x"]
    assert [len(o["datos"]) for o in t["oficial"]] == [0, 1]
    assert not expediente.es_oficial("https://gob.mx.falso.com/x")


def test_comparativa_tiene_expediente():
    assert "comparativa" in expediente.FORMULAS and set(expediente.FORMULAS) <= set(expediente.OFICIAL)


def test_web_de_groq_saca_las_ligas_de_la_busqueda(monkeypatch):
    class R:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"executed_tools": [
                {"type": "browser_search", "search_results": {"results": [
                    {"url": "https://www.inegi.org.mx/b.pdf", "title": "Boletín"}, {"url": "no-es-liga"}]}},
                {"type": "browser.open", "search_results": {"results": [{"url": "https://otra.mx"}]}}]}}]}
    monkeypatch.setenv("GROQ_API_KEY", "x")
    monkeypatch.setattr(expediente.httpx, "post", lambda *a, **k: R())
    assert [r["liga"] for r in expediente.web("pobreza")] == ["https://www.inegi.org.mx/b.pdf"]


def test_la_misma_cita_no_se_repite(monkeypatch):
    monkeypatch.setattr(ia_gratis, "pedir", lambda *a, **k: {"datos": [
        {"dato": "a", "cita": "14 colonias sin servicio", "nota": 0},
        {"dato": "b", "cita": "14 colonias  sin servicio", "nota": 0}]})
    assert len(expediente.datos("agua", [{"medio": "m", "texto": NOTA}])) == 1


def test_tema_viejo_no_llega_a_claude(monkeypatch, tmp_path):
    """29/10/2026: un podcast del 05/10 con nota de hoy ("sigue la polémica")."""
    from datetime import datetime, timedelta

    import pytest
    monkeypatch.setattr(expediente, "CARPETA", tmp_path)
    hoy = datetime.now()
    titulares = [{"titulo": "Sigue la polémica por el podcast", "medio": "m", "liga": "", "fecha": None},
                 {"titulo": "Diputado ofende a maestros", "medio": "m", "liga": "", "fecha": None},
                 {"titulo": "Influencer se burla de enfermeras", "medio": "m", "liga": "", "fecha": None}]
    monkeypatch.setattr(expediente, "candidatos", lambda *a, **k: list(titulares))
    monkeypatch.setattr(expediente, "_oficial", lambda t, f: None)
    pedidos = []

    def pedir(prompt, **k):
        pedidos.append(prompt)
        return {"elegidos": [{"i": 0, "motivo": "x", "busqueda": "b", "desde": None},
                             {"i": 1, "motivo": "x", "busqueda": "b", "desde": f"{hoy:%d/%m/%Y}"},
                             {"i": 2, "motivo": "x", "busqueda": "b", "desde": "01/01/2020"}]}
    monkeypatch.setattr(ia_gratis, "pedir", pedir)
    monkeypatch.setattr(expediente, "_investigar", lambda t: t.update(notas=[{"medio": "m", "liga": "https://m.mx", "texto": "x"}], datos=[]))
    fechas = {"Sigue la polémica por el podcast": hoy - timedelta(days=24), "Diputado ofende a maestros": hoy}
    monkeypatch.setattr(expediente, "desde_cuando", lambda t: fechas[t["titulo"]])
    exp = expediente.armar("polemica", None, 2, "")
    assert "El HECHO tiene que haber empezado el" in pedidos[0]
    assert [t["titulo"] for t in exp["temas"]] == ["Diputado ofende a maestros"]  # la enfermera la tiró escoger
    assert exp["viejos"] and exp["viejos"][0].startswith("Sigue la polémica")
    assert "ya están filtrados" in expediente.bloque(exp).lower()

    fechas["Diputado ofende a maestros"] = hoy - timedelta(days=10)
    monkeypatch.setenv("FABRICA_EXPEDIENTE", "1")
    with pytest.raises(expediente.SinTemasFrescos, match="podcast"):
        expediente.agregar("I", "polemica", None, 2, "")
