"""Papasia en un turno de Claude (15/11/2026): lo que no necesita ni a Claude ni
a la IA gratis."""

import json

from dato_mata_gato_bot import claude_runner, papasia_guion as pg

TEMA = {"titulo": "¿Por qué mi bebé tiene hipo tan seguido?", "slug": "guion-papasia-prueba-hipo",
        "protagonista": "Bebe", "busqueda": "hipo recién nacido",
        "notas": [{"liga": "https://www.healthychildren.org/Spanish/hipo.aspx", "medio": "healthychildren.org",
                   "texto": "El hipo es normal en los recién nacidos y no les molesta."}],
        "datos": [{"dato": "El hipo es normal", "cita": "El hipo es normal en los recién nacidos",
                   "nota": 0, "tipo": "hecho", "comprobada": True}]}


def test_la_instruccion_es_de_un_turno():
    texto = pg.instruccion(TEMA)
    assert "<<" not in texto                      # no quedó ningún hueco sin llenar
    assert "C:\\Android_in" not in texto          # Claude no escribe en disco
    assert "AL TERMINAR" not in texto
    assert "BIBLIOTECA" not in texto              # sin los modelos de tradiciones
    assert '"formato": "papasia"' in texto and "EXPEDIENTE" in texto
    assert TEMA["notas"][0]["liga"] in texto and "«El hipo es normal en los recién nacidos»" in texto
    assert len(texto) < 12000


def test_el_ejemplo_de_escena_pasa_la_revision():
    escena = json.loads(pg.EJEMPLO)
    assert pg.formula.problemas_de_escena(escena) == []


def test_una_correccion_cambia_solo_sus_escenas():
    guion = {"formato": "papasia", "titulo": "a", "escenas": [{"id": "uno", "texto": "x"}, {"id": "dos", "texto": "y"}],
             "_schema": {"fuentes": {"uno": "f1"}, "descartado": []}}
    nuevo = pg.aplicar(guion, {"escenas": [{"id": "dos", "texto": "z"}], "titulo": "b",
                               "_schema": {"fuentes": {"dos": "f2"}}})
    assert [e["texto"] for e in nuevo["escenas"]] == ["x", "z"]
    assert nuevo["titulo"] == "b" and nuevo["_schema"]["fuentes"] == {"uno": "f1", "dos": "f2"}
    entero = {"formato": "papasia", "escenas": [{"id": "tres"}]}
    assert pg.aplicar(guion, entero) is entero


def test_una_liga_que_no_se_leyo_se_rechaza():
    guion = {"formato": "papasia", "escenas": [], "_schema": {"fuentes": {
        "a": "lo dice la AAP: https://www.healthychildren.org/Spanish/hipo.aspx",
        "b": "lo dice la AAP: https://www.healthychildren.org/Spanish/inventada.aspx"}}}
    fuera = [p for p in pg.problemas(guion, TEMA) if "no es del expediente" in p]
    assert len(fuera) == 1 and "inventada" in fuera[0]


def test_escribe_corrige_y_anota(monkeypatch, tmp_path):
    monkeypatch.setattr(pg, "ANDROID_IN", tmp_path)
    monkeypatch.setattr(pg, "BITACORA", tmp_path / "fabrica" / "papasia_tokens.csv")
    revisiones = iter([["uno: falta algo"], []])
    monkeypatch.setattr(pg, "problemas", lambda guion, t: next(revisiones))
    turnos = []

    def run_turn(sesion, mensaje, is_new_session, **kw):
        turnos.append((mensaje, is_new_session, kw))
        respuesta = ({"formato": "papasia", "escenas": [{"id": "uno", "texto": "x"}]} if is_new_session
                     else {"escenas": [{"id": "uno", "texto": "corregida"}]})
        return claude_runner.ClaudeTurnResult(True, "```json\n" + json.dumps(respuesta) + "\n```", "")

    monkeypatch.setattr(pg.claude_runner, "run_turn", run_turn)
    g = pg.escribir(TEMA, contar_tokens=lambda s: {"total": 100, "salida": 40})
    assert g.paso and g.turnos == 2
    assert turnos[0][2]["herramientas"] == "" and turnos[0][2]["sistema"] == pg.SISTEMA
    assert "uno: falta algo" in turnos[1][0] and len(turnos[1][0]) < 800   # solo la lista de problemas
    guion = json.loads((tmp_path / TEMA["slug"] / "guion.json").read_text(encoding="utf-8"))
    assert guion["escenas"][0]["texto"] == "corregida"
    pg.anotar(g)
    assert json.loads((tmp_path / TEMA["slug"] / "tokens.json").read_text(encoding="utf-8"))["total"] == 100
    assert "guion-papasia-prueba-hipo" in pg.BITACORA.read_text(encoding="utf-8-sig")
    assert "100 tokens" in pg.renglon(g)


def test_las_claves_que_no_dice_la_voz_se_quitan_solas():
    guion = {"escenas": [{"id": "a", "texto": "Esto no sustituye a tu pediatra.", "claves": ["sustituye", "pediatra", "madrugada"]},
                         {"id": "b", "texto": "Hola bebé.", "claves": ["bebé", "cuna"]}]}
    pg.limpiar(guion)
    assert guion["escenas"][0]["claves"] == ["sustituye", "pediatra"]
    assert guion["escenas"][1]["claves"] == ["bebé", "cuna"]   # quedaría 1: lo corrige Claude


def test_la_fabrica_usa_el_turno_unico(monkeypatch):
    import asyncio

    from dato_mata_gato_bot import bot, fabrica

    avisos = []

    class Avisador:
        class message:
            @staticmethod
            async def reply_text(texto):
                avisos.append(texto)

    hechos = [pg.Guion("guion-papasia-a", tokens={"total": 25000, "salida": 6000}, sesion="s1", turnos=1),
              pg.Guion("guion-papasia-b", problemas=["algo"], sesion="s2", turnos=3)]
    monkeypatch.setattr(pg, "lote", lambda *a, **k: (hechos, None))
    monkeypatch.setattr(bot, "_ya_cubiertos", lambda prefijo: "(ninguno)")
    buenos, sesiones = asyncio.run(fabrica._guiones_papasia(Avisador(), None, 2))
    assert buenos == [{"slug": "guion-papasia-a", "vigencia": "perenne"}] and sesiones == ["s1", "s2"]
    assert "25,000 tokens" in avisos[0] and "no pasó" in avisos[0]

    monkeypatch.setattr(pg, "lote", lambda *a, **k: (hechos[:1], "You've hit your session limit · resets 3pm"))
    try:
        asyncio.run(fabrica._guiones_papasia(Avisador(), None, 2))
        raise AssertionError("tenía que cortar por el límite de Claude")
    except bot.LimiteDeClaude as exc:
        assert exc.slugs == ["guion-papasia-a"]
