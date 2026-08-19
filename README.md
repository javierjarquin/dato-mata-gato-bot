# dato-mata-gato-bot

Puente entre Telegram y Claude Code para dirigir el pipeline de **Dato Mata
Gato** (`tts-kokoro` + `illustrated-narrator`) desde el celular. Cada chat
de Telegram se mapea 1:1 a una sesión de Claude Code — la conversación tiene
memoria real, como en una sesión interactiva.

## Cómo funciona

El bot separa **recolectar archivos** (puro manejo de archivos, sin
Claude) de **generar** (el único momento en que se invoca a Claude):

1. `/nuevovideo [slug]` — empieza un capítulo. Sin `slug`, se deriva del
   `guion.json` que mandes después.
2. Mandas el `guion.json` (como documento) — el bot lo guarda en
   `C:\Android_in\<slug>\guion.json`. Sin invocar a Claude todavía.
3. (Opcional) Mandas fotos con este texto/caption:
   `p1 [inicio] [1]` (número de plano, posición legible, índice de toma).
   El bot las guarda en `C:\Android_in\<slug>\imagenes_manuales\`, ya
   parseadas — tampoco invoca a Claude.
4. `/generar` — ahora sí dispara UNA sesión de Claude Code
   (`claude -p ... --session-id/--resume`) desde `C:\illustrated-narrator`,
   que ya conoce el pipeline completo (documentado en su `CLAUDE.md`):
   genera el audio con `tts-kokoro`, arma el video con
   `illustrated-narrator`, coloca las imágenes manuales, revisa
   coherencia de medios, y copia el resultado a `Android_out`.
5. `/estatus` — si hay una generación corriendo y desde cuándo.
6. Después de generar, los mensajes de texto libres siguen la misma
   conversación (`--resume`) para pedir ajustes — memoria real, como una
   sesión interactiva. `/nuevo` la reinicia desde cero.

El video final **no se manda por Telegram** (pesa ~200MB+, por encima
del límite de 50MB para bots) — llega a `C:\Android_out` como siempre, y
de ahí a tu celular vía Syncthing. El bot solo avisa por texto.

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
cp .env.example .env   # completar TELEGRAM_BOT_TOKEN
```

## Primer uso

1. Corre el bot (`python -m dato_mata_gato_bot.bot` o el script de
   `tools/`).
2. Escríbele cualquier cosa desde Telegram — te va a responder con tu
   `chat_id` porque `TELEGRAM_ALLOWED_CHAT_IDS` empieza vacío (seguro por
   defecto, nadie puede usarlo hasta que lo autorices).
3. Agrega ese `chat_id` a `TELEGRAM_ALLOWED_CHAT_IDS` en el `.env` y
   reinicia el bot.

## Arranque automático con Windows

`tools/instalar_tarea.ps1` crea un acceso directo en la carpeta de Inicio
de Windows (`shell:startup`) que arranca el bot (sin ventana de consola,
via `pythonw.exe`) al iniciar sesión — no requiere permisos de
administrador. Correrlo una vez.

## Requisitos

- Python 3.10+
- `claude` (Claude Code CLI) en el PATH, ya autenticado
- `tts-kokoro` y `illustrated-narrator` instalados en sus rutas estándar
  (`C:\tts-kokoro`, `C:\illustrated-narrator`)
