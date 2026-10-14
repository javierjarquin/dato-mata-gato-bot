"""Los lotes: crimen lo escribe Claude, trivia sale del banco, y salen juntos.

Desde el 14/09/2026 las trivias NO pasan por Claude: son una plantilla sobre
el banco de preguntas aprobadas. Los dos tipos comparten el mismo helper y
terminan en el mismo pending_batch, así que /generarlote los genera como un
solo lote.
"""

import asyncio
from unittest.mock import patch

from dato_mata_gato_bot import bot


class _Msg:
    def __init__(self, text):
        self.text = text
        self.replies = []

    async def reply_text(self, texto, **kwargs):
        self.replies.append(texto)


class _Update:
    def __init__(self, chat_id=1, text="/crimen"):
        self.effective_chat = type("C", (), {"id": chat_id})()
        self.message = _Msg(text)


class _Ctx:
    def __init__(self, args=None):
        self.args = args or []


def _correr(cmd, update, ctx, trivias=None):
    """Corre un comando interceptando Claude y el generador de trivias.

    Devuelve (mensaje_a_claude, cantidad_pedida_al_banco, lote_guardado).
    """
    espia = {"claude": "", "trivias": None, "lote": None}

    def _fake_run_turn(session_id, mensaje, is_new, *_):
        espia["claude"] = mensaje
        return type("R", (), {"ok": False, "text": "cortado a proposito"})()

    def _fake_trivias(cantidad, session_id, is_new):
        espia["trivias"] = cantidad
        return (trivias if trivias is not None else []), ""

    with patch.object(bot, "run_turn", _fake_run_turn), \
         patch.object(bot, "_generar_trivias", _fake_trivias), \
         patch.object(bot.sessions, "get_generating", lambda c: (False, None)), \
         patch.object(bot.sessions, "set_generating", lambda c, v: None), \
         patch.object(bot.sessions, "ensure_session_id", lambda c: ("sid", True)), \
         patch.object(bot.sessions, "set_pending_batch",
                      lambda c, s: espia.__setitem__("lote", s)), \
         patch.object(bot, "ALLOWED_CHAT_IDS", {1}):
        asyncio.run(cmd(update, ctx))
    return espia


def test_crimen_se_lo_pide_a_claude():
    espia = _correr(bot.cmd_crimen, _Update(text="/crimen"), _Ctx())
    assert "true crime mexicano" in espia["claude"]
    assert espia["trivias"] is None   # no toca el banco


def test_trivia_sale_del_banco_y_no_llama_a_claude():
    # Es el punto de todo el generador: una trivia no necesita que un modelo
    # escriba el guion, la estructura es siempre la misma.
    espia = _correr(bot.cmd_trivia, _Update(text="/trivia"), _Ctx(args=["2"]))
    assert espia["claude"] == ""
    assert espia["trivias"] == 2


def test_el_lote_mixto_usa_las_dos_fuentes():
    trivias = [{"slug": "trivia-forense-01", "titulo": "T", "resumen_hechos": "..."}]
    with patch.object(bot.publish_schedule, "contar_por_tipo",
                      lambda: {"crimen": 0, "trivia": 0}):
        espia = _correr(bot.cmd_lote, _Update(text="/lote"), _Ctx(args=["5"]), trivias=trivias)
    # 3 de crimen a Claude, 2 de trivia al banco. El fake de Claude devuelve
    # error a propósito: el tramo de trivia tiene que correr igual.
    assert "3 guiones" in espia["claude"].replace("Generá 3", "3 guiones")
    assert espia["trivias"] == 2


