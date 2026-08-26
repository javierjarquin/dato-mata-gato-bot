"""Orquestador determinístico del pipeline completo — CERO Claude.
Corre tts-kokoro + illustrated-narrator directo, valida el resultado con
media_check (heurística de país incoherente / toma sin medio), y
reintenta solo. Si tras los reintentos automáticos algo sigue ambiguo,
devuelve necesita_claude=True para que el llamador escale — Claude se usa
solo para lo que la heurística no puede resolver, no para toda la corrida."""

import json
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import requests

from dato_mata_gato_bot import drive_upload, media_check, publish_schedule, sessions

logger = logging.getLogger(__name__)

TTS_KOKORO_PY = r"C:\tts-kokoro\.venv\Scripts\python.exe"
TTS_KOKORO_PROJECTS = Path(r"C:\tts-kokoro\projects")
NARRATOR_PROJECTS = Path(r"C:\illustrated-narrator\projects")
POETRY_EXE = r"C:\Users\jarqu\AppData\Roaming\Python\Scripts\poetry.exe"
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


def _run(args: list[str], cwd: str | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
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
        stdout, stderr = proc.communicate(timeout=SUBPROCESS_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        # No se relanza el TimeoutExpired: antes se propagaba sin atrapar
        # hasta bot.py (pipeline.run no tiene try/except alrededor), lo que
        # dejaba la corrida colgada en el hilo del bot sin que el usuario
        # recibiera jamás una respuesta en Telegram. Devolver un
        # CompletedProcess con returncode != 0 reusa el mismo camino de
        # necesita_claude=True que ya usa cada otro fallo de este archivo.
        logger.error(
            "Timeout de %ds corriendo %s -- matando árbol de procesos (PID %d)",
            SUBPROCESS_TIMEOUT_SECONDS, args[0], proc.pid,
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


def _generate_audio(slug: str, voz: str, velocidad: float = 1.0) -> tuple[bool, str]:
    guion_path = TTS_KOKORO_PROJECTS / slug / "guion.json"
    proc = _run([
        TTS_KOKORO_PY, "-m", "tts_kokoro.cli",
        "--guion", str(guion_path), "--voz", voz, "--velocidad", str(velocidad),
    ])
    if proc.returncode != 0:
        return False, f"tts-kokoro falló:\n{proc.stderr[-1500:]}"
    return True, proc.stdout


def _apply_logo(dest_dir: Path) -> None:
    logo = sessions.logo_path()
    if not logo:
        return
    target_dir = dest_dir / "media" / "p00"
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


def _setup_narrator_project(slug: str) -> None:
    src_guion = TTS_KOKORO_PROJECTS / slug / "guion.json"
    dest_dir = NARRATOR_PROJECTS / slug
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(src_guion, dest_dir / "guion.json")

    guion = json.loads(src_guion.read_text(encoding="utf-8"))
    plano_ids = [p["id"] for p in guion.get("planos", [])]

    wav_dir = TTS_KOKORO_PROJECTS / slug / "narracion"
    list_path = dest_dir / "_concat_list.txt"
    with list_path.open("w", encoding="utf-8") as f:
        for pid in plano_ids:
            wav = wav_dir / f"{pid}.wav"
            f.write(f"file '{wav.as_posix()}'\n")

    narracion_wav = dest_dir / "narracion.wav"
    proc = _run([
        FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(list_path),
        "-ar", "48000", "-ac", "2", "-acodec", "pcm_s16le", str(narracion_wav),
    ])
    list_path.unlink(missing_ok=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg concat falló:\n{proc.stderr[-1500:]}")

    _apply_logo(dest_dir)
    _apply_cierre(dest_dir, guion)
    _apply_manual_images(slug, dest_dir)


def _run_narrator_generate(slug: str) -> tuple[bool, str]:
    # NARR_A1111_RESTART_BEFORE_USE=1: el fallback de video-IA daba 500 en
    # la segunda generación de una misma corrida (agotamiento de VRAM entre
    # generaciones consecutivas de AnimateDiff, confirmado en corrida real
    # -- ver a1111_lifecycle.py en illustrated-narrator). Solo acá, en las
    # corridas automáticas del bot -- nunca por default en una sesión
    # interactiva, donde reiniciar A1111 solo sería sorpresivo.
    env = {**os.environ, "NARR_NARRACION": "voz", "NARR_A1111_RESTART_BEFORE_USE": "1"}
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


def _stage_guion_for_tts(slug: str) -> None:
    src = ANDROID_IN / slug / "guion.json"
    dest_dir = TTS_KOKORO_PROJECTS / slug
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dest_dir / "guion.json")


def run(slug: str, voz: str, chat_id: int | None = None) -> PipelineResult:
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
    _stage_guion_for_tts(slug)
    _kick_off_a1111_if_needed()

    progreso("generando audio (tts-kokoro)")
    ok, out = _generate_audio(slug, voz)
    if not ok:
        return PipelineResult(False, out, necesita_claude=True)

    progreso("armando proyecto en illustrated-narrator")
    try:
        _setup_narrator_project(slug)
    except Exception as exc:  # setup con ffmpeg/archivos -- error real, no ambiguedad
        return PipelineResult(False, str(exc), necesita_claude=True)

    progreso("corriendo narrator generate (intento 1)")
    ok, out = _run_narrator_generate(slug)
    if not ok:
        return PipelineResult(False, f"narrator generate falló:\n{out}", necesita_claude=True)

    progreso("revisando coherencia de medios")
    flagged = media_check.check_manifest(NARRATOR_PROJECTS, slug)
    for intento in range(MAX_AUTO_RETRIES):
        if not flagged:
            break
        logger.info("Reintento %d/%d por %d toma(s) marcadas", intento + 1, MAX_AUTO_RETRIES, len(flagged))
        progreso(f"reintento {intento + 1}/{MAX_AUTO_RETRIES} por {len(flagged)} toma(s) sospechosas")
        _delete_flagged_assets(slug, flagged)
        ok, out = _run_narrator_generate(slug)
        if not ok:
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

    progreso("subiendo a Google Drive")
    try:
        detalle = _upload_to_drive(slug)
    except Exception as exc:  # noqa: BLE001 — el video ya existe local, solo falló la subida
        return PipelineResult(
            False, f"Video generado pero falló la subida a Drive:\n{exc}", necesita_claude=True
        )
    return PipelineResult(True, f"Video listo y subido a Drive, sin intervención de Claude: {detalle}")
