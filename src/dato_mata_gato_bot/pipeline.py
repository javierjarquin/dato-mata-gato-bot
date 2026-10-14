"""Orquestador determinístico del pipeline completo — CERO Claude.
Corre tts-kokoro + illustrated-narrator directo, valida el resultado con
media_check (heurística de país incoherente / toma sin medio), y
reintenta solo. Si tras los reintentos automáticos algo sigue ambiguo,
devuelve necesita_claude=True para que el llamador escale — Claude se usa
solo para lo que la heurística no puede resolver, no para toda la corrida."""

import json
import logging
import os
import re
import shutil
import subprocess
import time
import zlib
from dataclasses import dataclass, field
from pathlib import Path

import requests

from dato_mata_gato_bot import (
    avatar_presentador,
    drive_upload,
    evidencia,
    media_check,
    publish_schedule,
    quiz_cards,
    sessions,
)

logger = logging.getLogger(__name__)

TTS_KOKORO_PY = r"C:\tts-kokoro\.venv\Scripts\python.exe"
TTS_KOKORO_PROJECTS = Path(r"C:\tts-kokoro\projects")
NARRATOR_PROJECTS = Path(r"C:\illustrated-narrator\projects")
POETRY_EXE = r"C:\Users\jarqu\AppData\Roaming\Python\Scripts\poetry.exe"
# Shorts Factory: el pipeline viejo de bajar un video ajeno y trocearlo.
SHORTS_FACTORY_DIR = Path(r"C:\clip_assistance")
SHORTS_FACTORY_PY = SHORTS_FACTORY_DIR / ".venv" / "Scripts" / "python.exe"
# Carpeta de Drive donde viven los troceos, aparte de los videos del canal.
CARPETA_TROZOS = "Shorts troceados"
# Marca de agua de los trozos, arriba a la izquierda. Configurable por si hay
# que usar otro logo segun el canal de destino.
LOGO_TROZOS = os.getenv("LOGO_SHORTS") or str(SHORTS_FACTORY_DIR / "assets" / "logo_gamer.png")
# Bajar + cortar + reencodear a 9:16 un video largo lleva su rato; el timeout
# general de 2h no alcanza para uno de varias horas.
TIMEOUT_TROCEO = 60 * 60 * 4
# Sprites del gato del logo (emblema + las 9 formas de boca). Se regeneran con
# gato_sprites.py --modo emblema --pipeline, en clip_assistance.
MASCOTA_PATH = r"C:\illustrated-narrator\assets\mascota_gato"
# Emblema fijo de los true crime con su voz propia (ver voz_de_true_crime).
EMBLEMA_ESQUINA = r"C:\illustrated-narrator\assets\dato_mata_gato_emblema.png"
ANDROID_IN = Path(r"C:\Android_in")
FFMPEG = "ffmpeg"

# El fallback de video-IA (NARR_VIDEO_FALLBACK_MAX_PLANOS en el .env de
# illustrated-narrator) necesita A1111 con --api corriendo. Ahí mismo NO
# se autolanza a propósito (ver su CLAUDE.md, decisión para sesiones
# interactivas) -- pero el pipeline automático del bot sí necesita que
# esté listo sin que nadie lo prenda a mano, si no el fallback simplemente
# no dispara nunca (is_available() da False, salta directo a FALLIDO).
A1111_BASE_URL = "http://127.0.0.1:7860"
A1111_BAT = r"C:\illustrated-narrator\tools\run_a1111.bat"
A1111_TOOLS_DIR = r"C:\illustrated-narrator\tools"
A1111_HEALTH_TIMEOUT = 3

# Subido de 2 a 10 a pedido explícito del usuario (23/08/2026): con 2, el
# pipeline escalaba a Claude en casi todos los capítulos. La mayoría de
# los reintentos son rápidos (solo re-investigan las tomas marcadas, no
# todo el capítulo -- resolve_shot_asset se salta lo ya resuelto), así que
# subir el tope no vuelve el pipeline mucho más lento en el caso típico.
MAX_AUTO_RETRIES = 10
SUBPROCESS_TIMEOUT_SECONDS = 60 * 60 * 2
# Solo para el paso de audio con VoiceStudio (ver _generate_audio).
TIMEOUT_AUDIO_VOICESTUDIO = 60 * 60 * 6


@dataclass
class PipelineResult:
    ok: bool
    mensaje: str
    necesita_claude: bool = False
    flagged: list[media_check.FlaggedShot] = field(default_factory=list)


def _kill_process_tree(pid: int) -> None:
    """`Popen.kill()` en Windows solo mata el proceso de arriba (poetry.exe),
    no sus descendientes -- python.exe y ffmpeg.exe quedan huérfanos y
    corriendo, y pueden seguir escribiendo archivos de una corrida vieja
    mientras el bot ya arrancó la siguiente (mismo bug confirmado en una
    corrida real de illustrated-narrator: así se corrompió un final.mp4 sin
    que nadie lo notara, con el proceso "ganador" reportando éxito igual).
    `taskkill /T` sí mata el árbol completo."""
    subprocess.run(
        ["taskkill", "/F", "/T", "/PID", str(pid)],
        capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW,
    )


