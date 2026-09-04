"""Los dos tipos de lote (/crimen y /trivia) comparten el mismo helper y solo
cambian la instrucción que se le manda a Claude."""

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


def _correr(coro):
    return asyncio.run(coro)


def _instruccion_enviada(update, ctx):
    """Corre el comando interceptando la llamada a Claude y devuelve el texto
    que se le habría mandado."""
    enviado = {}

    def _fake_run_turn(session_id, mensaje, is_new):
        enviado["mensaje"] = mensaje
        return type("R", (), {"ok": False, "text": "cortado a proposito"})()

    with patch.object(bot, "run_turn", _fake_run_turn), \
         patch.object(bot.sessions, "get_generating", lambda c: (False, None)), \
         patch.object(bot.sessions, "set_generating", lambda c, v: None), \
         patch.object(bot.sessions, "ensure_session_id", lambda c: ("sid", True)), \
         patch.object(bot, "ALLOWED_CHAT_IDS", {1}):
        _correr(bot.cmd_crimen(update, ctx) if update.message.text.startswith("/crimen")
                else bot.cmd_trivia(update, ctx))
    return enviado.get("mensaje", "")


def test_crimen_manda_la_instruccion_de_true_crime():
    mensaje = _instruccion_enviada(_Update(text="/crimen"), _Ctx())
    assert "true crime mexicano" in mensaje
    assert "pausa_despues_seg" not in mensaje


def test_trivia_manda_la_instruccion_de_preguntas():
    mensaje = _instruccion_enviada(_Update(text="/trivia"), _Ctx())
    assert "TRIVIA" in mensaje
    # Los campos propios del formato tienen que estar explicados, si no Claude
    # escribe un guion sin pausas ni cuenta regresiva.
    for campo in ("pausa_despues_seg", "texto_grande", "reloj", "busqueda_medios"):
        assert campo in mensaje, campo


def test_ambos_respetan_la_cantidad_pedida():
    for texto, cmd in (("/crimen", bot.cmd_crimen), ("/trivia", bot.cmd_trivia)):
        mensaje = _instruccion_enviada(_Update(text=texto), _Ctx(args=["3"]))
        assert "3 guiones" in mensaje.replace("Generá 3", "3 guiones"), texto


def test_la_instruccion_de_trivia_prohibe_revelar_la_respuesta_en_la_foto():
    # Una foto que muestre la respuesta arruina la pregunta.
    assert "no debe revelar la respuesta" in bot.INSTRUCCION_TRIVIA
