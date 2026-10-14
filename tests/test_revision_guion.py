"""Nombres, lugar exacto y evidencia: se comprueban antes de generar.

El lote del 26/09/2026 salió con guiones sin UN SOLO nombre propio (Tierra
Blanca: "un vocero", "un comandante", "los jóvenes"; Colosio: ninguno), y la
audiencia decía que los videos parecían cuentos.
"""

import asyncio
import json

from dato_mata_gato_bot import bot, revision_guion

_EVID = [{"id": f"e{i}", "tipo": "lugar"} for i in range(3)]


def _guion(narraciones, evidencia=_EVID):
    return {"evidencia": evidencia, "planos": [
        {"id": f"p0{i}", "narracion": n, "visual": {"evidencia": ["e0"]}}
        for i, n in enumerate(narraciones)]}


BUENO = _guion([
    "Cinco jóvenes subieron a una patrulla en Tierra Blanca, Veracruz.",
    "Te imaginas a José Benítez de la O, que volvía de un cumpleaños.",
    "Luego cayó su jefe, Marcos Conde Hernández, delegado de Seguridad Pública.",
    "El fiscal Luis Ángel Bravo dijo que un testigo lo confirmó.",
])


def test_un_guion_con_nombres_lugar_y_evidencia_pasa():
    assert revision_guion.problemas(BUENO) == []


def test_sin_nombres_no_pasa():
    """El Tierra Blanca del 26/09/2026, tal cual."""
    g = _guion(["Una cámara grabó a policías deteniendo a cinco jóvenes en Tierra Blanca.",
                "Un comandante les dijo que ahí no había pasado nada."])
    assert any("nombre" in p for p in revision_guion.problemas(g))


def test_solo_el_estado_no_es_lugar_exacto():
    g = _guion(["José Benítez de la O, Luis Ángel Bravo y Marcos Conde Hernández en Veracruz."])
    assert any("lugar exacto" in p for p in revision_guion.problemas(g))


def test_instituciones_y_lugares_no_cuentan_como_personas():
    nombres = revision_guion.nombres_de_persona(_guion(
        ["La Policía Estatal de Veracruz y Seguridad Pública llegaron a Playa Vicente."]))
    assert nombres == set()


def test_sin_evidencia_real_no_pasa():
    g = dict(BUENO, evidencia=[{"id": "e0", "tipo": "ficha"}])
    assert any("evidencia" in p for p in revision_guion.problemas(g))


def test_cuatro_nombres_en_una_frase_no_pasa():
    """La voz se comió a "Mario" en una lista así (Tierra Blanca, 28/09/2026)."""
    g = _guion(["Iba con Bernardo Benítez, José Alfredo González, Mario Arturo Orozco y "
                "Susana Tapia Garibo en Tierra Blanca."] + [p["narracion"] for p in BUENO["planos"]])
    assert any("más de dos nombres" in p for p in revision_guion.problemas(g))


def test_palabras_con_tl_no_van_en_la_voz():
    g = _guion([p["narracion"] for p in BUENO["planos"]] + ["Había restos en Tlalixcoyan."])
    assert any("Tlalixcoyan" in p for p in revision_guion.problemas(g))


class _Msg:
    def __init__(self):
        self.textos = []

    async def reply_text(self, t):
        self.textos.append(t)


class _Update:
    def __init__(self):
        self.message = _Msg()


def test_lo_que_sigue_fallando_sale_del_lote(tmp_path, monkeypatch):
    for slug, g in (("guion-bueno", BUENO), ("guion-cuento", _guion(["Un policía llegó."]))):
        (tmp_path / slug).mkdir()
        (tmp_path / slug / "guion.json").write_text(json.dumps(g), encoding="utf-8")
    monkeypatch.setattr(bot, "_problemas_de", lambda s: revision_guion.problemas(
        json.loads((tmp_path / s / "guion.json").read_text(encoding="utf-8"))))
    pedidos = []

    def _run_turn(session, texto, nuevo, *_):
        pedidos.append(texto)
        return type("R", (), {"ok": True, "text": "sin json"})()

    monkeypatch.setattr(bot, "run_turn", _run_turn)
    upd = _Update()
    guiones = [{"slug": "guion-bueno"}, {"slug": "guion-cuento"}]
    quedan = asyncio.run(bot._revisar_guiones_crimen(upd, "s", guiones, "de prueba"))
    assert [g["slug"] for g in quedan] == ["guion-bueno"]
    assert len(pedidos) == 1 and "guion-cuento" in pedidos[0]  # UNA ronda de corrección
    assert "guion-cuento" in upd.message.textos[0]


def test_si_todo_cumple_no_se_llama_a_claude(tmp_path, monkeypatch):
    (tmp_path / "guion-bueno").mkdir()
    (tmp_path / "guion-bueno" / "guion.json").write_text(json.dumps(BUENO), encoding="utf-8")
    monkeypatch.setattr(bot, "_problemas_de", lambda s: revision_guion.problemas(
        json.loads((tmp_path / s / "guion.json").read_text(encoding="utf-8"))))
    monkeypatch.setattr(bot, "run_turn", lambda *a: (_ for _ in ()).throw(AssertionError))
    assert asyncio.run(bot._revisar_guiones_crimen(_Update(), "s", [{"slug": "guion-bueno"}],
                                                  "x")) == [{"slug": "guion-bueno"}]
