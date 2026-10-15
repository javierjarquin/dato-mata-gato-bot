"""Modo automático de /lotegrande, noticia/perenne y "que envejezca bien" (14/10/2026)."""

import asyncio
import json
from datetime import datetime
from types import SimpleNamespace

from dato_mata_gato_bot import bot, fabrica, instruccion_cercania


def test_mezcla_tres_noticias_por_dos_perennes():
    assert instruccion_cercania.repartir_vigencias(5) == [("noticia", 3), ("perenne", 2)]
    assert dict(instruccion_cercania.repartir_vigencias(20)) == {"noticia": 12, "perenne": 8}
    # Compensa lo que ya hay: si sobran noticias, la tanda va a perennes.
    assert dict(instruccion_cercania.repartir_vigencias(2, {"noticia": 5, "perenne": 0})) == {"perenne": 2}


def test_instruccion_por_vigencia():
    noticia = instruccion_cercania.instruccion("cancun", 3, "-", vigencia="noticia",
                                               hoy=datetime(2026, 10, 14).date())
    perenne = instruccion_cercania.instruccion("cancun", 2, "-", vigencia="perenne")
    # Desde el 15/10/2026: tema de este mes que hace hablar (antes, noticia de 2 días).
    assert "ESTÁ HABLANDO" in noticia and "14/09/2026" in noticia and "HACE HABLAR" in noticia
    assert "SIGUE PASANDO" in perenne and "ESTÁ HABLANDO" not in perenne
    assert "DOS PREGUNTAS directas" in noticia and "DOS PREGUNTAS directas" in perenne
    for t in (noticia, perenne):
        assert "QUE ENVEJEZCA BIEN" in t and "VALOR PRÁCTICO" in t and "<<" not in t


def _guion(narracion, **schema):
    return {"planos": [{"id": "p00", "narracion": narracion}], "_schema": schema}


def test_tiempo_relativo_en_la_voz():
    out = fabrica.problemas_de_vigencia(_guion("Ayer cerraron la playa y esta semana sigue igual."))
    assert out and "'ayer'" in out[0] and "'esta semana'" in out[0]
    assert fabrica.problemas_de_vigencia(_guion("Esa mañana, en octubre de dos mil veintiséis, cerró.")) == []


def test_noticia_de_mas_de_un_mes_no_pasa():
    hoy = datetime(2026, 10, 14, 9)
    vieja = _guion("x", vigencia="noticia", impacto="lo más leído de PorEsto",
                   condiciones={"2_esta_pasando_ahorita": "PorEsto, 10/09/2026: cerró."})
    nueva = _guion("x", vigencia="noticia", impacto="lo más leído de PorEsto",
                   condiciones={"2_esta_pasando_ahorita": "PorEsto, 12/10/2026: cerró."})
    assert any("10/09/2026" in p for p in fabrica.problemas_de_vigencia(vieja, "noticia", hoy))
    assert fabrica.problemas_de_vigencia(nueva, "noticia", hoy) == []
    sin_impacto = _guion("x", vigencia="noticia", condiciones={"2_esta_pasando_ahorita": "13/10/2026"})
    assert any("impacto" in p for p in fabrica.problemas_de_vigencia(sin_impacto, "noticia", hoy))
    assert any('"perenne"' in p for p in fabrica.problemas_de_vigencia(nueva, "perenne", hoy))


def test_aviso_de_limite_semanal():
    ahora = datetime(2026, 10, 14, 6, 0)  # martes
    assert fabrica.hora_de_reset("weekly limit · resets Oct 20, 3pm", ahora) == datetime(2026, 10, 20, 15, 2)
    assert fabrica.hora_de_reset("resets Mon 9am", ahora) == datetime(2026, 10, 19, 9, 2)
    assert fabrica.hora_de_reset("session limit · resets 3:40pm", ahora) == datetime(2026, 10, 14, 15, 42)


def test_noticias_primero_en_la_fila():
    estado = {"videos": {"a": {"estado": "pendiente", "intentos": 0, "vigencia": "perenne"},
                         "b": {"estado": "pendiente", "intentos": 0, "vigencia": "noticia"},
                         "c": {"estado": "pendiente", "intentos": 0, "vigencia": "perenne"}}}
    assert fabrica.pendientes(estado) == ["b", "a", "c"]


