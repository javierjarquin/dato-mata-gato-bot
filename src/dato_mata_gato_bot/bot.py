"""Bot de Telegram que puentea la conversación a una sesión de Claude Code
por chat, para dirigir el pipeline de Dato Mata Gato desde el celular.

Flujo por comandos (no todo dispara a Claude):
  /nuevovideo [slug]  -> modo recolección: guarda guion.json e imágenes
                         SIN invocar a Claude, es solo mover archivos.
  /generar            -> el único disparo real a Claude: corre el
                         pipeline completo con todo lo ya recolectado.
  /estatus             -> si hay una generación en curso y desde cuándo.
  /nuevo               -> reinicia la conversación con Claude desde cero.
Los mensajes de texto libres sí siguen la conversación con Claude
(para pedir ajustes después de generar), salvo que haya una generación
en curso.
"""

import asyncio
import logging
import os
import re
from datetime import datetime, timezone
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

from dato_mata_gato_bot import (
    auto_query,
    free_image_search,
    generated_videos,
    image_naming,
    pipeline,
    sessions,
    summary,
    wiki_images,
)
from dato_mata_gato_bot.claude_runner import run_turn
from dato_mata_gato_bot.logging_config import setup_logging

load_dotenv()  # antes de leer TELEGRAM_ALLOWED_CHAT_IDS a nivel de modulo

logger = logging.getLogger(__name__)

ANDROID_IN = Path(r"C:\Android_in")
TELEGRAM_MSG_LIMIT = 4000
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".bmp"}

# Catalogo de voces ya exploradas/probadas (ver tts-kokoro/projects/voces_exploracion).
VOICES = (
    "am_adam", "am_santa", "am_onyx", "am_michael", "am_fenrir",
    "bm_george", "pm_santa", "pm_alex", "em_santa", "em_alex", "ef_dora",
)

INSTRUCCION_ESCALAR = (
    "El pipeline automático (sin Claude) ya corrió para '{slug}' -- audio generado, "
    "proyecto armado en illustrated-narrator, y al menos una pasada de narrator generate "
    "con reintentos ya agotados. Esto quedó sin resolver:\n\n{detalle}\n\n"
    "Resolvelo vos siguiendo CLAUDE.md (investigar/ajustar busqueda_medios, o ficha de "
    "texto si no hay foto real, etc.), corré narrator generate las veces que haga falta "
    "TODO EN FOREGROUND, y copiá el resultado final a Android_out vos mismo. Avisame "
    "cuando esté listo, o si algo no se puede resolver."
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
        f"Este chat no está autorizado todavía.\n\nTu chat_id es: `{chat_id}`\n\n"
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
    sessions.set_generating(chat_id, True)
    try:
        result = await asyncio.to_thread(run_turn, session_id, message, is_new)
        await _send_long(update, result.text)
    finally:
        sessions.set_generating(chat_id, False)


def _slugify(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", text.strip())


HELP_TEXT = """Comandos disponibles — flujo típico: /nuevovideo → mandar guion.json → (opcional: fotos/logo/voz) → /generar

/nuevovideo [slug]
  Empieza un capítulo nuevo. Sin slug, se deriva del nombre del archivo que mandes después.
  Ejemplo: /nuevovideo elchalequero
  Después: mandale el guion.json como documento adjunto (no como texto pegado).

/generar
  Corre el pipeline completo (audio + video) para el proyecto actual. Primero intenta
  todo por código; si algo queda ambiguo, recién ahí pide ayuda a Claude.
  Ejemplo: /generar
  Requiere: haber mandado guion.json antes con /nuevovideo.

/estatus
  Dice si hay algo corriendo ahora y en qué paso va (audio, armado, reintento N, etc.).
  Ejemplo: /estatus

/resumen
  Lista cada plano del guion actual: sección, duración, narración y estado de medios.
  Ejemplo: /resumen
  Requiere: proyecto actual con guion.json ya recibido.

/videos
  Lista todos los videos ya generados en Android_out (nombre, tamaño, fecha).
  Ejemplo: /videos

/voz [nombre]
  Sin argumento: muestra la voz actual y la lista completa.
  Con argumento: la cambia para el próximo /generar.
  Ejemplo: /voz am_onyx
  Opciones: am_adam (default), am_santa, am_onyx, am_michael, am_fenrir, bm_george,
  pm_santa, pm_alex, em_santa, em_alex, ef_dora

/logo
  Prepara el bot para recibir el logo del canal — el siguiente mensaje debe ser la
  imagen (adjunta, no un link). Se usa siempre en el plano 0 de todos los videos.
  Ejemplo: /logo, después adjuntar la foto del logo.

/investigar <url | id de plano | palabras clave>
  Busca imágenes con licencia libre (Wikipedia + Openverse + NASA) y te las manda
  una por una (con fuente, licencia y autor) para que elijas. Con un id de plano
  (ej. p02), arma la búsqueda solo con el título del guion + nombres propios de esa
  narración — no hace falta pasar una URL. Independiente de /generar — si falla,
  solo avisa, no bloquea nada.
  Ejemplos:
    /investigar https://es.wikipedia.org/wiki/Criptografía
    /investigar p02
    /investigar Alan Turing máquina Enigma

/nuevo
  Reinicia la conversación con Claude desde cero (borra la memoria del chat, no tus
  archivos ni proyectos).
  Ejemplo: /nuevo

Enviar una imagen para un plano específico:
  Adjuntá la foto (botón de clip, no como texto) con este texto/caption:
  p1 [inicio] [1]
  p1 = número de plano · [inicio|medio|fin] = posición (informativo) · [N] = índice de toma

/ayuda o /help — vuelve a mostrar este mensaje."""


# Para el menú nativo de Telegram (botón "/" con autocompletado). Telegram
# limita la descripción a un renglón corto -- el detalle completo con
# ejemplos vive en HELP_TEXT (/ayuda).
BOT_COMMANDS = [
    ("nuevovideo", "Empezar un capítulo nuevo [slug opcional]"),
    ("generar", "Correr el pipeline completo del proyecto actual"),
    ("estatus", "Ver si hay algo corriendo y en qué paso va"),
    ("resumen", "Narración y estado de medios de cada plano"),
    ("videos", "Listar los videos ya generados en Android_out"),
    ("voz", "Ver o elegir la voz [nombre opcional]"),
    ("logo", "Mandar/actualizar el logo del canal"),
    ("investigar", "Buscar imágenes libres [url, plano o palabras clave]"),
    ("nuevo", "Reiniciar la conversación con Claude"),
    ("ayuda", "Ver todos los comandos con ejemplos"),
]


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update.effective_chat.id):
        await _reject_unauthorized(update)
        return
    await _send_long(update, HELP_TEXT)


async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update.effective_chat.id):
        await _reject_unauthorized(update)
        return
    await _send_long(update, HELP_TEXT)


