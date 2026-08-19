# dato-mata-gato-bot

Puente entre Telegram y Claude Code para dirigir el pipeline de **Dato Mata
Gato** (`tts-kokoro` + `illustrated-narrator`) desde el celular. Cada chat
de Telegram se mapea 1:1 a una sesión de Claude Code — la conversación tiene
memoria real, como en una sesión interactiva.

## Cómo funciona

1. Mandas un `guion.json` (como documento) al bot, con el slug en el texto
   del mensaje o en el nombre del archivo.
2. El bot lo guarda en `C:\Android_in\<slug>\guion.json` y dispara una
   sesión de Claude Code (`claude -p ... --session-id ...`) desde
   `C:\illustrated-narrator` — esa sesión ya conoce el pipeline completo
   porque está documentado en su `CLAUDE.md`.
3. Cada mensaje siguiente en ese chat usa `--resume` sobre la misma sesión:
   puedes pedir ajustes, ver progreso, mandar fotos, todo en la misma
   conversación.
4. Fotos: mándalas con esta convención en el texto/caption —
   `p1 [inicio] [1]` (número de plano, posición legible, índice de toma).
   Claude las coloca como override manual siguiendo las reglas ya
   documentadas en `illustrated-narrator/CLAUDE.md`.
5. El video final **no se manda por Telegram** (pesa ~200MB+, por encima
   del límite de 50MB para bots) — llega a `C:\Android_out` como siempre,
   y de ahí a tu celular vía Syncthing. El bot solo avisa por texto.

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
