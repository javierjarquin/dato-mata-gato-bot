"""Tradiciones en un turno de Claude (22/11/2026)."""

import json

import pytest

from dato_mata_gato_bot import claude_runner, tradiciones_guion as tg


def _tema(slug="guion-tradicion-flor"):
    return {"titulo": "¿Por qué ponemos cempasúchil?", "objeto": "flor de cempasúchil", "protagonista": "Flor",
            "slug": slug, "motivo": "su nombre",
            "notas": [{"medio": "es.wikipedia.org", "liga": "https://es.wikipedia.org/wiki/Tagetes_erecta",
                       "texto": "Su nombre viene del náhuatl cempoalxóchitl, veinte flores."}],
            "datos": [{"nota": 0, "comprobada": True, "tipo": "hecho", "dato": "veinte flores",
                       "cita": "veinte flores"}]}


@pytest.fixture
def entrada(tmp_path, monkeypatch):
    monkeypatch.setattr(tg.pipeline, "ANDROID_IN", tmp_path)
    return tmp_path


def test_armar_deja_fuera_lo_ya_hecho_y_lo_flaco(entrada, monkeypatch):
    flaco = {**_tema(), "titulo": "¿Por qué el copal?", "objeto": "copal", "datos": []}
    hecho = {**_tema(), "titulo": "¿Por qué el pan?", "objeto": "pan de muerto",
             "datos": _tema()["datos"] * 3}
    bueno = {**_tema(), "datos": _tema()["datos"] * 3}
    (entrada / "guion-tradicion-pan-de-muerto").mkdir()
    (entrada / "guion-tradicion-pan-de-muerto" / "guion.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(tg.expediente_tradiciones, "armar",
                        lambda tema, n, ya: {"temas": [flaco, hecho, bueno], "modelos": ["gemini"]})
    temas, _ = tg.armar(None, 2, "")
    assert [t["slug"] for t in temas] == ["guion-tradicion-flor-de-cempasuchil"]


def test_la_instruccion_es_de_un_guion_con_su_expediente():
    texto = tg.instruccion(_tema())
    assert "UN guion" in texto and "<<" not in texto
    assert 'el slug ya es "guion-tradicion-flor"' in texto
    assert "https://es.wikipedia.org/wiki/Tagetes_erecta" in texto
    assert "AL TERMINAR" not in texto and "Escríbelo en C:" not in texto
    assert '{"objeto": "Flor"}' in texto


def test_una_liga_que_no_se_leyo_no_pasa(monkeypatch):
    monkeypatch.setattr(tg.formula, "problemas", lambda g: [])
    guion = {"_schema": {"fuentes": {"nombre": "Wikipedia, https://es.wikipedia.org/wiki/Tagetes_erecta",
                                     "mito": "inventada https://otra.com/mito"}}}
    assert tg.problemas(guion, _tema()) == [
        "mito: la liga https://otra.com/mito no es del expediente; usa solo las páginas que te di"]


def test_escribe_corrige_solo_lo_que_falla_y_guarda(entrada, monkeypatch):
    respuestas = iter([
        json.dumps({"titulo": "x", "escenas": [{"id": "a", "texto": "uno"}, {"id": "b", "texto": "dos"}]}),
        json.dumps({"escenas": [{"id": "b", "texto": "dos bien"}]}),
    ])
    mensajes = []

    def turno(sesion, mensaje, is_new_session, **kw):
        mensajes.append((mensaje, is_new_session, kw.get("herramientas")))
        return claude_runner.ClaudeTurnResult(ok=True, text=next(respuestas), raw="")
    monkeypatch.setattr(tg.claude_runner, "run_turn", turno)
    monkeypatch.setattr(tg.formula, "problemas",
                        lambda g: [] if g["escenas"][1]["texto"] == "dos bien" else ["b: mal"])
    g = tg.escribir(_tema())
    assert g.paso and g.turnos == 2
    assert [m[1] for m in mensajes] == [True, False] and all(m[2] == "" for m in mensajes)
    assert "b: mal" in mensajes[1][0]
    guardado = json.loads((entrada / "guion-tradicion-flor" / "guion.json").read_text(encoding="utf-8"))
    assert guardado["formato"] == "tradiciones" and guardado["slug"] == "guion-tradicion-flor"
    assert [e["texto"] for e in guardado["escenas"]] == ["uno", "dos bien"]


def test_lote_se_corta_con_el_cli_viejo(entrada, monkeypatch):
    monkeypatch.setattr(tg, "armar", lambda tema, n, ya: ([_tema("guion-tradicion-a"), _tema("guion-tradicion-b")],
                                                          {"modelos": []}))
    viejo = "API Error: 400 Claude Code 2.1.220 does not support this model; version 2.1.280 or newer is required"
    monkeypatch.setattr(tg.claude_runner, "run_turn",
                        lambda *a, **k: claude_runner.ClaudeTurnResult(ok=False, text=viejo, raw=""))
    hechos, limite = tg.lote(None, 2, "")
    assert len(hechos) == 1 and limite == viejo
    assert (entrada / "fabrica" / "tradiciones_tokens.csv").exists()


def test_sin_temas_avisa_para_volver_al_camino_de_antes(monkeypatch):
    monkeypatch.setattr(tg, "armar", lambda tema, n, ya: ([], {"modelos": []}))
    with pytest.raises(tg.ia_gratis.SinIA):
        tg.lote(None, 1, "")