async def cmd_nuevovideo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    slug = _slugify(" ".join(context.args)) if context.args else None
    sessions.start_collection(chat_id, slug)

    if slug:
        (ANDROID_IN / slug).mkdir(parents=True, exist_ok=True)
        await update.message.reply_text(
            f"Listo, proyecto '{slug}'. Mándame el guion.json de este capítulo."
        )
    else:
        await update.message.reply_text(
            "Listo, capítulo nuevo. Mándame el guion.json (el slug sale del "
            "nombre del archivo o del texto que le pongas)."
        )


async def cmd_generar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    slug = sessions.get_slug(chat_id)
    if not slug:
        await update.message.reply_text("No sé de qué proyecto — usa /nuevovideo primero.")
        return

    guion_path = ANDROID_IN / slug / "guion.json"
    if not guion_path.exists():
        await update.message.reply_text(f"Todavía no tengo el guion.json de '{slug}'.")
        return

    running, since = sessions.get_generating(chat_id)
    if running:
        await update.message.reply_text(f"Ya hay una generación corriendo desde {since}.")
        return

    voz = sessions.get_voice(chat_id)
    await update.message.reply_text(
        f"Arrancando el pipeline para '{slug}' con voz '{voz}' — primero sin Claude "
        f"(más rápido y sin costo). Puede tardar varios minutos. /estatus para ver el paso."
    )

    sessions.set_generating(chat_id, True)
    try:
        result = await asyncio.to_thread(pipeline.run, slug, voz, chat_id)
    finally:
        sessions.set_generating(chat_id, False)
        sessions.set_progress(chat_id, None)

    if result.ok:
        await update.message.reply_text(result.mensaje)
        sessions.set_phase(chat_id, sessions.PHASE_IDLE)
        return

    if not result.necesita_claude:
        await update.message.reply_text(f"Falló: {result.mensaje}")
        return

    await update.message.reply_text(
        f"El pipeline automático no pudo terminar solo:\n{result.mensaje}\n\n"
        f"Paso esto a Claude para que lo investigue y resuelva..."
    )
    await _dispatch_to_claude(update, INSTRUCCION_ESCALAR.format(slug=slug, detalle=result.mensaje))
    sessions.set_phase(chat_id, sessions.PHASE_IDLE)


