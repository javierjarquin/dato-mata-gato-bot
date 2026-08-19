"""Bot de Telegram que puentea la conversación a una sesión de Claude Code
por chat, para dirigir el pipeline de Dato Mata Gato desde el celular."""

import asyncio
import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from dato_mata_gato_bot import sessions
from dato_mata_gato_bot.claude_runner import run_turn
from dato_mata_gato_bot.logging_config import setup_logging

load_dotenv()  # antes de leer TELEGRAM_ALLOWED_CHAT_IDS a nivel de modulo

logger = logging.getLogger(__name__)

ANDROID_IN = Path(r"C:\Android_in")
TELEGRAM_MSG_LIMIT = 4000

INSTRUCCION_GUION = (
    "Se subió un guion.json nuevo para el proyecto '{slug}' en "
    r"C:\Android_in\{slug}\guion.json"
    ". Generá el audio (tts-kokoro, voz pm_santa, velocidad 1.15) y el video "
    "completo siguiendo el pipeline documentado en CLAUDE.md, revisando "
    "coherencia de país en los medios reales antes de darlo por terminado. "
    "Avisame cuando esté listo en Android_out, o si algo falla."
)

INSTRUCCION_IMAGEN = (
    "Imagen recibida, guardada en {path}. Instrucción del usuario: {caption}\n"
    "Proyecto actual: {slug}"
)


def _load_allowed_ids() -> set[int]:
    raw = os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").strip()
    if not raw:
        return set()
    return {int(x.strip()) for x in raw.split(",") if x.strip()}


ALLOWED_CHAT_IDS = _load_allowed_ids()


def _authorized(chat_id: int) -> bool:
    return chat_id in ALLOWED_CHAT_IDS


async def _reject_unauthorized(update: Update) -> None:
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"Este chat no está autorizado todavía.\n\n"
        f"Tu chat_id es: `{chat_id}`\n\n"
        f"Agrégalo a TELEGRAM_ALLOWED_CHAT_IDS en el .env del bot y reinícialo.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def _send_long(update: Update, text: str) -> None:
    if not text:
        text = "(sin salida)"
    for i in range(0, len(text), TELEGRAM_MSG_LIMIT):
        await update.message.reply_text(text[i : i + TELEGRAM_MSG_LIMIT])


async def _dispatch_to_claude(update: Update, message: str) -> None:
    chat_id = update.effective_chat.id
    session_id, is_new = sessions.ensure_session_id(chat_id)
    await update.message.reply_text(
        "Recibido, trabajando en esto — puede tardar varios minutos si involucra "
        "generar audio/video. Aviso cuando termine."
    )
    result = await asyncio.to_thread(run_turn, session_id, message, is_new)
    await _send_long(update, result.text)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return
    await update.message.reply_text(
        "Listo. Mándame un guion.json (como documento, con el slug en el "
        "texto o en el nombre del archivo) para generar un video nuevo, "
        "o escríbeme directo para seguir la conversación sobre el proyecto "
        "actual. /nuevo empieza una conversación desde cero."
    )


async def cmd_nuevo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return
    sessions.reset_session(chat_id)
    await update.message.reply_text("Conversación reiniciada.")


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".bmp"}


async def on_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    doc = update.message.document
    suffix = Path(doc.file_name or "").suffix.lower()

    if suffix in IMAGE_EXTENSIONS:
        # Telegram manda las fotos "sin comprimir" (adjuntadas como
        # archivo en vez de foto) como Document, no como PhotoSize --
        # mismo tratamiento que on_photo, no rechazarlas.
        tg_file = await doc.get_file()
        await _handle_image(update, chat_id, tg_file, doc.file_unique_id, suffix)
        return

    if suffix != ".json":
        await update.message.reply_text(
            f"Recibí un archivo ({doc.file_name}) que no reconozco — esperaba "
            f".json (guion) o una imagen ({', '.join(sorted(IMAGE_EXTENSIONS))})."
        )
        return

    caption = (update.message.caption or "").strip()
    slug = caption or Path(doc.file_name).stem
    slug = re.sub(r"[^a-zA-Z0-9_-]", "_", slug)

    dest_dir = ANDROID_IN / slug
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / "guion.json"

    tg_file = await doc.get_file()
    await tg_file.download_to_drive(custom_path=str(dest_path))

    sessions.set_slug(chat_id, slug)
    await update.message.reply_text(f"Guardado en {dest_path}. Slug: {slug}")
    await _dispatch_to_claude(update, INSTRUCCION_GUION.format(slug=slug))


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    photo = update.message.photo[-1]  # la de mayor resolución
    tg_file = await photo.get_file()
    await _handle_image(update, chat_id, tg_file, photo.file_unique_id, ".jpg")


async def _handle_image(update: Update, chat_id: int, tg_file, unique_id: str, suffix: str) -> None:
    slug = sessions.get_slug(chat_id)
    if not slug:
        await update.message.reply_text(
            "Todavía no sé de qué proyecto es esta imagen — mándame primero "
            "el guion.json de ese capítulo."
        )
        return

    caption = (update.message.caption or "").strip()
    staging = sessions.staging_dir_for(chat_id)
    dest_path = staging / f"{unique_id}{suffix}"
    await tg_file.download_to_drive(custom_path=str(dest_path))

    await update.message.reply_text(f"Imagen recibida y guardada en {dest_path}.")
    await _dispatch_to_claude(
        update, INSTRUCCION_IMAGEN.format(path=dest_path, caption=caption or "(sin texto)", slug=slug)
    )


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return
    await _dispatch_to_claude(update, update.message.text)


def main() -> None:
    setup_logging(os.getenv("LOG_LEVEL", "INFO"))

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Falta TELEGRAM_BOT_TOKEN en el .env")

    if not ALLOWED_CHAT_IDS:
        logger.warning(
            "TELEGRAM_ALLOWED_CHAT_IDS está vacío: nadie puede usar el bot todavía "
            "(seguro por defecto). Escríbele al bot para que te diga tu chat_id."
        )

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("nuevo", cmd_nuevo))
    app.add_handler(MessageHandler(filters.Document.ALL, on_document))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    logger.info("Bot arrancado, escuchando Telegram (polling)...")
    app.run_polling()


if __name__ == "__main__":
    main()