def _run(
    args: list[str],
    cwd: str | None = None,
    env: dict | None = None,
    timeout: int | None = None,
) -> subprocess.CompletedProcess:
    timeout = timeout or SUBPROCESS_TIMEOUT_SECONDS
    logger.info("Ejecutando: %s", " ".join(str(a) for a in args))
    proc = subprocess.Popen(
        args, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        # errors="replace": un subproceso (visto real: tts-kokoro) puede
        # imprimir algún byte que no es UTF-8 válido (ej. un guion largo en
        # cp1252 de la consola de Windows) -- sin esto, el hilo lector de
        # subprocess.Popen.communicate() explota con UnicodeDecodeError y
        # se pierde ese stream (comunicate() igual puede devolver algo si
        # el OTRO stream sí se leyó bien, pero es buena suerte, no algo en
        # lo que confiar).
        text=True, encoding="utf-8", errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        # No se relanza el TimeoutExpired: antes se propagaba sin atrapar
        # hasta bot.py (pipeline.run no tiene try/except alrededor), lo que
        # dejaba la corrida colgada en el hilo del bot sin que el usuario
        # recibiera jamás una respuesta en Telegram. Devolver un
        # CompletedProcess con returncode != 0 reusa el mismo camino de
        # necesita_claude=True que ya usa cada otro fallo de este archivo.
        logger.error(
            "Timeout de %ds corriendo %s -- matando árbol de procesos (PID %d)",
            timeout, args[0], proc.pid,
        )
        _kill_process_tree(proc.pid)
        stdout, stderr = proc.communicate()  # drena lo que ya estaba bufferizado
        stderr = (stderr or "") + f"\n[TIMEOUT tras {SUBPROCESS_TIMEOUT_SECONDS}s -- proceso matado]"
        return subprocess.CompletedProcess(args, returncode=-1, stdout=stdout, stderr=stderr)
    return subprocess.CompletedProcess(args, proc.returncode, stdout, stderr)


def _a1111_ready() -> bool:
    try:
        resp = requests.get(f"{A1111_BASE_URL}/sdapi/v1/sd-models", timeout=A1111_HEALTH_TIMEOUT)
        return resp.ok
    except requests.RequestException:
        return False


def _kick_off_a1111_if_needed() -> None:
    """Lanza A1111 en segundo plano sin esperar a que cargue -- no bloquea
    el pipeline. Para cuando llegue a research_plano_media/generate_images
    (varios pasos después: audio, ffmpeg concat, investigación de medios de
    TODOS los planos) ya debería estar listo si hacía falta. Si no llegó a
    tiempo, el fallback simplemente se salta esta vez (is_available()==False
    -> plano queda FALLIDO como si el fallback estuviera desactivado) --
    nunca bloquea ni rompe la corrida."""
    if _a1111_ready():
        return
    logger.info("A1111 no está corriendo, arrancándolo en paralelo (%s)", A1111_BAT)
    try:
        subprocess.Popen(
            [A1111_BAT], cwd=A1111_TOOLS_DIR,
            creationflags=subprocess.CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        logger.warning("No se pudo arrancar A1111 (%s); el fallback de video-IA se saltará si hace falta", exc)


def _esperar_a1111(segundos: int = 180) -> bool:
    """Espera a que A1111 conteste. True si llegó a estar listo.

    `_kick_off_a1111_if_needed()` lanza y NO espera, a propósito: en un video
    nuevo pasan minutos (audio, concat, investigación de medios) antes de que
    haga falta la primera imagen, y bloquear ahí sería tiempo tirado.

    Pero hay dos casos donde sí hay que esperar, y los dos mordieron:

    - Un proyecto que se RETOMA ya tiene el audio y los clips en disco, así
      que el narrador llega a pedir imágenes a los pocos segundos. El
      23/09/2026 guion-mara-castilla falló en seis segundos por esto.
    - El reintento por falla de A1111 CIERRA el proceso y vuelve a lanzarlo;
      si reintenta enseguida, A1111 todavía está cargando el checkpoint y el
      reintento se pierde igual que el primer intento.

    Arrancar tarda ~14s medidos, pero con el checkpoint frío puede más; el
    tope de tres minutos es holgado y no bloquea para siempre si no levanta.
    """
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        if _a1111_ready():
            return True
        time.sleep(3)
    logger.warning("A1111 no respondió en %ss", segundos)
    return False


def _es_falla_de_a1111(salida: str) -> bool:
    """¿El narrador falló por A1111 y no por el guion?

    Se reconoce por cualquier mención a su puerto. Todas las formas en que
    falla se arreglan igual -- cerrándolo y levantándolo limpio -- a
    diferencia de un guion con un plano mal escrito, que va a fallar igual
    cuantas veces se reintente. Vistas hasta ahora:

        500 Server Error ... /sdapi/v1/txt2img       (sin VRAM, 18/09 10:59)
        Max retries exceeded ... port=7860           (no levantó, 18/09 13:31)

    La primera versión de esto buscaba la cadena "7860/sdapi" y se perdió el
    segundo caso, donde el puerto y la ruta van separados por el texto del
    error. Por eso ahora alcanza con el puerto.
    """
    return "7860" in (salida or "")


def _detener_a1111() -> bool:
    """Cierra A1111 para devolverle la VRAM al sistema. True si cerró alguno.

    Hace falta porque A1111 carga su checkpoint al arrancar y se queda con
    ~6.6 GB de los 8 de la placa, esté generando o no. Con eso puesto:

    - su propio `txt2img` devuelve 500 por falta de memoria (visto el
      18/09/2026 en guion-ficrea-fraude, un minuto después de reiniciarlo);
    - y MuseTalk no arranca, porque necesita 2-3 GB que no hay.

    `/sdapi/v1/unload-checkpoint` NO sirve acá: devuelve 200 pero la memoria
    no baja. Esta instalación corre sobre DirectML (`/sdapi/v1/memory`
    responde `cuda: unavailable`) y ese backend no la devuelve. Cerrar el
    proceso es la única forma que funciona.

    No hay que relanzarlo a mano: `_kick_off_a1111_if_needed()` lo levanta de
    nuevo en el próximo video que lo necesite.
    """
    cerrados = 0
    for pid, linea in _procesos_python():
        if "launch.py" not in linea:
            continue
        logger.info("Cerrando A1111 (PID %s) para liberar la VRAM", pid)
        _kill_process_tree(pid)
        cerrados += 1
    return cerrados > 0


def _procesos_python() -> list[tuple[int, str]]:
    """(PID, línea de comando) de cada python.exe que está corriendo.

    Antes esto usaba `wmic`, que Windows 11 ya no trae: fallaba con
    "[WinError 2]" y devolvía nada, en silencio. Así, desde que se quitó,
    nada de lo que cierra procesos funcionaba -- ni cerrar A1111 antes de
    MuseTalk, ni el reinicio de A1111 cuando se queda sin memoria, ni
    `/pausa ya` (visto el 27/09/2026, en cada video con presentador de un
    lote de 20). PowerShell trae Get-CimInstance en cualquier Windows.
    """
    comando = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
               "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress")
    try:
        salida = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", comando],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60, creationflags=subprocess.CREATE_NO_WINDOW,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("No se pudo listar procesos de Python: %s", exc)
        return []
    if not salida:
        return []
    try:
        datos = json.loads(salida)
    except json.JSONDecodeError:
        logger.warning("Lista de procesos ilegible: %s", salida[:300])
        return []
    if isinstance(datos, dict):  # con un solo proceso PowerShell no arma lista
        datos = [datos]
    return [(int(d["ProcessId"]), d.get("CommandLine") or "")
            for d in datos if str(d.get("ProcessId", "")).isdigit()]


def hoja_de_contacto(slug: str) -> Path | None:
    """Todas las imágenes de un mito en una sola hoja, para revisarlas de un
    vistazo desde Telegram antes de publicar. None si no es un mito o no hay
    imágenes.

    Solo para mitos porque es donde el modelo de imagen dibuja PERSONAJES, y
    ahí se equivoca de maneras que ninguna regla anticipa del todo. En los
    dos POC salió: figuras humanas desnudas para el Pombero, un hombre de
    abrigo negro en vez del Yum Balam, una cara de muchacha con ojos rojos
    para el Huay Chivo (25/09/2026). Todos se vieron mirando las imágenes, no
    con tests. Nada se publica solo, así que alcanza con verlas antes.
    """
    from PIL import Image, ImageDraw

    proyecto = NARRATOR_PROJECTS / slug
    try:
        guion = json.loads((proyecto / "guion.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if guion.get("formato") != "mito":
        return None

    def orden(ruta: Path):
        m = re.match(r"p(\d+)(?:_(\d+))?", ruta.stem)
        return (int(m.group(1)), int(m.group(2) or 0)) if m else (999, 0)

    # Sin el plano del cartel de cierre: ese es fijo y ya se sabe cómo se ve.
    cierre = next((p["id"] for p in guion.get("planos", [])
                   if p.get("seccion") == "identidad_cierre"), None)
    fotos = sorted((f for f in (proyecto / "images").glob("p*.png")
                    if not (cierre and f.stem.split("_")[0] == cierre)), key=orden)
    if not fotos:
        return None

    ancho, columnas, rotulo = 180, 8, 16
    miniaturas = []
    for f in fotos:
        im = Image.open(f).convert("RGB")
        miniaturas.append((f.stem, im.resize((ancho, max(1, int(im.height * ancho / im.width))))))
    alto = max(m.height for _, m in miniaturas)
    filas = (len(miniaturas) + columnas - 1) // columnas
    hoja = Image.new("RGB", (ancho * columnas, (alto + rotulo) * filas), "black")
    dibujo = ImageDraw.Draw(hoja)
    for i, (nombre, m) in enumerate(miniaturas):
        x, y = (i % columnas) * ancho, (i // columnas) * (alto + rotulo)
        hoja.paste(m, (x, y + rotulo))
        dibujo.text((x + 3, y + 2), nombre, fill="yellow")
    destino = proyecto / "hoja_de_contacto.jpg"
    hoja.save(destino, quality=85)
    return destino


def detener_generacion() -> bool:
    """Corta el `narrator generate` que esté corriendo. True si cortó alguno.

    Lo usa `/pausa ya` cuando hace falta la placa YA y no se puede esperar a
    que termine el video. El video cortado no se pierde del lote: sigue en
    `pending_batch` y se rehace al retomar (ver cmd_pausa en bot.py).

    Se busca por línea de comando y no por un handle guardado porque el
    subproceso lo lanza `_run_cmd` con `subprocess.run`, que no deja handle
    -- y porque el que pide la pausa es otro hilo, el del bot de Telegram.
    """
    cortados = 0
    for pid, linea in _procesos_python():
        if "narrator" not in linea or "generate" not in linea:
            continue
        logger.info("Cortando narrator generate (PID %s) por pausa pedida", pid)
        _kill_process_tree(pid)
        cortados += 1
    return cortados > 0


def motor_tts() -> str:
    """Motor de síntesis en uso. Lo lee del entorno igual que tts-kokoro, para
    que el bot y el subproceso siempre coincidan."""
    return (os.getenv("TTS_ENGINE") or "voicestudio").strip().lower()


def motor_tts_listo() -> str:
    """Mensaje de qué falta para poder sintetizar, o "" si está todo bien.

    Se chequea ANTES de arrancar un lote: con el contenedor abajo, el primer
    video se cae en el paso de audio y escala a Claude, que lo resuelve pero
    tarda quince minutos y gasta una llamada (confirmado en el lote del
    14/09/2026). Preguntarlo antes cuesta dos segundos.
    """
    if motor_tts() != "voicestudio":
        return ""
    base = os.getenv("VOICESTUDIO_BASE_URL", "http://localhost:3900/v1").rstrip("/")
    try:
        resp = requests.get(f"{base}/audio/voices", timeout=8)
    except requests.RequestException as exc:
        logger.warning("VoiceStudio no responde en %s: %s", base, exc)
        return (
            f"VoiceStudio no responde en {base}. Levantá el contenedor de Docker "
            "antes de arrancar el lote; si no, el primer video se cae en el audio."
        )
    if not resp.ok:
        return f"VoiceStudio contestó {resp.status_code} en {base}."
    return ""


# Prueba de voces (11/10/2026): la mitad de los true crime con Fish 3 y la
# otra mitad con la voz nueva de Javier (perfil clonado de "sin nombre.wav",
# grabada sin supresión de ruido). Javier eligió de oído su voz con el ajuste B
# del gancho, pero quiere comparar resultados publicados antes de quedarse con
# una. Sin VOICESTUDIO_VOICE_ID_CRIMEN_JAVIER todo sale con Fish 3, como antes.
VOCES_CRIMEN = {
    "fish3": lambda: (os.getenv("VOICESTUDIO_VOICE_ID_CRIMEN") or "").strip(),
    "javier": lambda: (os.getenv("VOICESTUDIO_VOICE_ID_CRIMEN_JAVIER") or "").strip(),
}
NOMBRE_VOZ = {"fish3": "Fish 3", "javier": "Javier (voz nueva)"}


def voz_narrador(slug: str) -> str:
    """'fish3' o 'javier' para un true crime.

    Manda el campo `voz_narrador` del guion (lo escribe `lote_grande.repartir_voces`
    para alternar una y una dentro del lote). Sin campo, se decide por el slug
    con un hash estable: el mismo video sale siempre con la misma voz, también
    si se regenera.
    """
    if not VOCES_CRIMEN["javier"]():
        return "fish3"
    guion = ANDROID_IN / slug / "guion.json"
    try:
        elegida = json.loads(guion.read_text(encoding="utf-8")).get("voz_narrador")
    except (OSError, ValueError):
        elegida = None
    if elegida in VOCES_CRIMEN:
        return elegida
    return "javier" if zlib.crc32(slug.encode("utf-8")) % 2 else "fish3"


def voz_de_true_crime(slug: str, avatar: bool = False) -> dict[str, str]:
    """Variables de voz propias de los true crime, o {} si el video usa la de
    siempre (VOICESTUDIO_VOICE_ID).

    Desde el 28/09/2026 los true crime van con otra voz, más de narrador (el
    usuario la eligió entre tres en videos completos de Tierra Blanca), y con
    num_step=32, que le dio más entonación. Trivia y mitos siguen con la voz de
    Javier. Con presentador tampoco se cambia: es la cara de Javier moviendo
    los labios, y con otra voz se vería doblado.

    Un true crime se reconoce por el prefijo `guion-`, igual que en
    lote_grande.admite_avatar: trivia y mitos tienen prefijo propio.
    """
    if motor_tts() != "voicestudio" or avatar or not slug.startswith("guion-"):
        return {}
    voz = VOCES_CRIMEN[voz_narrador(slug)]()
    if not voz:
        return {}
    # Verificación con Whisper (29/09/2026): tts-kokoro comprueba que el plano
    # se dijo entero y reintenta con otra semilla si no. El "cia" del final de
    # cada frase se resolvió en la muestra (perfil v3, respiración quitada), no
    # recortando: el recorte frase por frase se llegó a comer palabras.
    env = {"VOICESTUDIO_VOICE_ID": voz, "VOICESTUDIO_VERIFICAR": "1"}
    pasos = (os.getenv("VOICESTUDIO_NUM_STEP_CRIMEN") or "").strip()
    if pasos:
        env["VOICESTUDIO_NUM_STEP"] = pasos
    return env


def _generate_audio(slug: str, voz: str, velocidad: float = 1.0,
                    avatar: bool = False) -> tuple[bool, str]:
    guion_path = TTS_KOKORO_PROJECTS / slug / "guion.json"
    args = [
        TTS_KOKORO_PY, "-m", "tts_kokoro.cli",
        "--guion", str(guion_path), "--velocidad", str(velocidad),
    ]
    # `voz` es un nombre de voz de KOKORO (am_adam, em_santa...), que es lo que
    # elige el usuario con /voz. En VoiceStudio la voz es un profile_id propio
    # de esa instancia: pasarle un nombre de Kokoro lo haría fallar. Ahí se
    # omite --voz a propósito para que el CLI use VOICESTUDIO_VOICE_ID.
    if motor_tts() != "voicestudio":
        args += ["--voz", voz]

    # VoiceStudio sintetiza a ~13x el largo del audio (corre en CPU): el
    # episodio más largo que hay hoy (604s de narración) tarda ~131 min y NO
    # entra en el timeout general de 2h -- se cortaría a mitad y escalaría a
    # Claude por un fallo que no es tal. Kokoro va más rápido que tiempo real
    # y no necesita este margen.
    timeout = TIMEOUT_AUDIO_VOICESTUDIO if motor_tts() == "voicestudio" else None
    propia = voz_de_true_crime(slug, avatar)
    env = {**os.environ, **propia} if propia else None
    if propia:
        logger.info("%s: voz de true crime %s", slug, propia)
    proc = _run(args, env=env, timeout=timeout)
    if proc.returncode != 0:
        return False, f"tts-kokoro falló:\n{proc.stderr[-1500:]}"
    return True, proc.stdout


def _apply_logo(dest_dir: Path, guion: dict) -> None:
    """Copia el logo del canal al plano de apertura, SI el guion tiene uno.
    Desde el 27/08/2026 los guiones nuevos ya NO llevan plano de apertura
    (el título del caso se narra al arranque de p01, sobre imagen real --
    ver CLAUDE.md): en ese caso esto no hace nada. Se localiza el plano por
    seccion=="identidad_apertura" y no por el id fijo "p00" porque sin plano
    de identidad el id p00 pasa a ser el primer plano de contenido real, y
    pisarle el logo encima le taparía la imagen del caso."""
    logo = sessions.logo_path()
    if not logo:
        return
    plano = next(
        (p for p in guion.get("planos", []) if p.get("seccion") == "identidad_apertura"), None
    )
    if plano is None:
        return
    target_dir = dest_dir / "media" / plano["id"]
    target_dir.mkdir(parents=True, exist_ok=True)
    # "elegido" SIN índice (no "elegido_1"): _manual_override en
    # research_plano_media.py prueba primero "elegido_<N>.*" por toma y
    # cae a "elegido.*" si no hay uno específico -- así el logo cubre
    # TODAS las tomas del plano, sin importar en cuántas se termine
    # partiendo. Con "elegido_1" fijo, si p00 dura apenas más de 4s reales
    # (duracion_seg es solo estimado) se parte en 2 tomas y la 2da cae en
    # la búsqueda real: confirmado en corridas reales, eligió una moneda
    # de bitcoin de stock como "mejor match" para la query del logo.
    shutil.copy(logo, target_dir / f"elegido{logo.suffix}")


def _apply_cierre(dest_dir: Path, guion: dict) -> None:
    """Mismo mecanismo que _apply_logo, para el plano identidad_cierre (el
    logo final sobre negro puro -- contenido genérico que ninguna búsqueda
    de stock real puede encontrar, confirmado en corridas reales: siempre
    termina escalando a Claude). El id del plano varía (p09, p10, p11...
    según cuántos planos tenga el guion), así que se busca por
    seccion=="identidad_cierre" en vez de un id fijo -- ese valor sí es
    estable en todos los guiones (simétrico a identidad_apertura de p00)."""
    cierre = sessions.cierre_path()
    # Los mitos tienen su cartel: el del canal dice "¿QUÉ OPINAS DE ESTE
    # CASO?", y una leyenda no es un caso. Si no existe, el de siempre.
    if guion.get("formato") == "mito":
        cierre = sessions.cierre_mito_path() or cierre
    if not cierre:
        return
    plano = next(
        (p for p in guion.get("planos", []) if p.get("seccion") == "identidad_cierre"), None
    )
    if plano is None:
        return
    target_dir = dest_dir / "media" / plano["id"]
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(cierre, target_dir / f"elegido{cierre.suffix}")


def _apply_manual_images(slug: str, dest_dir: Path) -> None:
    manual_dir = ANDROID_IN / slug / "imagenes_manuales"
    if not manual_dir.exists():
        return
    for f in manual_dir.glob("*"):
        parts = f.stem.split("_")  # <plano>_<posicion>_<indice>
        if len(parts) < 3:
            continue
        plano_id, indice = parts[0], parts[-1]
        target_dir = dest_dir / "media" / plano_id
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(f, target_dir / f"elegido_{indice}{f.suffix}")


_PAUSA_MAX_SEG = 15.0


def _pausa_despues_seg(plano: dict) -> float:
    """Segundos de silencio a insertar DESPUÉS de este plano.

    Habilita el formato de preguntas: la pregunta se queda en pantalla
    mientras el espectador piensa, y recién después entra la respuesta.
    Funciona sin tocar el ensamblador porque el clip de un plano dura hasta
    el inicio del siguiente (ver render_timeline.py en illustrated-narrator),
    así que el silencio se absorbe como tiempo en pantalla del plano previo.
    """
    # También dentro de "audio": ahí la puso Claude en los dos mitos del
    # 26/09/2026 (mito-aluxes, mito-sip-keej), y es un lugar razonable -- la
    # pausa existe para que suene algo. Sin esto los videos salían sin
    # ninguna pausa, con el sonido de cada señal debajo de la voz.
    crudo = plano.get("pausa_despues_seg")
    if crudo is None:
        crudo = (plano.get("audio") or {}).get("pausa_despues_seg")
    try:
        pausa = float(crudo or 0)
    except (TypeError, ValueError):
        logger.warning("pausa_despues_seg inválida en %s, se ignora", plano.get("id"))
        return 0.0
    if pausa <= 0:
        return 0.0
    return min(pausa, _PAUSA_MAX_SEG)


def _generar_silencio(dest_dir: Path, plano_id: str, segundos: float) -> Path:
    """WAV de silencio con el MISMO formato que los de Kokoro: el concat
    demuxer de ffmpeg exige que todas las entradas coincidan en tasa de
    muestreo y canales, si no falla o produce audio corrupto."""
    silencios = dest_dir / "_silencios"
    silencios.mkdir(parents=True, exist_ok=True)
    destino = silencios / f"{plano_id}_pausa.wav"
    proc = _run([
        FFMPEG, "-y", "-f", "lavfi",
        "-i", f"anullsrc=channel_layout=mono:sample_rate=24000",
        "-t", f"{segundos:.3f}", "-acodec", "pcm_s16le", str(destino),
    ])
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg no pudo generar el silencio:\n{proc.stderr[-800:]}")
    return destino


def _setup_narrator_project(slug: str) -> None:
    src_guion = TTS_KOKORO_PROJECTS / slug / "guion.json"
    dest_dir = NARRATOR_PROJECTS / slug
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(src_guion, dest_dir / "guion.json")

    guion = json.loads(src_guion.read_text(encoding="utf-8"))
    planos = guion.get("planos", [])

    wav_dir = TTS_KOKORO_PROJECTS / slug / "narracion"
    list_path = dest_dir / "_concat_list.txt"
    with list_path.open("w", encoding="utf-8") as f:
        for plano in planos:
            wav = wav_dir / f"{plano['id']}.wav"
            f.write(f"file '{wav.as_posix()}'\n")
            pausa = _pausa_despues_seg(plano)
            if pausa:
                silencio = _generar_silencio(dest_dir, plano["id"], pausa)
                f.write(f"file '{silencio.as_posix()}'\n")

    narracion_wav = dest_dir / "narracion.wav"
    proc = _run([
        FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(list_path),
        "-ar", "48000", "-ac", "2", "-acodec", "pcm_s16le", str(narracion_wav),
    ])
    list_path.unlink(missing_ok=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg concat falló:\n{proc.stderr[-1500:]}")

    _apply_logo(dest_dir, guion)
    _apply_cierre(dest_dir, guion)
    # Antes de _apply_manual_images: si el usuario subió una imagen a mano
    # para un plano, esa gana sobre la tarjeta generada.
    quiz_cards.generar_tarjetas(guion, dest_dir)
    _apply_manual_images(slug, dest_dir)

    # Solo para guiones con pausas: ahí el alineador por Whisper se saltea
    # tramos y deja planos sin renderizar (ver escribir_alineacion_exacta).
    # Los guiones normales siguen usando la alineación por transcripción,
    # que es la que tolera que el audio no coincida exactamente con el texto.
    if any(_pausa_despues_seg(p) for p in planos):
        quiz_cards.escribir_alineacion_exacta(guion, wav_dir, dest_dir)


def _run_narrator_generate(slug: str, avatar: bool = False,
                           sin_ia: bool = False) -> tuple[bool, str]:
    # NARR_A1111_RESTART_BEFORE_USE=1: el fallback de video-IA daba 500 en
    # la segunda generación de una misma corrida (agotamiento de VRAM entre
    # generaciones consecutivas de AnimateDiff, confirmado en corrida real
    # -- ver a1111_lifecycle.py en illustrated-narrator). Solo acá, en las
    # corridas automáticas del bot -- nunca por default en una sesión
    # interactiva, donde reiniciar A1111 solo sería sorpresivo.
    env = {
        **os.environ,
        # El gato del logo presenta el video desde la esquina, con la boca
        # articulando por visemas (ver rhubarb_visemes.py en illustrated-
        # narrator). Si falta el binario de Rhubarb o los sprites, el narrador
        # cae solo a voz y el video sale igual.
        "NARR_NARRACION": "mascota",
        "NARR_MASCOTA_PATH": MASCOTA_PATH,
        "NARR_MASCOTA_POS": "bottom-right",
        # El emblema es cuadrado: 0.157 del alto = 302 px, o sea 28% del ancho.
        "NARR_MASCOTA_HEIGHT_FRAC": "0.157",
        # Los subtítulos van más arriba de lo normal (14%): con la mascota en
        # la esquina, a la altura de siempre le pasan por encima.
        "SUBS_MARGEN_INFERIOR_REL": "0.24",
        # La tarjeta de cierre tiene que pedir LO MISMO que pide la voz. El
        # default del narrador es "SÍGUEME PARA MÁS HISTORIAS", y desde que la
        # narración de identidad_cierre pide un comentario (17/09/2026) eso se
        # contradecía en pantalla: la voz pedía una cosa y el cartel otra.
        "NARR_CTA_TEXT": "COMENTA QUÉ OPINAS",
        "NARR_A1111_RESTART_BEFORE_USE": "1",
    }
    if sin_ia:
        # Video con evidencia real (ver evidencia.py): sin generador de
        # imágenes ni video-IA de respaldo. Si una toma se quedara sin pieza,
        # el narrador falla en vez de rellenarla con IA.
        env["NARR_IMAGE_BACKEND"] = "none"
        env["NARR_VIDEO_FALLBACK_MAX_PLANOS"] = "0"
    if voz_de_true_crime(slug, avatar):
        # Con la voz de true crime (28/09/2026) el gato no habla: con otra voz
        # que no es la de siempre, un gato moviendo la boca no tenía sentido.
        # Queda solo el emblema, chico y fijo arriba a la izquierda, como en el
        # video de Tacuba (ver logo_overlay.py en illustrated-narrator). Sin
        # mascota en la esquina los subtítulos vuelven a su altura normal.
        env["NARR_NARRACION"] = "voz"
        env.pop("NARR_MASCOTA_PATH", None)
        env.pop("NARR_MASCOTA_POS", None)
        env.pop("NARR_MASCOTA_HEIGHT_FRAC", None)
        env.pop("SUBS_MARGEN_INFERIOR_REL", None)
        env["NARR_LOGO_ESQUINA"] = EMBLEMA_ESQUINA
        # Más abajo que en Tacuba (y=90): acá hay rótulo arriba al centro, que
        # ocupa de ~70 a ~120 px, y un rótulo largo pasaba por debajo del logo
        # (visto en el primer render real, guion-tierra-blanca-veracruz-fish3).
        env["NARR_LOGO_ESQUINA_Y"] = "150"
        # Sin cama de fondo (11/10/2026, decisión de Javier): la música se le
        # pone en TikTok, con un sonido en tendencia (liga el video a la página
        # del sonido). El pad sintético del narrador casi no se oía y con la
        # música de TikTok encima quedarían dos fondos peleándose.
        env["NARR_AUDIO_BED"] = "0"
    if avatar:
        # Modo vaca morada: presenta Javier en persona, no el gato. Los dos no
        # entran -- ocupan la misma esquina -- y el presentador es más grande
        # (0.55 del ancho), así que los subtítulos suben más todavía.
        env["NARR_NARRACION"] = "voz"
        env.pop("NARR_MASCOTA_PATH", None)
        env.pop("NARR_MASCOTA_POS", None)
        env.pop("NARR_MASCOTA_HEIGHT_FRAC", None)
        env["SUBS_MARGEN_INFERIOR_REL"] = avatar_presentador.SUBS_MARGEN
    proc = _run(
        [POETRY_EXE, "run", "narrator", "generate", slug, "--vertical"],
        cwd=r"C:\illustrated-narrator", env=env,
    )
    ok = proc.returncode == 0
    return ok, (proc.stdout[-3000:] + proc.stderr[-1500:])


def publish_to_facebook(slug: str) -> tuple[bool, str]:
    """Dispara `narrator publish` (Facebook Graph API, ya configurado y
    verificado con una llamada real -- ver facebook_adapter.py). A PROPÓSITO
    no se llama desde run()/_generarlote -- es manual, disparado a mano por
    el usuario (/publicarfacebook) hasta que decida engancharlo al pipeline."""
    proc = _run(
        [POETRY_EXE, "run", "narrator", "publish", slug],
        cwd=r"C:\illustrated-narrator",
    )
    ok = proc.returncode == 0
    return ok, (proc.stdout[-2000:] + proc.stderr[-1000:])


def publish_to_tiktok(slug: str) -> tuple[bool, str]:
    """Dispara `narrator publish-tiktok`. Sin auditoría de TikTok todavía,
    el video queda en modo privado (SELF_ONLY) -- ver tiktok_publisher.py.
    Igual que Facebook, manual a propósito: no se llama desde run()."""
    proc = _run(
        [POETRY_EXE, "run", "narrator", "publish-tiktok", slug],
        cwd=r"C:\illustrated-narrator",
    )
    ok = proc.returncode == 0
    return ok, (proc.stdout[-2000:] + proc.stderr[-1000:])


def _delete_flagged_assets(slug: str, flagged: list[media_check.FlaggedShot]) -> None:
    project = NARRATOR_PROJECTS / slug
    for shot in flagged:
        for rel in (f"images/{shot.shot_id}.png", f"images/clean/{shot.shot_id}.png"):
            p = project / rel
            if p.exists():
                p.unlink()
        video = project / "media" / "videos" / f"{shot.shot_id}.mp4"
        if video.exists():
            video.unlink()


_MENSAJE_TOKEN_DRIVE = (
    "⚠️ El video de *{slug}* se generó bien, pero **caducó el token de Google Drive** "
    "y no se pudo subir.\n\n"
    "Esto lo tenés que hacer vos: reautorizar necesita abrir el navegador e iniciar "
    "sesión en Google.\n\n"
    "```\n"
    "C:\\dato-mata-gato-bot\\.venv\\Scripts\\python.exe -m dato_mata_gato_bot.drive_auth\n"
    "```\n\n"
    "Imprime una URL: abrila, aceptá con la cuenta del canal, y volvé a correr el lote "
    "(los videos ya generados no se rehacen).\n\n"
    "Para que no se repita cada semana: en Google Cloud Console → Pantalla de "
    "consentimiento de OAuth, pasá el estado de publicación de *Testing* a *In "
    "production*. En Testing, Google caduca el token a los 7 días."
)


def _es_token_drive_vencido(exc: Exception) -> bool:
    """El token de Drive caducó o fue revocado.

    Con la app de OAuth en estado 'Testing', Google caduca los refresh tokens
    a los 7 DÍAS exactos aunque se usen -- confirmado en una corrida real: el
    token se generó el 27/08 22:23 y el lote del 03/09 falló entero, los cinco
    videos, con `invalid_grant`.
    """
    texto = f"{type(exc).__name__}: {exc}".lower()
    return "invalid_grant" in texto or "expired or revoked" in texto


def _upload_to_drive(slug: str) -> str:
    # Leído en el momento (no como constante a nivel de módulo): bot.py
    # importa este módulo ANTES de llamar load_dotenv() (import primero,
    # load_dotenv() recién en la línea siguiente -- ver bot.py), así que
    # una constante de módulo acá quedaba fija en "" para siempre, sin
    # importar qué tuviera el .env -- confirmado en una corrida real: la
    # subida fallaba con "Falta GOOGLE_DRIVE_FOLDER_ID" aunque el .env sí
    # lo tenía.
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
    if not folder_id:
        raise RuntimeError("Falta GOOGLE_DRIVE_FOLDER_ID en el .env del bot")
    guion = json.loads((NARRATOR_PROJECTS / slug / "guion.json").read_text(encoding="utf-8"))
    titulo = guion.get("titulo") or slug
    fecha = publish_schedule.assign_date(slug)
    final_mp4 = NARRATOR_PROJECTS / slug / "final.mp4"
    nombre, link = drive_upload.upload_video(final_mp4, titulo, fecha, folder_id)
    publish_schedule.record_upload(slug, nombre, link)
    return f"{nombre} (publicar el {fecha[:2]}/{fecha[2:4]}/{fecha[4:]}) -> {link}"


_MENSAJE_TOKEN_DRIVE_TROZOS = (
    "⚠️ Los {n} trozos se cortaron bien y están en `{carpeta}`, pero **caducó el "
    "token de Google Drive** y no se pudieron subir.\n\n"
    "Esto lo tenés que hacer vos: reautorizar necesita abrir el navegador e iniciar "
    "sesión en Google.\n\n"
    "```\n"
    "C:\\dato-mata-gato-bot\\.venv\\Scripts\\python.exe -m dato_mata_gato_bot.drive_auth\n"
    "```\n\n"
    "Imprime una URL: abrila, aceptá con la cuenta del canal, y volvé a mandar el "
    "mismo /shorts -- el video ya está bajado, así que la segunda vez va directo."
)


@dataclass
class TrozoSubido:
    indice: int
    nombre: str
    link: str
    inicio_seg: float
    fin_seg: float


@dataclass
class ResultadoTroceo:
    ok: bool
    mensaje: str
    titulo: str = ""
    carpeta_link: str = ""
    trozos: list[TrozoSubido] = field(default_factory=list)


def info_video_a_trocear(url: str) -> dict | None:
    """Título, duración y cuántos trozos saldrían, sin descargar nada.

    Se consulta ANTES de empezar para poder avisar: una película de hora y
    media son ~73 trozos y más de 3 GB de subida a Drive, y eso hay que
    saberlo antes de arrancar, no una hora después.
    """
    if not SHORTS_FACTORY_PY.exists():
        return None
    proc = _run(
        [str(SHORTS_FACTORY_PY), "-m", "shorts_factory.cli.main", "info-video", url],
        cwd=str(SHORTS_FACTORY_DIR),
        timeout=180,
    )
    if proc.returncode != 0:
        logger.warning("info-video falló para %s: %s", url, (proc.stdout + proc.stderr)[-500:])
        return None
    for linea in reversed(f"{proc.stdout}\n{proc.stderr}".splitlines()):
        if linea.startswith("INFO "):
            try:
                return json.loads(linea[len("INFO "):])
            except json.JSONDecodeError:
                return None
    return None


def trocear_y_subir(url: str, progreso=None) -> ResultadoTroceo:
    """Baja un video, lo parte en trozos de 1 minuto y los sube a Drive.

    El corte es LITERAL cada 60s: no se analiza dónde está lo interesante.
    Para eso está `analyze` en Shorts Factory, que es justo lo que acá se
    saltea a propósito.
    """
    def avisar(paso: str) -> None:
        logger.info("Troceo: %s", paso)
        if progreso is not None:
            progreso(paso)

    if not SHORTS_FACTORY_PY.exists():
        return ResultadoTroceo(False, f"No existe el intérprete {SHORTS_FACTORY_PY}")

    destino = SHORTS_FACTORY_DIR / "data" / "troceos" / _slug_de_url(url)
    avisar("bajando y cortando el video")
    proc = _run(
        [str(SHORTS_FACTORY_PY), "-m", "shorts_factory.cli.main", "trocear", url,
         "--salida", str(destino), "--logo", LOGO_TROZOS],
        cwd=str(SHORTS_FACTORY_DIR),
        timeout=TIMEOUT_TROCEO,
    )
    salida = f"{proc.stdout}\n{proc.stderr}"
    if proc.returncode != 0:
        # Al log completo, no solo a Telegram: el mensaje que ve el usuario va
        # recortado a 1500 caracteres, y la causa real suele estar más arriba.
        logger.error("Troceo de %s falló (código %d):\n%s", url, proc.returncode, salida)
        return ResultadoTroceo(False, f"El troceo falló:\n{salida[-1500:]}")

    datos = _parsear_resultado_troceo(salida)
    if datos is None:
        logger.error("Troceo de %s sin línea RESULTADO:\n%s", url, salida)
        return ResultadoTroceo(False, f"No pude leer el resultado del troceo:\n{salida[-1500:]}")

    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
    if not folder_id:
        return ResultadoTroceo(False, "Falta GOOGLE_DRIVE_FOLDER_ID en el .env del bot")

    titulo = datos["titulo"]
    trozos = datos["trozos"]
    subidos: list[TrozoSubido] = []
    try:
        raiz = drive_upload.asegurar_carpeta(CARPETA_TROZOS, folder_id)
        # Subcarpeta por video: con el ID en el nombre, dos videos que se llamen
        # igual no terminan mezclando sus trozos en la misma carpeta.
        carpeta = drive_upload.asegurar_carpeta(
            f"{drive_upload.slugify_titulo(titulo)}_{datos['video_id']}", raiz
        )
        for t in trozos:
            avisar(f"subiendo {t['indice']}/{len(trozos)} a Drive")
            nombre = f"{drive_upload.slugify_titulo(titulo)}_parte{t['indice']:02d}.mp4"
            # reusar_existente: repetir un /shorts que se cortó a mitad retoma
            # donde quedó, en vez de dejar cada trozo ya subido duplicado.
            nombre, link = drive_upload.subir_archivo(
                Path(t["path"]), nombre, carpeta, reusar_existente=True
            )
            subidos.append(TrozoSubido(
                indice=t["indice"], nombre=nombre, link=link,
                inicio_seg=t["inicio"], fin_seg=t["fin"],
            ))
    except Exception as exc:  # noqa: BLE001 -- los trozos ya están cortados en disco
        if _es_token_drive_vencido(exc):
            return ResultadoTroceo(False, _MENSAJE_TOKEN_DRIVE_TROZOS.format(
                n=len(trozos), carpeta=destino,
            ))
        return ResultadoTroceo(
            False,
            f"Los {len(trozos)} trozos quedaron en {destino}, pero falló la subida a "
            f"Drive:\n{exc}",
        )

    return ResultadoTroceo(
        ok=True,
        mensaje=f"{len(subidos)} trozo(s) de {datos['duracion_seg'] / 60:.1f} min de video",
        titulo=titulo,
        carpeta_link=f"https://drive.google.com/drive/folders/{carpeta}",
        trozos=subidos,
    )


def _parsear_resultado_troceo(salida: str) -> dict | None:
    """La línea `RESULTADO {json}` que imprime el CLI de Shorts Factory.

    Se busca la línea y no se parsea todo stdout porque el CLI también imprime
    los avisos de progreso y los logs de yt-dlp y ffmpeg.
    """
    for linea in reversed(salida.splitlines()):
        if linea.startswith("RESULTADO "):
            try:
                return json.loads(linea[len("RESULTADO "):])
            except json.JSONDecodeError:
                return None
    return None


def _slug_de_url(url: str) -> str:
    """Nombre de carpeta local seguro, derivado de la URL."""
    limpio = re.sub(r"[^a-zA-Z0-9]+", "_", url).strip("_")
    return limpio[-60:] or "video"


def ajuste_del_gancho(slug: str, avatar: bool = False) -> dict | None:
    """Cómo se dice el gancho (primer plano) con la voz de true crime.

    Prueba de ganchos del 11/10/2026: el mismo gancho con Fish 3 v3 en varias
    configuraciones; el usuario eligió de oído la "B", un poco más rápida y
    más pegada a la voz (guidance 3.0, velocidad 1.08). Solo el gancho: el
    resto del video no se probó así. Se apaga quitando las dos variables.
    """
    if not voz_de_true_crime(slug, avatar):
        return None
    ajuste = {}
    velocidad = (os.getenv("VOICESTUDIO_GANCHO_VELOCIDAD") or "").strip()
    guidance = (os.getenv("VOICESTUDIO_GANCHO_GUIDANCE") or "").strip()
    if velocidad:
        ajuste["velocidad"] = float(velocidad)
    if guidance:
        ajuste["guidance"] = float(guidance)
    return ajuste or None


# Capa de render con Remotion (13/10/2026): el POC de illustrated-narrator/
# poc_remotion, aprobado por Javier sobre el video del IMSS. Subtítulos karaoke
# en caja, títulos animados, Ken Burns con fundidos y el cierre como gráfico
# animado, en azul marino y dorado. Toma lo que ya dejó `narrator generate`
# (audio, palabras, planos alineados, imágenes): el narrador NO cambia, y su
# final.mp4 de FFmpeg queda de respaldo.
REMOTION_DIR = Path(r"C:\illustrated-narrator\poc_remotion")
NARRATOR_PY = r"C:\illustrated-narrator\.venv\Scripts\python.exe"
TIMEOUT_REMOTION = 30 * 60  # tarda ~1.2x lo que dura el video


def modo_render(slug: str, avatar: bool = False) -> str:
    """'remotion' o 'ffmpeg' para este video.

    RENDER_VIDEO en el .env: 'ffmpeg' (default, como siempre), 'remotion', o
    'mitad' (prueba A/B: se alterna por slug, estable, sin relación con la
    prueba de voces). El guion puede fijarlo con "render". Solo los true crime
    y cercanía sin presentador: el layout de Remotion no tiene lugar para él.
    """
    if not voz_de_true_crime(slug, avatar):
        return "ffmpeg"
    try:
        elegido = json.loads((ANDROID_IN / slug / "guion.json").read_text(encoding="utf-8")).get("render")
    except (OSError, ValueError):
        elegido = None
    if elegido in ("remotion", "ffmpeg"):
        return elegido
    modo = (os.getenv("RENDER_VIDEO") or "ffmpeg").strip().lower()
    if modo == "mitad":
        return "remotion" if zlib.crc32(f"render:{slug}".encode("utf-8")) % 2 else "ffmpeg"
    return "remotion" if modo == "remotion" else "ffmpeg"


def render_plus() -> bool:
    """RENDER_PLUS (default 1): Remotion con las animaciones de retención
    (CapituloPlus, 13/10/2026): mapa del lugar, contador del gancho, tarjeta de
    contradicción, fichas animadas que resaltan lo que dice la voz, palabras
    clave en rojo y destellos. Salen del bloque "plus" del guion; lo que falte
    se omite. 0 = el Capitulo de antes."""
    return (os.getenv("RENDER_PLUS") or "1").strip() != "0"


def render_remotion(slug: str) -> tuple[bool, str]:
    """Renderiza con Remotion y, si sale bien, lo deja como final.mp4.

    El final de FFmpeg se guarda como final_ffmpeg.mp4: si Remotion falla, el
    video de siempre queda donde estaba y el lote sigue. Las copias que el
    script hace en public/ y out/ se borran al terminar (~70 MB por video).
    """
    proyecto = NARRATOR_PROJECTS / slug
    plus = render_plus()
    script = "render_plus.py" if plus else "render_capitulo.py"
    salida = REMOTION_DIR / "out" / (f"{slug}_plus.mp4" if plus else f"{slug}.mp4")
    try:
        proc = subprocess.run(
            [NARRATOR_PY, str(REMOTION_DIR / "scripts" / script), slug],
            cwd=REMOTION_DIR, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=TIMEOUT_REMOTION, env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired:
        return False, f"se pasó de {TIMEOUT_REMOTION // 60} min"
    finally:
        shutil.rmtree(REMOTION_DIR / "public" / slug, ignore_errors=True)
    if proc.returncode != 0 or not salida.exists() or salida.stat().st_size < 100_000:
        salida.unlink(missing_ok=True)
        return False, (proc.stderr or proc.stdout)[-1500:]
    final = proyecto / "final.mp4"
    respaldo = proyecto / "final_ffmpeg.mp4"
    if final.exists():
        respaldo.unlink(missing_ok=True)
        final.rename(respaldo)
    shutil.move(str(salida), str(final))
    # La línea "plus: ..." dice qué animaciones entraron (va al aviso de Telegram).
    resumen = next((l for l in proc.stdout.splitlines() if l.startswith("plus: ") and "fichas" in l), "")
    return True, resumen or proc.stdout[-300:]


def velocidad_de_la_voz(slug: str, avatar: bool = False) -> float | None:
    """Velocidad de TODO el video para la voz nueva de Javier, o None.

    El POC del 11/10/2026 (Ed Gein) salió en 75.7 s contra 59.3 con Fish 3: el
    clon de "sin nombre.wav" habla ~25% más lento. A Fish 3 no se le toca.
    """
    if not voz_de_true_crime(slug, avatar) or voz_narrador(slug) != "javier":
        return None
    v = (os.getenv("VOICESTUDIO_VELOCIDAD_JAVIER") or "").strip()
    return float(v) if v else None


def _stage_guion_for_tts(slug: str, avatar: bool = False) -> None:
    src = ANDROID_IN / slug / "guion.json"
    dest_dir = TTS_KOKORO_PROJECTS / slug
    dest_dir.mkdir(parents=True, exist_ok=True)
    ajuste = ajuste_del_gancho(slug, avatar)
    base = velocidad_de_la_voz(slug, avatar)
    if not ajuste and not base:
        shutil.copy(src, dest_dir / "guion.json")
        return
    guion = json.loads(src.read_text(encoding="utf-8"))
    planos = guion.get("planos") or []
    # Lo que el guion ya traiga escrito en "voz" se respeta.
    gancho_propio = bool(planos) and "voz" in planos[0]
    if base:
        for p in planos:
            p.setdefault("voz", {}).setdefault("velocidad", base)
    if planos and ajuste and not gancho_propio:
        # El gancho nunca va más lento que el resto del video.
        planos[0]["voz"] = {**ajuste, "velocidad": max(ajuste.get("velocidad", 1.0), base or 1.0)}
    (dest_dir / "guion.json").write_text(json.dumps(guion, ensure_ascii=False, indent=2),
                                         encoding="utf-8")


def _archivar_local(slug: str, final_mp4: Path, carpeta: Path) -> Path:
    """Copia el video a `carpeta` con el NOMBRE CORTO del caso.

    El nombre sale del `titulo` del guion, que desde el 17/09/2026 es el
    nombre corto ("Caso Paulette", "Villas de Salvárcar") y no la primera
    frase hablada. Si dos casos comparten título se numera, en vez de que el
    segundo pise al primero sin avisar.
    """
    carpeta.mkdir(parents=True, exist_ok=True)
    guion = json.loads((NARRATOR_PROJECTS / slug / "guion.json").read_text(encoding="utf-8"))
    titulo = (guion.get("titulo") or guion.get("meta", {}).get("titulo") or slug).strip()
    base = drive_upload.slugify_titulo(titulo) or slug
    destino = carpeta / f"{base}.mp4"
    n = 2
    while destino.exists():
        destino = carpeta / f"{base}_{n}.mp4"
        n += 1
    shutil.copy2(final_mp4, destino)
    return destino


def run(slug: str, voz: str, chat_id: int | None = None,
        avatar: bool = False, avatar_num: int | None = None,
        destino_local: Path | None = None) -> PipelineResult:
    """Corre todo el pipeline sin Claude. Si algo requiere juicio (país
    incoherente que no se resolvió solo, o una toma sin medio), devuelve
    necesita_claude=True en vez de intentar decidir por su cuenta."""

    def progreso(paso: str) -> None:
        logger.info("Progreso %s: %s", slug, paso)
        if chat_id is not None:
            sessions.set_progress(chat_id, paso)

    guion_src = ANDROID_IN / slug / "guion.json"
    if not guion_src.exists():
        return PipelineResult(False, f"No existe {guion_src}", necesita_claude=False)
    # Evidencia real (29/09/2026): si el guion trae su lista de evidencia, se
    # arma ANTES de todo y el video sale sin una sola imagen de IA. Va antes de
    # _stage_guion_for_tts porque preparar() escribe en el guion (movimiento
    # calmo en los planos con texto) y esa versión es la que tiene que viajar.
    sin_ia = evidencia.tiene_evidencia(json.loads(guion_src.read_text(encoding="utf-8")))
    aviso_evidencia = ""
    if sin_ia:
        progreso("armando la evidencia real")
        reporte = evidencia.preparar(slug)
        aviso_evidencia = reporte.resumen()
        if reporte.reales == 0:
            # Sin una sola pieza real no se hace el video: rellenarlo con IA es
            # justo lo que esto vino a eliminar. No escala a Claude: hay que
            # revisar las fuentes del caso, no reintentar.
            return PipelineResult(
                False, f"{slug}: sin evidencia real utilizable ({aviso_evidencia}). "
                "No se genera con IA.\n" + "\n".join(
                    f"- {k}: {v}" for k, v in reporte.fallidas.items()),
                necesita_claude=False)
    _stage_guion_for_tts(slug, avatar)
    if not sin_ia:
        _kick_off_a1111_if_needed()

    # Con VoiceStudio esto tarda ~13x el largo del audio (CPU), asi que el
    # aviso dice QUE motor esta corriendo: si no, un lote de 2 horas parece
    # colgado y encima nombrando al motor equivocado.
    # Docker se apagó dos veces el 13-14/10/2026 (una a media corrida, otra con
    # un reinicio de Windows): antes de cada voz se levanta si hace falta, igual
    # que en la fábrica. Si no levanta, el video falla aquí con el motivo.
    if motor_tts() == "voicestudio":
        from dato_mata_gato_bot import fabrica  # import tardío: fabrica importa este módulo
        problema = fabrica.asegurar_infra()
        if problema:
            return PipelineResult(False, f"La voz no está disponible: {problema}", necesita_claude=False)

    progreso(f"generando audio ({motor_tts()})")
    ok, out = _generate_audio(slug, voz, avatar=avatar)
    if not ok:
        return PipelineResult(False, out, necesita_claude=True)

    progreso("armando proyecto en illustrated-narrator")
    try:
        _setup_narrator_project(slug)
    except Exception as exc:  # setup con ffmpeg/archivos -- error real, no ambiguedad
        return PipelineResult(False, str(exc), necesita_claude=True)

    progreso("corriendo narrator generate (intento 1)")
    ok, out = _run_narrator_generate(slug, avatar, sin_ia)
    if not ok and not sin_ia and _es_falla_de_a1111(out):
        # Un 500 de A1111 es falta de VRAM, no un guion roto: se cierra, se
        # vuelve a levantar limpio y se reintenta una vez. Sin esto, un video
        # entero se pierde por un tropiezo de memoria -- pasó el 18/09/2026
        # con guion-ficrea-fraude, el primero de un lote de treinta.
        logger.warning("A1111 falló para %s; lo reinicio y reintento", slug)
        progreso("A1111 se quedó sin memoria: lo reinicio y reintento")
        _detener_a1111()
        _kick_off_a1111_if_needed()
        # ESPERAR antes de reintentar. Sin esto el reintento salía corriendo
        # contra un A1111 que todavía estaba cargando el checkpoint y se
        # perdía igual que el primer intento -- o sea, el reintento no
        # reintentaba nada. Confirmado el 23/09/2026 con guion-mara-castilla:
        # los dos intentos fallaron en seis segundos con "A1111 no responde".
        progreso("esperando a que A1111 termine de cargar")
        _esperar_a1111()
        ok, out = _run_narrator_generate(slug, avatar)
    if not ok:
        # Al log COMPLETO antes de escalar: el mensaje que viaja a Claude y a
        # Telegram va recortado, y después no queda forma de saber por qué
        # escaló un video (confirmado el 14/09/2026: dos escalaciones en un
        # lote y ninguna dejó rastro de su causa).
        logger.error("narrator generate falló para %s:\n%s", slug, out)
        return PipelineResult(False, f"narrator generate falló:\n{out}", necesita_claude=True)

    progreso("revisando coherencia de medios")
    # Con evidencia no hay nada que revisar: las piezas las eligió la
    # investigación del caso, no una búsqueda por palabras. Y el reintento de
    # abajo borra la toma para que se regenere -- sin IA no habría con qué.
    flagged = [] if sin_ia else media_check.check_manifest(NARRATOR_PROJECTS, slug)
    for intento in range(MAX_AUTO_RETRIES):
        if not flagged:
            break
        logger.info("Reintento %d/%d por %d toma(s) marcadas", intento + 1, MAX_AUTO_RETRIES, len(flagged))
        progreso(f"reintento {intento + 1}/{MAX_AUTO_RETRIES} por {len(flagged)} toma(s) sospechosas")
        _delete_flagged_assets(slug, flagged)
        ok, out = _run_narrator_generate(slug, avatar)
        if not ok:
            logger.error("narrator generate falló en reintento para %s:\n%s", slug, out)
            return PipelineResult(False, f"narrator generate falló en reintento:\n{out}", necesita_claude=True)
        flagged = media_check.check_manifest(NARRATOR_PROJECTS, slug)

    final_mp4 = NARRATOR_PROJECTS / slug / "final.mp4"
    if not final_mp4.exists():
        return PipelineResult(False, "narrator generate terminó pero no existe final.mp4", necesita_claude=True)

    if flagged:
        detalle = "\n".join(f"- {s.shot_id}: {s.reason} ({s.detalle})" for s in flagged)
        return PipelineResult(
            False,
            f"Quedaron {len(flagged)} toma(s) sin resolver tras {MAX_AUTO_RETRIES} "
            f"reintentos automáticos:\n{detalle}",
            necesita_claude=True, flagged=flagged,
        )

    aviso_render = ""
    if modo_render(slug, avatar) == "remotion":
        progreso("render con Remotion")
        ok_r, detalle_r = render_remotion(slug)
        if ok_r:
            aviso_render = ("render: Remotion + animaciones (" + detalle_r[len("plus: "):] + ")"
                            if detalle_r.startswith("plus: ") else "render: Remotion")
        else:
            aviso_render = f"render: FFmpeg (Remotion falló: {detalle_r[-300:]})"
        aviso_evidencia = "\n".join(x for x in (aviso_evidencia, aviso_render) if x)
    elif voz_de_true_crime(slug, avatar) and (os.getenv("RENDER_VIDEO") or "").strip():
        aviso_evidencia = "\n".join(x for x in (aviso_evidencia, "render: FFmpeg") if x)

    if avatar:
        # Último paso y el más caro. Va acá a propósito: si falla, el video del
        # pipeline ya está entero en disco y se puede publicar sin presentador
        # en vez de perder toda la corrida.
        # A1111 se queda con 6.6 GB de los 8 aunque esté ocioso, y MuseTalk
        # necesita 2-3. Si sigue abierto, el paso de labios muere con "not
        # enough GPU video memory" -- el mismo final que tuvo la corrida del
        # 16/09/2026 con un juego abierto.
        if _detener_a1111():
            progreso("cerré A1111 para liberar la GPU")
        progreso("agregando el presentador (~35 min)")
        try:
            avatar_presentador.componer(final_mp4, progreso, avatar_num)
        except Exception as exc:  # noqa: BLE001 -- el video base sigue sirviendo
            logger.error("El presentador falló para %s:\n%s", slug, exc)
            return PipelineResult(
                False,
                f"El video quedó generado en {final_mp4} pero falló el "
                f"presentador:\n{exc}",
                necesita_claude=True,
            )

    if destino_local is not None:
        # Modo lote grande: el video se archiva en disco y NO se sube ni se le
        # asigna fecha de publicación. Son treinta videos para revisar y
        # publicar a mano, no una tanda del calendario.
        progreso("archivando el video")
        try:
            destino = _archivar_local(slug, final_mp4, destino_local)
        except Exception as exc:  # noqa: BLE001 -- el video existe, solo falló la copia
            return PipelineResult(
                False, f"Video generado pero no se pudo archivar:\n{exc}",
                necesita_claude=True,
            )
        return PipelineResult(True, f"Video listo: {destino}" + _notas(slug, aviso_evidencia, avatar))

    progreso("subiendo a Google Drive")
    try:
        detalle = _upload_to_drive(slug)
    except Exception as exc:  # noqa: BLE001 — el video ya existe local, solo falló la subida
        if _es_token_drive_vencido(exc):
            # Escalarlo a Claude no sirve: reautorizar exige que una PERSONA
            # abra el navegador e inicie sesión en Google. Se le avisa al
            # usuario con el comando exacto, y necesita_claude=False para no
            # gastar una corrida de Claude en algo que no puede resolver.
            return PipelineResult(False, _MENSAJE_TOKEN_DRIVE.format(slug=slug))
        return PipelineResult(
            False, f"Video generado pero falló la subida a Drive:\n{exc}", necesita_claude=True
        )
    return PipelineResult(True, f"Video listo y subido a Drive, sin intervención de Claude: {detalle}"
                          + _notas(slug, aviso_evidencia, avatar))


def nombres_dudosos(slug: str) -> list[str]:
    """Nombres propios del guion que no aparecen en lo que Whisper oyó.

    Usa la transcripción que el narrador ya hizo para alinear: no cuesta nada
    extra. Es un aviso para escuchar esas palabras, no una prueba -- el Whisper
    del narrador es el modelo chico. En Tierra Blanca (28/09/2026) la voz se
    comió "Mario" en una lista de cuatro nombres y se saltó "Tlalixcoyan"
    entero; los dos habrían salido acá.
    """
    import difflib
    import unicodedata

    def plano(t: str) -> str:
        t = unicodedata.normalize("NFD", t.lower())
        return "".join(c for c in t if unicodedata.category(c) != "Mn")

    try:
        guion = json.loads((ANDROID_IN / slug / "guion.json").read_text(encoding="utf-8"))
        oido = json.loads((NARRATOR_PROJECTS / slug / "transcript.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    oidas = {plano(re.sub(r"\W", "", w.get("text", ""))) for w in oido.get("words", [])}
    oidas.discard("")
    dudosos = []
    for p in guion.get("planos", []):
        texto = p.get("narracion", "")
        # Palabras con mayúscula que no abren frase: nombres, lugares, siglas.
        for m in re.finditer(r"(?<![.!?¿¡]\s)(?<!^)\b([A-ZÁÉÍÓÚÑ][\wáéíóúñ]+)", texto):
            palabra = plano(m.group(1))
            if len(palabra) < 3 or palabra in oidas:
                continue
            if not difflib.get_close_matches(palabra, oidas, n=1, cutoff=0.8):
                dudosos.append(m.group(1))
    return list(dict.fromkeys(dudosos))


def _notas(slug: str, aviso_evidencia: str, avatar: bool = False) -> str:
    notas = [aviso_evidencia] if aviso_evidencia else []
    if voz_de_true_crime(slug, avatar) and VOCES_CRIMEN["javier"]():
        # Prueba de voces: al publicar hay que saber cuál es cuál.
        notas.append(f"voz: {NOMBRE_VOZ[voz_narrador(slug)]}")
    dudosos = nombres_dudosos(slug)
    if dudosos:
        notas.append("escuchar: " + ", ".join(dudosos)
                     + " (no se oyeron claros; si están mal, van a pronunciacion.json)")
    return "".join(f"\n{n}" for n in notas)
