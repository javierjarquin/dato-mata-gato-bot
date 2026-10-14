"""Sesión ligera para escribir guiones y conteo de tokens sin duplicados (13/10/2026)."""

import json
import subprocess

from dato_mata_gato_bot import claude_runner, fabrica, herramientas_guion, instruccion_cercania


def _respuesta(i, ctx):
    u = {"input_tokens": 1, "cache_read_input_tokens": ctx, "cache_creation_input_tokens": 0, "output_tokens": 10}
    return {"type": "assistant", "message": {"id": f"msg_{i}", "usage": u, "content": []}}


def test_tokens_cuenta_cada_respuesta_una_vez(tmp_path, monkeypatch):
    monkeypatch.setattr(claude_runner, "carpeta_de_sesiones", lambda cwd: tmp_path)
    # Una respuesta con texto + 2 herramientas ocupa 3 líneas con el mismo usage.
    lineas = [_respuesta(1, 1000)] * 3 + [_respuesta(2, 2000)] * 2
    (tmp_path / "s1.jsonl").write_text("\n".join(json.dumps(x) for x in lineas), encoding="utf-8")
    tot = fabrica.tokens_de_sesiones(["s1"])
    assert tot["lectura_cache"] == 3000
    assert tot["salida"] == 20


def test_run_turn_ligera_usa_carpeta_limpia_y_pocas_herramientas(monkeypatch, tmp_path):
    visto = {}

    def falso(args, cwd, **kw):
        visto["args"], visto["cwd"] = args, cwd
        return subprocess.CompletedProcess(args, 0, stdout='{"result": "ok"}', stderr="")

    monkeypatch.setattr(claude_runner, "CWD_LIGERO", str(tmp_path / "escritura"))
    monkeypatch.setattr(claude_runner.subprocess, "run", falso)
    assert claude_runner.run_turn("sid", "hola", True, ligera=True).ok
    assert visto["cwd"] == str(tmp_path / "escritura")
    assert "--strict-mcp-config" in visto["args"]
    assert visto["args"][visto["args"].index("--tools") + 1] == claude_runner.HERRAMIENTAS_LIGERAS

    claude_runner.run_turn("sid", "hola", True)
    assert visto["cwd"] == claude_runner.CWD and "--tools" not in visto["args"]


def test_carpeta_de_sesiones_como_claude_code():
    assert claude_runner.carpeta_de_sesiones(r"C:\Android_in\fabrica\_escritura").name == \
        "C--Android-in-fabrica--escritura"
    assert claude_runner.carpeta_de_sesiones(r"C:\illustrated-narrator").name == "C--illustrated-narrator"


def test_instruccion_ligera_conserva_la_formula_y_agrega_como_trabajar():
    normal = instruccion_cercania.instruccion("cancun", 1, "(ninguno)")
    ligera = instruccion_cercania.instruccion("cancun", 1, "(ninguno)", ligera=True)
    assert "CÓMO TRABAJAR" not in normal and "CÓMO TRABAJAR" in ligera
    assert "herramientas_guion fotos" in ligera and "herramientas_guion revisar" in ligera
    assert "api.php?action=query" not in ligera
    for pieza in ("LA CONTRADICCIÓN LOCAL", "1. TE AFECTA", "4. CORAJE", "VERIFICACIÓN", "ESTRUCTURA (9 planos"):
        assert pieza in ligera


def test_sesion_ligera_por_defecto(monkeypatch):
    monkeypatch.delenv("FABRICA_SESION_LIGERA", raising=False)
    assert fabrica.sesion_ligera()
    monkeypatch.setenv("FABRICA_SESION_LIGERA", "0")
    assert not fabrica.sesion_ligera()


def _plano(i, texto):
    return {"id": f"p0{i}", "narracion": texto}


