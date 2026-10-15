"""Corre /lotefish3 desde la consola, con el código real del bot, y completa
el lote si la revisión sacó guiones.

La revisión (revision_guion) deja fuera los guiones que no cumplen nombres,
lugar exacto o evidencia, así que un /lotefish3 5 puede terminar con 3 (pasó
el 29/09/2026). Esto pide los que faltan UNA vez más, acumulando en el mismo
lote; si siguen faltando, avisa y no insiste (cada ronda cuesta tokens).

Lo que el bot le respondería al usuario se manda igual por Telegram.

Uso:  python tools/lote_fish3.py 5
"""

import asyncio
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from dato_mata_gato_bot import bot, formatos, sessions  # noqa: E402

CHAT_ID = int(os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "0").split(",")[0])
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class _Mensaje:
    text = "/lotefish3"

    async def reply_text(self, texto, **kwargs):
        print(texto, "\n", flush=True)
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            return
        for i in range(0, len(texto), 4000):  # límite de Telegram por mensaje
            datos = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": texto[i:i + 4000]}).encode()
            try:
                urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage",
                                       datos, timeout=30)
            except Exception as exc:  # noqa: BLE001
                print(f"  (no llegó a Telegram: {exc})")


class _Update:
    effective_chat = type("C", (), {"id": CHAT_ID})()
    message = _Mensaje()


class _Ctx:
    def __init__(self, args):
        self.args = args


async def main(n: int, completar: bool) -> None:
    """`completar`: el lote pendiente ya tiene guiones (una corrida cortada,
    03/10/2026: quedaron 2 de 5) y solo se piden los que faltan."""
    if not completar:
        await bot.cmd_lotefish3(_Update(), _Ctx([str(n)]))
    # Dos rondas como mucho: la revisión puede volver a sacar alguno, pero
    # insistir más es gastar tokens en casos que no tienen con qué.
    for _ in range(2):
        faltan = n - len(sessions.get_pending_batch(CHAT_ID))
        if faltan <= 0:
            break
        await _Update.message.reply_text(
            f"El lote tiene {n - faltan} de {n}. Pido {faltan} más para completarlo.")
        await bot._pedir_lote(_Update(), _Ctx([]), formatos.repartir_fish3, cantidad=faltan,
                              acumular=True, sin_avatar=True)
    print("LOTE:", sessions.get_pending_batch(CHAT_ID), flush=True)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    asyncio.run(main(int(args[0]) if args else 5, "--completar" in sys.argv))
