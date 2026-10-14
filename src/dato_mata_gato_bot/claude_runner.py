"""Invoca Claude Code CLI en modo no interactivo (--print), reusando una
sesión por chat de Telegram para que la conversación tenga memoria real."""

import json
import logging
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)

CLAUDE_EXE = "claude"
CWD = r"C:\illustrated-narrator"
ADD_DIRS = [r"C:\tts-kokoro", r"C:\Android_in", r"C:\dato-mata-gato-bot"]

# Subido de 1h a 20h a pedido explícito del usuario (25/08/2026): /nuevolote
# le pide a Claude escribir varios guiones investigados de una sola vez (no
# es solo generar un video, ~10-20 min), y una escalada real puede implicar
# varias corridas de narrator generate en foreground para resolver un caso
# difícil -- 1h resultaba corto para eso. No es la causa del corte real de
# /generarlote del 25/08 (ese fue un ReadTimeout de la API de Telegram al
# avisar progreso, no de este subproceso -- ver cmd_generarlote/_safe_reply
# en bot.py), pero igual se sube por las dudas.
SUBPROCESS_TIMEOUT_SECONDS = 60 * 60 * 20


@dataclass
class ClaudeTurnResult:
    ok: bool
    text: str
    raw: str


# Sesión ligera para escribir guiones (13/10/2026). Desde C:\illustrated-narrator
# cada paso de Claude cargaba ~40k tokens fijos (el CLAUDE.md del narrador, de
# 33 KB, todas las herramientas y los conectores MCP), y un guion da ~20 pasos.
# Desde una carpeta vacía, con solo las herramientas que usa y sin MCP: ~7k.
CWD_LIGERO = r"C:\Android_in\fabrica\_escritura"
HERRAMIENTAS_LIGERAS = "WebSearch,WebFetch,Write,Read,Edit,Bash"
# Sesión recortada (13/10/2026) para los guiones de crimen y mitos del bot:
# misma carpeta (su instrucción se apoya en el CLAUDE.md del narrador para el
# formato del guion), pero sin conectores MCP ni herramientas que no usa.
# Medido: 39.9k -> 24.4k tokens fijos por paso.
HERRAMIENTAS_RECORTADAS = "WebSearch,WebFetch,Write,Read,Edit,Bash,Glob,Grep"


def carpeta_de_sesiones(cwd: str = CWD):
    """Donde Claude Code guarda el historial (.jsonl) de las sesiones de `cwd`."""
    from pathlib import Path
    return Path.home() / ".claude" / "projects" / cwd.replace(":", "-").replace("\\", "-").replace("_", "-")


def run_turn(session_id: str, message: str, is_new_session: bool, ligera: bool = False,
             recortada: bool = False) -> ClaudeTurnResult:
    args = [
        CLAUDE_EXE,
        "-p", message,
        "--output-format", "json",
        "--permission-mode", "bypassPermissions",
    ]
    for d in ADD_DIRS:
        args += ["--add-dir", d]
    if ligera:
        args += ["--tools", HERRAMIENTAS_LIGERAS, "--strict-mcp-config"]
    elif recortada:
        args += ["--tools", HERRAMIENTAS_RECORTADAS, "--strict-mcp-config"]
    args += (["--session-id", session_id] if is_new_session else ["--resume", session_id])
    cwd = CWD_LIGERO if ligera else CWD
    if ligera:
        from pathlib import Path
        Path(cwd).mkdir(parents=True, exist_ok=True)

    logger.info("Invocando claude (nueva=%s, ligera=%s, session=%s)", is_new_session, ligera, session_id)
    try:
        proc = subprocess.run(
            args, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
            timeout=SUBPROCESS_TIMEOUT_SECONDS,
            # claude.exe es una app de consola; sin esto, al lanzarla desde
            # pythonw.exe (sin consola) Windows le abre una ventana visible
            # que el usuario puede cerrar por error y matar la generación.
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except subprocess.TimeoutExpired:
        return ClaudeTurnResult(ok=False, text="Se agotó el tiempo de espera (60 min).", raw="")

    if proc.returncode != 0:
        # El motivo viene en stdout, no en stderr: con la cuota agotada Claude
        # sale con código 1, stderr VACÍO, y en el JSON de stdout dice "You've
        # hit your session limit · resets 3:40pm". El 26/09/2026 un lote se
        # cortó así y el usuario solo vio "Error ejecutando Claude:".
        motivo = _motivo_del_error(proc.stdout) or proc.stderr[-1500:].strip()
        logger.error("claude salió con código %s: %s", proc.returncode, motivo[:2000])
        return ClaudeTurnResult(ok=False, text=f"Error ejecutando Claude: {motivo}", raw=proc.stdout)

    return _parse_output(proc.stdout)


def _motivo_del_error(stdout: str) -> str:
    try:
        data = json.loads(stdout)
    except (json.JSONDecodeError, TypeError):
        return (stdout or "").strip()[-500:]
    return str(data.get("result") or data.get("error") or "").strip()


def es_limite_de_uso(texto: str) -> bool:
    """¿El error es que se acabó la cuota de Claude? Ahí no sirve reintentar:
    hay que esperar a la hora que dice el mensaje."""
    t = (texto or "").lower()
    return "limit" in t and ("hit your" in t or "resets" in t or "usage" in t)


def tamano_sesion(session_id: str) -> int:
    """Bytes del historial guardado de una sesión (0 si no existe).

    Sirve para no reusar una conversación gigante: cada paso de Claude vuelve
    a leer el historial entero. La del chat del bot llegó a 16 MB (unos 900.000
    tokens de contexto), y escribir 13 guiones costó 34 millones de tokens.
    """
    from pathlib import Path
    carpeta = Path.home() / ".claude" / "projects" / CWD.replace(":", "-").replace("\\", "-")
    ruta = carpeta / f"{session_id}.jsonl"
    try:
        return ruta.stat().st_size
    except OSError:
        return 0


def _parse_output(stdout: str) -> ClaudeTurnResult:
    try:
        data = json.loads(stdout)
        text = data.get("result") or data.get("text") or stdout
        return ClaudeTurnResult(ok=True, text=text, raw=stdout)
    except json.JSONDecodeError:
        return ClaudeTurnResult(ok=True, text=stdout.strip(), raw=stdout)