def test_los_dos_tipos_terminan_en_el_mismo_lote():
    # Si no comparten pending_batch, /generarlote los trata como lotes
    # distintos y deja de ser un lote mixto.
    trivias = [{"slug": "trivia-forense-01", "titulo": "T", "resumen_hechos": "..."}]

    def _fake_run_turn(session_id, mensaje, is_new, *_):
        return type("R", (), {
            "ok": True,
            "text": '{"guiones": [{"slug": "guion-caso", "titulo": "C"}]}',
        })()

    espia = {"lote": None}
    # guion-caso no existe en disco: acá se prueba la mezcla del lote, no la
    # revisión de nombres/evidencia (esa tiene sus tests en test_revision_guion).
    with patch.object(bot, "run_turn", _fake_run_turn), \
         patch.object(bot, "_problemas_de", lambda s: []), \
         patch.object(bot, "_generar_trivias", lambda n, s, i: (trivias, "")), \
         patch.object(bot.publish_schedule, "contar_por_tipo",
                      lambda: {"crimen": 0, "trivia": 0}), \
         patch.object(bot.sessions, "get_generating", lambda c: (False, None)), \
         patch.object(bot.sessions, "set_generating", lambda c, v: None), \
         patch.object(bot.sessions, "ensure_session_id", lambda c: ("sid", True)), \
         patch.object(bot.sessions, "set_pending_batch",
                      lambda c, s: espia.__setitem__("lote", s)), \
         patch.object(bot, "ALLOWED_CHAT_IDS", {1}):
        asyncio.run(bot.cmd_lote(_Update(text="/lote"), _Ctx(args=["2"])))

    assert espia["lote"] == ["guion-caso", "trivia-forense-01"]


def test_un_banco_vacio_no_tumba_la_parte_de_crimen():
    # Falta de preguntas cargadas no puede costar el lote entero.
    def _fake_run_turn(session_id, mensaje, is_new, *_):
        return type("R", (), {
            "ok": True,
            "text": '{"guiones": [{"slug": "guion-caso", "titulo": "C"}]}',
        })()

    espia = {"lote": None, "avisos": []}
    upd = _Update(text="/lote")
    with patch.object(bot, "run_turn", _fake_run_turn), \
         patch.object(bot, "_problemas_de", lambda s: []), \
         patch.object(bot, "_generar_trivias", lambda n, s, i: ([], "el banco está vacío")), \
         patch.object(bot.publish_schedule, "contar_por_tipo",
                      lambda: {"crimen": 0, "trivia": 0}), \
         patch.object(bot.sessions, "get_generating", lambda c: (False, None)), \
         patch.object(bot.sessions, "set_generating", lambda c, v: None), \
         patch.object(bot.sessions, "ensure_session_id", lambda c: ("sid", True)), \
         patch.object(bot.sessions, "set_pending_batch",
                      lambda c, s: espia.__setitem__("lote", s)), \
         patch.object(bot, "ALLOWED_CHAT_IDS", {1}):
        asyncio.run(bot.cmd_lote(upd, _Ctx(args=["2"])))

    assert espia["lote"] == ["guion-caso"]
    assert any("banco" in r for r in upd.message.replies)


def test_si_falta_banco_se_rellena_dentro_del_mismo_lote():
    """El banco es un caché, no un trámite: si no alcanza para las trivias del
    lote, se piden preguntas y se sigue. No hay comando aparte."""
    from dato_mata_gato_bot import bot as b

    llamadas = {"relleno": 0, "generadas": 0}

    def _fake_temas(por_video):
        # Primera consulta: no hay temas. Segunda (tras el relleno): hay uno.
        listos = ["forense"] if llamadas["relleno"] else []
        return {}, set(), listos

    def _fake_rellenar(faltan, session_id, is_new):
        llamadas["relleno"] += 1
        return "6 pregunta(s) nuevas al banco"

    def _fake_generar(cantidad, destino, preguntas=6):
        llamadas["generadas"] = cantidad
        return []

    with patch.object(b, "_temas_listos", _fake_temas), \
         patch.object(b, "_rellenar_banco", _fake_rellenar), \
         patch.object(b.trivia_generator, "generar", _fake_generar):
        guiones, aviso = b._generar_trivias(1, "sid", False)

    assert llamadas["relleno"] == 1
    assert llamadas["generadas"] == 1
    assert "nuevas al banco" in aviso
    assert guiones == []
