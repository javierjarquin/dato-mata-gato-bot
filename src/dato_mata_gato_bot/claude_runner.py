"""Invoca Claude Code CLI en modo no interactivo (--print), reusando una
sesión por chat de Telegram para que la conversación tenga memoria real."""

import json
import logging
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)

CLAUDE_EXE = "claude"
CWD = r"C:\illustrated-narrator"
ADD_DIRS = [r"C:\tts-kokoro", r"C:\Android_in", r"C:\Android_out"]

# Sin timeout corto: generar un video (transcripcion + investigacion de
# medios + ensamblado) toma facilmente 10-20 minutos.
SUBPROCESS_TIMEOUT_SECONDS = 60 * 60


@dataclass
class ClaudeTurnResult:
    ok: bool
    text: str
    raw: str


def run_turn(session_id: str, message: str, is_new_session: bool) -> ClaudeTurnResult:
    args = [
        CLAUDE_EXE,
        "-p", message,
        "--output-format", "json",
        "--permission-mode", "bypassPermissions",
    ]
    for d in ADD_DIRS:
        args += ["--add-dir", d]
    args += (["--session-id", session_id] if is_new_session else ["--resume", session_id])

    logger.info("Invocando claude (nueva=%s, session=%s)", is_new_session, session_id)
    try:
        proc = subprocess.run(
            args, cwd=CWD, capture_output=True, text=True, encoding="utf-8",
            timeout=SUBPROCESS_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return ClaudeTurnResult(ok=False, text="Se agotó el tiempo de espera (60 min).", raw="")

    if proc.returncode != 0:
        logger.error("claude salió con código %s: %s", proc.returncode, proc.stderr[-2000:])
        return ClaudeTurnResult(ok=False, text=f"Error ejecutando Claude:\n{proc.stderr[-1500:]}", raw=proc.stdout)

    return _parse_output(proc.stdout)


def _parse_output(stdout: str) -> ClaudeTurnResult:
    try:
        data = json.loads(stdout)
        text = data.get("result") or data.get("text") or stdout
        return ClaudeTurnResult(ok=True, text=text, raw=stdout)
    except json.JSONDecodeError:
        return ClaudeTurnResult(ok=True, text=stdout.strip(), raw=stdout)