def test_tanda_automatica_reparte_vigencias(monkeypatch):
    pedidos = []

    async def falso(avisador, clave, cant, ligera=None, vigencia=None):
        pedidos.append((clave, vigencia, cant))
        return [{"slug": f"guion-{clave}-{vigencia}-{i}"} for i in range(cant)], [f"s-{vigencia}"]

    monkeypatch.setattr(fabrica, "_guiones_de_cercania", falso)
    estado = {"objetivo": 20, "videos": {}, "guiones_pedidos": 0, "formato": "cercania",
              "tema": "cancun", "por_tanda": 6, "vigencias": True}
    nuevos, limite = fabrica.escribir_tanda(estado)
    assert limite is None and len(nuevos) == 6
    assert sorted(pedidos) == [("cancun", "noticia", 4), ("cancun", "perenne", 2)]
    assert estado["_vigencias"]["guion-cancun-noticia-0"] == "noticia"


def test_lotegrande_automatico_crea_la_fabrica(tmp_path, monkeypatch):
    monkeypatch.setattr(fabrica, "RAIZ", tmp_path)
    monkeypatch.setattr(bot, "_authorized", lambda chat: True)
    lanzados = []
    import subprocess
    monkeypatch.setattr(subprocess, "Popen", lambda args, **k: lanzados.append(args))
    respuestas = []

    async def responder(texto, **_):
        respuestas.append(texto)

    update = SimpleNamespace(effective_chat=SimpleNamespace(id=1),
                             message=SimpleNamespace(reply_text=responder))
    asyncio.run(bot.cmd_lotegrande(update, SimpleNamespace(args=["20", "0-9", "cancun"])))
    estados = list(tmp_path.glob("auto-*/estado.json"))
    assert len(estados) == 1
    e = json.loads(estados[0].read_text(encoding="utf-8"))
    assert (e["objetivo"], e["horas_claude"], e["tema"], e["vigencias"]) == (20, "0-9", "cancun", True)
    assert lanzados and lanzados[0][-2:] == ["ciclo", e["lote"]]
    assert "12 noticias + 8 perennes" in respuestas[0]

    # Con una activa no se crea otra: comparten la voz.
    asyncio.run(bot.cmd_lotegrande(update, SimpleNamespace(args=["5", "dia"])))
    assert len(list(tmp_path.glob("auto-*/estado.json"))) == 1 and "Ya hay una fábrica" in respuestas[-1]

    asyncio.run(bot.cmd_pararfabrica(update, SimpleNamespace(args=[])))
    assert json.loads(estados[0].read_text(encoding="utf-8"))["terminado"] is True


def test_tanda_cortada_no_cuenta_para_la_ventana(monkeypatch):
    monkeypatch.setenv("FABRICA_TANDAS_5H", "1")
    ahora = datetime(2026, 10, 14, 11, 0)
    cortada = {"horas_claude": "", "consumo": [{"t": "2026-10-14T09:13", "guiones": 4, "cortada": True}]}
    assert fabrica.puede_usar_claude(cortada, ahora) is None
    entera = {"horas_claude": "", "consumo": [{"t": "2026-10-14T09:13", "guiones": 6}]}
    assert "ya se pidieron" in fabrica.puede_usar_claude(entera, ahora)



def test_dos_preguntas_directas():
    planos = lambda **n: {"planos": [{"id": k, "narracion": v} for k, v in n.items()]}
    assert fabrica.problemas_de_preguntas(planos(p01="¿A ti ya te cobraron?", p04="¿Tú pagarías?")) == []
    sin_temprana = fabrica.problemas_de_preguntas(planos(p03="Nada.", p04="¿Tú pagarías?"))
    assert len(sin_temprana) == 1 and "segundo diez" in sin_temprana[0]
    sin_mitad = fabrica.problemas_de_preguntas(planos(p02="¿Y tú?, ¿lo sabías?"))
    assert len(sin_mitad) == 1 and "mitad" in sin_mitad[0]
