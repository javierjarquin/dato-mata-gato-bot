"""Corre /completarlote desde la consola, con el código real del bot.

Lo que el bot le respondería al usuario se le manda igual por Telegram. Sirve
para retomar un lote sin tocar el teléfono, por el mismo camino que el comando.

Uso:  python tools/completar_lote.py
"""

import asyncio
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv  # noqa: E402

from dato_mata_gato_bot import bot  # noqa: E402

load_dotenv()
CHAT_ID = int(os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "0").split(",")[0])
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class _Mensaje:
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
    args = []


if __name__ == "__main__":
    asyncio.run(bot.cmd_completarlote(_Update(), _Ctx()))
