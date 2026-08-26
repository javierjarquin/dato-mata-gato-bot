"""_safe_reply: un aviso de progreso que falla (ReadTimeout/Bad Gateway de
Telegram, confirmado en una corrida real) no debe tirar abajo el comando
que lo llama -- antes, un solo aviso fallido mataba TODO /generarlote a
mitad de camino (2/5 videos generados bien, los otros 3 ni se intentaron
porque el traceback del aviso #2 mató la corrutina entera)."""

import asyncio

from dato_mata_gato_bot.bot import _safe_reply


class _FakeMessage:
    def __init__(self, should_fail: bool) -> None:
        self._should_fail = should_fail
        self.sent: list[str] = []

    async def reply_text(self, text: str) -> None:
        if self._should_fail:
            raise RuntimeError("ReadTimeout simulado")
        self.sent.append(text)


class _FakeUpdate:
    def __init__(self, should_fail: bool) -> None:
        self.message = _FakeMessage(should_fail)


def test_safe_reply_no_lanza_si_reply_text_falla():
    update = _FakeUpdate(should_fail=True)
    asyncio.run(_safe_reply(update, "hola"))  # no debe lanzar


def test_safe_reply_manda_el_texto_si_todo_ok():
    update = _FakeUpdate(should_fail=False)
    asyncio.run(_safe_reply(update, "hola"))
    assert update.message.sent == ["hola"]
