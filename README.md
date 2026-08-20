# dato-mata-gato-bot

Puente entre Telegram y el pipeline de **Dato Mata Gato** (`tts-kokoro` +
`illustrated-narrator`) desde el celular. `/generar` corre todo por
código, determinístico — Claude Code solo entra si algo queda ambiguo
después de reintentos automáticos.

## Cómo funciona

El bot separa **recolectar archivos** (puro manejo de archivos) de
**generar** (pipeline determinístico primero, Claude solo si hace falta):

1. `/nuevovideo [slug]` — empieza un capítulo. Sin `slug`, se deriva del
   `guion.json` que mandes después.
2. Mandas el `guion.json` (como documento) — el bot lo guarda en
   `C:\Android_in\<slug>\guion.json`.
3. (Opcional) Mandas fotos con este texto/caption:
   `p1 [inicio] [1]` (número de plano, posición legible, índice de toma).
   El bot las guarda en `C:\Android_in\<slug>\imagenes_manuales\`, ya
   parseadas. `/logo` para el logo del canal (fijo, se usa siempre en el
   plano 0). `/voz [nombre]` para elegir la voz (default `am_adam`).
4. `/generar` — corre `pipeline.py` (audio con tts-kokoro, armado del
   proyecto, `narrator generate`, y `media_check.py` revisando el
   `manifest.json` contra una lista de países/ciudades ya vistos como
   falsos positivos). Si algo queda marcado tras 2 reintentos
   automáticos, **recién ahí** se dispara una sesión de Claude Code
   (`claude -p ... --session-id/--resume`) con el detalle exacto de lo
   pendiente, para que investigue/decida lo que el código no puede.
5. `/estatus` — el paso real en el que va (generando audio, armando
   proyecto, reintento N/M, copiando a Android_out), no solo tiempo
   transcurrido.
6. Los mensajes de texto libres sí siguen la conversación con Claude
   (`--resume`, memoria real) para pedir ajustes después de generar.
   `/nuevo` la reinicia desde cero.

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