async def cmd_investigar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Herramienta de investigación manual, aparte del pipeline: busca
    imágenes de contenido con licencia libre a partir de una URL de
    Wikipedia, un plano del proyecto actual, o palabras clave sueltas --
    y las manda para que el usuario elija cuál usar. Si falla, no afecta
    a /generar ni a nada más del bot -- solo avisa."""
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    if not context.args:
        await update.message.reply_text(
            "Uso:\n"
            "/investigar <url de Wikipedia>\n"
            "/investigar <id de plano, ej. p02> — arma la búsqueda solo con el "
            "título del guion + nombres propios de la narración de ese plano\n"
            "/investigar <palabras clave sueltas>\n\n"
            "Busca en Wikipedia + Openverse + NASA (todas con licencia verificada). "
            "Para usar una imagen en un plano, reenviámela con el texto p1 [inicio] [1]."
        )
        return

    arg = " ".join(context.args)
    es_url = arg.startswith("http")

    if es_url:
        buscar_por_query = False
        query_o_url = arg
    else:
        slug = sessions.get_slug(chat_id)
        plano = summary.find_plano(summary.load_guion_dict(slug), arg) if slug else None
        if plano is not None:
            guion = summary.load_guion_dict(slug)
            query_o_url = auto_query.build_query(guion.get("titulo", ""), plano.get("narracion", ""))
            if not query_o_url:
                await update.message.reply_text(
                    f"No pude sacar palabras clave del plano '{arg}' (narración vacía o "
                    f"sin nombres propios) — probá con /investigar <palabras clave>."
                )
                return
            await update.message.reply_text(f"Plano {arg} → busco: \"{query_o_url}\"")
        else:
            query_o_url = arg
        buscar_por_query = True

    await update.message.reply_text("Buscando imágenes con licencia libre...")

    try:
        if buscar_por_query:
            imagenes = await asyncio.to_thread(free_image_search.search_all, query_o_url)
        else:
            imagenes = await asyncio.to_thread(free_image_search.search_wikipedia_url, query_o_url)
    except Exception as exc:
        logger.warning("investigar falló para %r: %s", query_o_url, exc)
        await update.message.reply_text(
            f"No pude investigar eso ({exc}). No afecta al resto del bot — /generar sigue normal."
        )
        return

    if not imagenes:
        await update.message.reply_text("No encontré imágenes con licencia libre para eso.")
        return

    await update.message.reply_text(f"Encontré {len(imagenes)} imagen(es):")
    for img in imagenes:
        caption = f"{img.titulo}\nFuente: {img.fuente}\nLicencia: {img.licencia or '(sin dato)'}\nAutor: {img.autor or '(sin dato)'}"
        try:
            await update.message.reply_photo(photo=img.url, caption=caption[:1024])
        except Exception as exc:
            logger.warning("No pude mandar %s: %s", img.url, exc)
            await update.message.reply_text(f"No pude mandar {img.titulo} ({exc}).")


async def cmd_videos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update.effective_chat.id):
        await _reject_unauthorized(update)
        return
    videos = generated_videos.list_generated_videos()
    await _send_long(update, generated_videos.format_video_list(videos))


async def cmd_resumen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    slug = sessions.get_slug(chat_id)
    if not slug:
        await update.message.reply_text("No sé de qué proyecto — usa /nuevovideo primero.")
        return

    texto = summary.build_summary(slug)
    await _send_long(update, texto)


async def cmd_voz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    if not context.args:
        actual = sessions.get_voice(chat_id)
        await update.message.reply_text(
            f"Voz actual: {actual}\nDisponibles: {', '.join(VOICES)}\n"
            f"Para cambiarla: /voz <nombre>"
        )
        return

    voz = context.args[0].strip().lower()
    if voz not in VOICES:
        await update.message.reply_text(
            f"No conozco esa voz. Disponibles: {', '.join(VOICES)}"
        )
        return

    sessions.set_voice(chat_id, voz)
    await update.message.reply_text(f"Listo, voz para el próximo /generar: {voz}")


async def cmd_logo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    actual = sessions.logo_path()
    sessions.set_awaiting_logo(chat_id, True)
    aviso_actual = f" (ya hay uno: {actual.name})" if actual else ""
    await update.message.reply_text(
        f"Mándame la imagen del logo del canal{aviso_actual} — se va a usar siempre "
        f"en el plano 0 de todos los videos nuevos."
    )


async def cmd_estatus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    slug = sessions.get_slug(chat_id) or "(ninguno)"
    running, since = sessions.get_generating(chat_id)
    if not running:
        await update.message.reply_text(f"Nada corriendo ahora. Proyecto actual: {slug}")
        return

    started = datetime.fromisoformat(since)
    elapsed_min = int((datetime.now(timezone.utc) - started).total_seconds() // 60)
    paso = sessions.get_progress(chat_id) or "arrancando"
    await update.message.reply_text(
        f"Generando '{slug}' desde hace {elapsed_min} min.\nPaso actual: {paso}"
    )


async def cmd_nuevo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return
    sessions.reset_session(chat_id)
    await update.message.reply_text("Conversación con Claude reiniciada.")


async def on_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    doc = update.message.document
    suffix = Path(doc.file_name or "").suffix.lower()

    if suffix in IMAGE_EXTENSIONS:
        tg_file = await doc.get_file()
        await _handle_image(update, chat_id, tg_file, suffix)
        return

    if suffix != ".json":
        await update.message.reply_text(
            f"Recibí un archivo ({doc.file_name}) que no reconozco — esperaba "
            f".json (guion) o una imagen ({', '.join(sorted(IMAGE_EXTENSIONS))})."
        )
        return

    slug = sessions.get_slug(chat_id)
    if not slug:
        caption = (update.message.caption or "").strip()
        slug = _slugify(caption or Path(doc.file_name).stem)

    dest_dir = ANDROID_IN / slug
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / "guion.json"

    tg_file = await doc.get_file()
    await tg_file.download_to_drive(custom_path=str(dest_path))

    sessions.set_slug(chat_id, slug)
    await update.message.reply_text(
        f"Guion recibido para '{slug}'. Mándame imágenes si quieres "
        f"(p1 [inicio] [1]), o escribe /generar cuando estés listo."
    )


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return
    photo = update.message.photo[-1]  # la de mayor resolución
    tg_file = await photo.get_file()
    await _handle_image(update, chat_id, tg_file, ".jpg")


async def _handle_image(update: Update, chat_id: int, tg_file, suffix: str) -> None:
    """Guarda la imagen directo en Android_in/<slug>/imagenes_manuales/ —
    NO invoca a Claude. Eso pasa recien con /generar."""
    if sessions.is_awaiting_logo(chat_id):
        sessions.LOGO_DIR.mkdir(parents=True, exist_ok=True)
        # Borra cualquier logo anterior con otra extension antes de guardar
        # el nuevo, para que sessions.logo_path() no encuentre dos.
        for old in sessions.LOGO_DIR.glob(f"{sessions.LOGO_STEM}.*"):
            old.unlink()
        dest_path = sessions.LOGO_DIR / f"{sessions.LOGO_STEM}{suffix}"
        await tg_file.download_to_drive(custom_path=str(dest_path))
        sessions.set_awaiting_logo(chat_id, False)
        await update.message.reply_text(
            f"Logo guardado en {dest_path}. Se va a usar en el plano 0 de ahora en adelante."
        )
        return

    slug = sessions.get_slug(chat_id)
    if not slug:
        await update.message.reply_text(
            "Todavía no sé de qué proyecto es esta imagen — usa /nuevovideo y "
            "mándame el guion.json primero."
        )
        return

    caption = (update.message.caption or "").strip()
    spec = image_naming.parse(caption)
    if spec is None:
        await update.message.reply_text(
            "No reconocí el formato del texto de esta imagen. Mándala de nuevo "
            "con un texto así: p1 [inicio] [1]  (número de plano, posición, índice)."
        )
        return

    dest_dir = sessions.manual_images_dir_for(slug)
    dest_path = dest_dir / image_naming.filename_for(spec, suffix)
    await tg_file.download_to_drive(custom_path=str(dest_path))

    await update.message.reply_text(
        f"Guardada: plano {spec.plano_id}, posición {spec.posicion}, toma {spec.indice}. "
        f"({dest_path})"
    )


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not _authorized(chat_id):
        await _reject_unauthorized(update)
        return

    running, since = sessions.get_generating(chat_id)
    if running:
        await update.message.reply_text(f"Sigo trabajando en la generación (desde {since}).")
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

    async def _post_init(app: Application) -> None:
        await app.bot.set_my_commands(BOT_COMMANDS)

    app = Application.builder().token(token).post_init(_post_init).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler(["ayuda", "help"], cmd_ayuda))
    app.add_handler(CommandHandler("nuevovideo", cmd_nuevovideo))
    app.add_handler(CommandHandler("generar", cmd_generar))
    app.add_handler(CommandHandler("estatus", cmd_estatus))
    app.add_handler(CommandHandler("resumen", cmd_resumen))
    app.add_handler(CommandHandler("videos", cmd_videos))
    app.add_handler(CommandHandler("investigar", cmd_investigar))
    app.add_handler(CommandHandler("voz", cmd_voz))
    app.add_handler(CommandHandler("logo", cmd_logo))
    app.add_handler(CommandHandler("nuevo", cmd_nuevo))
    app.add_handler(MessageHandler(filters.Document.ALL, on_document))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    logger.info("Bot arrancado, escuchando Telegram (polling)...")
    app.run_polling()


if __name__ == "__main__":
    main()
