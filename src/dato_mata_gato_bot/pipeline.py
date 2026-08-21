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

from dato_mata_gato_bot import media_check, sessions

logger = logging.getLogger(__name__)

TTS_KOKORO_PY = r"C:\tts-kokoro\.venv\Scripts\python.exe"
TTS_KOKORO_PROJECTS = Path(r"C:\tts-kokoro\projects")
NARRATOR_PROJECTS = Path(r"C:\illustrated-narrator\projects")
POETRY_EXE = r"C:\Users\jarqu\AppData\Roaming\Python\Scripts\poetry.exe"
ANDROID_IN = Path(r"C:\Android_in")
ANDROID_OUT = Path(r"C:\Android_out")
FFMPEG = "ffmpeg"

MAX_AUTO_RETRIES = 2
SUBPROCESS_TIMEOUT_SECONDS = 60 * 60


@dataclass
class PipelineResult:
    ok: bool
    mensaje: str
    necesita_claude: bool = False
    flagged: list[media_check.FlaggedShot] = field(default_factory=list)


def _run(args: list[str], cwd: str | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    logger.info("Ejecutando: %s", " ".join(str(a) for a in args))
    return subprocess.run(
        args, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8",
        timeout=SUBPROCESS_TIMEOUT_SECONDS, creationflags=subprocess.CREATE_NO_WINDOW,
    )


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
    shutil.copy(logo, target_dir / f"elegido_1{logo.suffix}")


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
    _apply_manual_images(slug, dest_dir)


def _run_narrator_generate(slug: str) -> tuple[bool, str]:
    env = {**os.environ, "NARR_NARRACION": "voz"}
    proc = _run(
        [POETRY_EXE, "run", "narrator", "generate", slug, "--vertical"],
        cwd=r"C:\illustrated-narrator", env=env,
    )
    ok = proc.returncode == 0
    return ok, (proc.stdout[-3000:] + proc.stderr[-1500:])


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


def _copy_to_android_out(slug: str) -> Path:
    src = NARRATOR_PROJECTS / slug / "final.mp4"
    dest = ANDROID_OUT / f"{slug}.mp4"
    shutil.copy(src, dest)
    return dest


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

    progreso("copiando a Android_out")
    dest = _copy_to_android_out(slug)
    return PipelineResult(True, f"Video listo, sin intervención de Claude: {dest}")
