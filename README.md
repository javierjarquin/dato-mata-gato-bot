# dato-mata-gato-bot

Puente entre Telegram y un pipeline de generación de video narrado, pensado
para operarse **desde el celular**. Orquesta dos proyectos hermanos:

- [tts-kokoro](https://github.com/javierjarquin/tts-kokoro) — narración TTS
  local (Kokoro-82M) a partir de un `guion.json`.
- [illustrated-narrator](https://github.com/javierjarquin/generate_assistance)
  — ensambla el video final (imágenes/video real o generado con IA, subtítulos,
  cama de audio).

`/generar` corre todo por código, determinístico — Claude Code (CLI) solo
entra si algo queda ambiguo después de reintentos automáticos, o para tareas
que necesitan criterio (escribir guiones nuevos, resolver un caso puntual).

Este bot fue armado para un canal concreto (true crime en español), pero la
lógica es genérica: cualquier canal de video narrado con imágenes/stock puede
adaptarlo cambiando el `guion.json` y los prompts.

## Arquitectura

```
Telegram (celular) → dato-mata-gato-bot → tts-kokoro (audio)
                                        → illustrated-narrator (video)
                                        → Google Drive (entrega final)
                                        → Claude Code CLI (solo si hace falta)
```

El bot separa **recolectar archivos** (puro manejo de archivos, sin costo) de
**generar** (pipeline determinístico primero, Claude solo si hace falta):

1. `/nuevovideo [slug]` — empieza un capítulo. Sin `slug`, se deriva del
   `guion.json` que mandes después.
2. Mandás el `guion.json` (como documento, no como texto pegado) — el bot lo
   guarda en `<ANDROID_IN>/<slug>/guion.json`. El formato de `guion.json` está
   documentado en el README de `illustrated-narrator`.
3. (Opcional) Mandás fotos con este texto/caption: `p1 [inicio] [1]` (número
   de plano, posición legible, índice de toma) para forzar una imagen a mano
   en un plano puntual. `/logo` para el logo de apertura (fijo, plano 0),
   `/cierre` para el cartel de cierre (fijo, último plano — evita que el
   pipeline se quede sin medio en el plano que SIEMPRE es un logo genérico).
   `/voz [nombre]` para elegir la voz de Kokoro (default `am_adam`).
4. `/generar` — corre `pipeline.py`: audio con tts-kokoro, arma el proyecto,
   `narrator generate`, y `media_check.py` revisa el `manifest.json` contra
   heurísticas de coherencia (país/lugar incoherente, toma sin medio real).
   Si algo queda marcado tras varios reintentos automáticos (`MAX_AUTO_RETRIES`
   en `pipeline.py`), **recién ahí** se dispara una sesión de Claude Code
   (`claude -p ... --session-id/--resume`) con el detalle exacto de lo
   pendiente, para que investigue/decida lo que el código no puede.
5. `/estatus` — el paso real en el que va (generando audio, armando proyecto,
   reintento N/M, subiendo a Drive), no solo tiempo transcurrido.
6. Los mensajes de texto libres siguen la conversación con Claude (`--resume`,
   memoria real por chat) para pedir ajustes después de generar, o para
   `/nuevolote`/`/generarlote` (ver abajo). `/nuevo` reinicia esa memoria.

### Comandos adicionales

- `/videos` — calendario de publicación: qué video, para qué fecha, y si ya
  se subió a Drive.
- `/investigar <url | id de plano | palabras clave>` — busca imágenes con
  licencia libre (Wikipedia + Openverse + NASA) fuera del flujo de
  `/generar`, para revisar candidatos a mano.
- `/scrapear <url>` — POC suelto, sin relación con el pipeline: baja
  imágenes/audio de una página (útil para armar un banco de recursos propio)
  usando un navegador real (Playwright), así funciona con sitios estáticos o
  SPAs de React. Todavía no recorre más de una página.
- `/nuevolote [cantidad]` (default 5) — le pide a la sesión de Claude de ese
  chat que escriba varios guiones nuevos de una (revisando qué ya está
  cubierto para no repetir tema/caso) y te devuelve título + resumen de cada
  uno para que revises la veracidad **antes** de generar ningún video.
- `/generarlote` — corre `/generar` en cadena para cada guion del último
  `/nuevolote`, uno detrás del otro (nunca en paralelo — la GPU es
  compartida). Si alguno no termina solo, lo escala a Claude y sigue con el
  resto sin trabarse.

El video final **no se manda por Telegram** (pesa ~200MB+, por encima del
límite de 50MB para bots) — se sube directo a una carpeta de Google Drive,
con nombre progresivo `<titulo>_<DDMMYYYY>.mp4` según el calendario de
publicación (`/videos` lo muestra). El bot solo avisa por texto. Publicar
ese video en YouTube/redes sigue siendo un paso manual — no hay integración
con ninguna plataforma de publicación todavía.

## Instalación

### 1. Prerrequisitos

- Python 3.10+
- [`illustrated-narrator`](https://github.com/javierjarquin/generate_assistance)
  y [`tts-kokoro`](https://github.com/javierjarquin/tts-kokoro) clonados e
  instalados (cada uno con su propio README) — este bot solo los orquesta,
  no reemplaza su instalación.
- [Claude Code CLI](https://docs.claude.com/claude-code) (`claude`) instalado,
  en el `PATH`, y ya autenticado (`claude login` u otro flujo de auth) —
  necesario incluso para el flujo "sin Claude", porque las escaladas y
  `/nuevolote` lo invocan.
- (Opcional) [AUTOMATIC1111 WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)
  con `--api`, solo si vas a usar el fallback de video-IA de
  `illustrated-narrator` (ver su README) — el bot lo arranca y reinicia solo
  cuando hace falta (`_kick_off_a1111_if_needed` / `NARR_A1111_RESTART_BEFORE_USE`
  en `pipeline.py`), pero requiere que la instalación ya exista en la ruta
  configurada.

### 2. Rutas hardcodeadas — ADAPTAR A TU MÁQUINA

Este proyecto asume Windows y rutas absolutas fijas (no variables de entorno,
por simplicidad). Si tu instalación no coincide con estas rutas, hay que
editar las constantes directamente en el código antes de correrlo:

| Constante | Archivo | Default | Qué es |
|---|---|---|---|
| `ANDROID_IN` | `bot.py`, `pipeline.py`, `sessions.py`, `summary.py` | `C:\Android_in` | Carpeta donde el bot guarda cada `guion.json`/imágenes recibidas por Telegram |
| `TTS_KOKORO_PROJECTS` | `pipeline.py` | `C:\tts-kokoro\projects` | Carpeta de proyectos de tts-kokoro |
| `TTS_KOKORO_PY` | `pipeline.py` | `C:\tts-kokoro\.venv\Scripts\python.exe` | Intérprete del venv de tts-kokoro |
| `NARRATOR_PROJECTS` | `pipeline.py`, `summary.py` | `C:\illustrated-narrator\projects` | Carpeta de proyectos de illustrated-narrator |
| `POETRY_EXE` | `pipeline.py` | `C:\Users\<usuario>\AppData\Roaming\Python\Scripts\poetry.exe` | **Específico del usuario** — ruta al ejecutable de Poetry que corre `narrator generate` |
| `A1111_BAT` / `A1111_TOOLS_DIR` | `pipeline.py` | `C:\illustrated-narrator\tools\run_a1111.bat` | Solo si usás el fallback de video-IA |
| `LOGO_DIR` | `sessions.py` | `C:\illustrated-narrator\assets` | Dónde se guarda el logo/cierre subidos por `/logo` y `/cierre` |
| `CWD` | `claude_runner.py` | `C:\illustrated-narrator` | Directorio de trabajo desde el que se invoca `claude -p` |

### 3. Instalar el bot

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
cp .env.example .env
```

Playwright (usado por `/scrapear`) necesita además su navegador:

```bash
python -m playwright install chromium
```

### 4. Crear el bot de Telegram

1. Hablále a [@BotFather](https://t.me/BotFather) en Telegram, `/newbot`,
   seguí las instrucciones. Te da un token (`123456:ABC-...`).
2. Poné ese token en `.env` como `TELEGRAM_BOT_TOKEN`.
3. Dejá `TELEGRAM_ALLOWED_CHAT_IDS` vacío por ahora (seguro por defecto:
   nadie puede usarlo hasta que lo autorices).

### 5. Google Drive (subida del video final)

1. Proyecto en [Google Cloud Console](https://console.cloud.google.com/) con
   la Drive API activada + credencial OAuth tipo "Desktop app" (Client ID).
   Descargá el JSON y guardalo como
   `credentials/google_drive_client_secret.json`.
2. Completá `GOOGLE_DRIVE_FOLDER_ID` en `.env` con el ID de la carpeta de
   Drive destino (el string en la URL después de `/folders/`).
3. Autorización única (abre el navegador, elegís tu cuenta, aceptás):
   ```
   .venv\Scripts\python.exe -m dato_mata_gato_bot.drive_auth
   ```
   Esto guarda un refresh token en `credentials/google_drive_token.json` que
   se reutiliza siempre — no hay que repetir este paso salvo que lo revoques
   desde tu cuenta de Google.

### 6. Primer arranque

```bash
python -m dato_mata_gato_bot.bot
```

Escribile cualquier cosa al bot desde Telegram — como
`TELEGRAM_ALLOWED_CHAT_IDS` empieza vacío, te va a responder con tu
`chat_id`. Agregalo a esa variable en `.env` y reiniciá el bot.

### 7. Arranque automático con Windows (opcional)

`tools/instalar_tarea.ps1` crea un acceso directo en la carpeta de Inicio de
Windows (`shell:startup`) que arranca el bot (sin ventana de consola, vía
`pythonw.exe`) al iniciar sesión — no requiere permisos de administrador.
Correrlo una vez.

## Tests

```bash
pip install -e ".[dev]"
pytest -q
```

## Requisitos resumidos

- Python 3.10+
- `claude` (Claude Code CLI) en el PATH, ya autenticado
- `tts-kokoro` y `illustrated-narrator` instalados (ver sus propios README)
- Poetry instalado (lo usa `illustrated-narrator` para correr `narrator generate`)
- Cuenta de Google Cloud con Drive API + credencial OAuth
- Bot de Telegram (token de @BotFather)
