"""Invoca Claude Code CLI en modo no interactivo (--print), reusando una
sesión por chat de Telegram para que la conversación tenga memoria real."""

import json
import logging
import os
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
# Esfuerzo y modelo de la sesión ligera (20/10/2026). Medido en 7 días de
# fábrica: el 46 % del gasto era salida (27k tokens por guion) y ~3/4 de esa
# salida era razonamiento interno, con el esfuerzo por defecto. FABRICA_EFFORT
# vacío = el de siempre; FABRICA_MODELO (p. ej. "sonnet") para el A/B de modelo.
EFFORT_ESCRITURA = (os.getenv("FABRICA_EFFORT") or "medium").strip()
MODELO_ESCRITURA = (os.getenv("FABRICA_MODELO") or "").strip()


def carpeta_de_sesiones(cwd: str = CWD):
    """Donde Claude Code guarda el historial (.jsonl) de las sesiones de `cwd`."""
    from pathlib import Path
    return Path.home() / ".claude" / "projects" / cwd.replace(":", "-").replace("\\", "-").replace("_", "-")


def run_turn(session_id: str, message: str, is_new_session: bool, ligera: bool = False,
             recortada: bool = False) -> ClaudeTurnResult:
    # El prompt va por STDIN, no como argumento (16/10/2026). Windows corta la
    # línea de comandos en 32 767 caracteres y CreateProcess falla con
    # "WinError 206: el nombre del archivo o la extensión es demasiado largo".
    # El lote viral del 16/10 se topó ahí: 34 454 caracteres (24 604 de
    # instrucción + 9 851 de la lista de guiones ya hechos, que crece con cada
    # video). Reventaba ANTES de arrancar Claude, así que no quedaba sesión en
    # disco ni mensaje de error: 17 ciclos seguidos sin escribir un solo guion.
    args = [
        CLAUDE_EXE,
        "-p",
        "--output-format", "json",
        "--permission-mode", "bypassPermissions",
    ]
    for d in ADD_DIRS:
        args += ["--add-dir", d]
    if ligera:
        args += ["--tools", HERRAMIENTAS_LIGERAS, "--strict-mcp-config"]
        if EFFORT_ESCRITURA:
            args += ["--effort", EFFORT_ESCRITURA]
        if MODELO_ESCRITURA:
            args += ["--model", MODELO_ESCRITURA]
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
            args, cwd=cwd, input=message, capture_output=True, text=True, encoding="utf-8",
            timeout=SUBPROCESS_TIMEOUT_SECONDS,
            # Sin memoria automática en la sesión ligera (29/10/2026): leer y
            # escribir sus .md era el 10 % del gasto de la fábrica. Lo que
            # aprende un guion va al código o a la instrucción, no ahí.
            # PYTHONWARNINGS: el FutureWarning de google.api_core (~400 letras)
            # salía al inicio de cada revisar/fotos/buscar y Claude lo releía en
            # todos los pasos que seguían (auditoría del 29/10/2026).
            env={**os.environ, "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
                 "PYTHONWARNINGS": "ignore::FutureWarning"} if ligera else None,
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
        # Claude puede salir con código 0 y traer el error DENTRO del JSON
        # (is_error). Sin mirarlo, el lote tomaba eso por un turno bueno, no
        # encontraba guiones y seguía como si nada: otro fallo mudo.
        if data.get("is_error"):
            return ClaudeTurnResult(ok=False, text=f"Claude devolvió un error: {text}", raw=stdout)
        return ClaudeTurnResult(ok=True, text=text, raw=stdout)
    except json.JSONDecodeError:
        return ClaudeTurnResult(ok=True, text=stdout.strip(), raw=stdout)