def test_problemas_de_forma():
    bien = " ".join(["palabra"] * 9) + "."
    planos = [_plano(i, bien if i == 0 else bien + " " + bien) for i in range(9)]
    assert herramientas_guion.problemas_de_forma({"planos": planos}) == []

    planos[0] = _plano(0, "En Cancún pagas 25 pesos y nadie te dice por qué pasa esto otra vez.")
    planos[3] = _plano(3, " ".join(["mucho"] * 22) + ".")
    out = " ".join(herramientas_guion.problemas_de_forma({"planos": planos[:8]}))
    assert "p00 a p08" in out
    assert "p00 tiene" in out and "cifras con número (25)" in out
    assert "frase de 22 palabras" in out


# --- /lotegrande con tema y bloque "plus" (13/10/2026) -----------------------

import asyncio
from types import SimpleNamespace

from dato_mata_gato_bot import bot


def _lotegrande(monkeypatch, args):
    pedido = {}

    async def falso(update, context, reparto, **kw):
        pedido["tramos"], pedido["kw"] = reparto(kw.get("cantidad")), kw

    respuestas = []

    async def responder(texto, **_):
        respuestas.append(texto)

    monkeypatch.setattr(bot, "_pedir_lote", falso)
    update = SimpleNamespace(message=SimpleNamespace(reply_text=responder))
    asyncio.run(bot.cmd_lotegrande(update, SimpleNamespace(args=args)))
    return pedido, respuestas


def test_lotegrande_con_tema_usa_la_formula_de_cercania(monkeypatch):
    for args in (["5", "cancun"], ["cancun", "5"], ["5", "Cancun"]):
        pedido, _ = _lotegrande(monkeypatch, args)
        assert pedido["tramos"] == [("cercania:cancun", "de Cancún y Quintana Roo (fórmula de cercanía)", 5)]
        assert pedido["kw"]["sin_avatar"] is True


def test_lotegrande_sin_tema_sigue_variado(monkeypatch):
    pedido, _ = _lotegrande(monkeypatch, ["4"])
    assert not any(t.startswith("cercania:") for t, _, _ in pedido["tramos"])
    assert sum(c for _, _, c in pedido["tramos"]) == 4


def test_lotegrande_tema_desconocido_explica_el_uso(monkeypatch):
    pedido, respuestas = _lotegrande(monkeypatch, ["5", "monterrey"])
    assert not pedido and "cancun" in respuestas[0]


def _guion_con_plus(plus):
    return {"planos": [{"id": f"p0{i}", "narracion": "Los anuncios oficiales no dicen cuándo abre."}
                       for i in range(9)], "plus": plus}


def test_plus_bien_formado_pasa():
    plus = {"contador": {"numero": 40, "antes": "HASTA", "despues": "BEBÉS AL DÍA"},
            "mapa": {"plano": "p02", "consulta": "Supermanzana 65, Cancún", "etiqueta": "SM 65 · CANCÚN"},
            "contradiccion": {"plano": "p04", "arriba": {"titulo": "A", "renglones": ["Hospital prometido"]},
                              "abajo": {"titulo": "B", "renglones": ["Sin fecha de apertura"]},
                              "abajo_en": "anuncios", "resaltar": "Sin fecha de apertura", "fuente": "X"}}
    assert herramientas_guion.problemas_de_plus(_guion_con_plus(plus)) == []


def test_plus_con_errores_se_explica():
    plus = {"contador": {"numero": "40", "despues": "BEBÉS"},
            "mapa": {"plano": "p12", "consulta": ""},
            "contradiccion": {"plano": "p00", "arriba": {"renglones": []},
                              "abajo": {"renglones": ["x" * 40]}, "abajo_en": "nunca", "resaltar": "otro"}}
    out = " | ".join(herramientas_guion.problemas_de_plus(_guion_con_plus(plus)))
    for pista in ("numero tiene que ser un número", 'mapa.plano "p12"', "consulta está vacía",
                  "uno de p01 a p07", "arriba: de 1 a 3", "pasa de 36 letras", "resaltar tiene que ser"):
        assert pista in out
    assert herramientas_guion.problemas_de_plus({"planos": []})[0].startswith('falta "plus"')
