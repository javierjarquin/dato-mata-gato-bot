"""El paso de escenas 3D de un video (11/11/2026).

Después de escribir el guion y de generar la voz, la fábrica le pide a Claude
QUÉ SE VE en cada plano (instruccion_escenas) y renderiza esas escenas con
illustrated-narrator/tradiciones_3d en lugar del formato "noticia" del render
plus. La voz, los subtítulos, la portada, el gato escondido y el aviso de
Telegram siguen igual.

Nunca tumba un video: si Claude no contesta, si el archivo no sirve o si el
render falla, se vuelve solo al render plus de siempre.

Se apaga de dos formas:
- ESCENAS_3D=0 en el .env: todo el canal vuelve al render de antes.
- "plus": {"sin_escenas": true} en un guion: ese video, nada más.
"""

import json
import logging
import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

TRADICIONES_DIR = Path(r"C:\illustrated-narrator\tradiciones_3d")
# El render son ~1.1x lo que dura el video; el tope deja aire para un arranque lento.
TIMEOUT_RENDER = 30 * 60
# Cuántas veces se le pide a Claude que corrija lo que la revisión marcó. Dos:
# con tradiciones, lo que no se arregla en la segunda no se arregla en la quinta.
INTENTOS = 2


def activas() -> bool:
    """ESCENAS_3D (default 1): 0 deja el canal con el render plus de antes."""
    return (os.getenv("ESCENAS_3D") or "1").strip() != "0"


def usa_escenas(slug: str) -> bool:
    """¿Este video va con escenas 3D? Solo los que hoy usan el render plus; el
    nicho de tradiciones tiene su propio 3D y no pasa por aquí."""
    from dato_mata_gato_bot import pipeline

    if not activas() or pipeline.es_tradicion(slug):
        return False
    try:
        guion = json.loads((pipeline.ANDROID_IN / slug / "guion.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return not (guion.get("plus") or {}).get("sin_escenas")


@dataclass
class Escenas:
    ok: bool
    detalle: str
    tokens: dict = field(default_factory=dict)
    sesion: str = ""


def ruta_plan(slug: str) -> Path:
    from dato_mata_gato_bot import pipeline

    return pipeline.ANDROID_IN / slug / "escenas.json"


def _leer(ruta: Path) -> dict | None:
    try:
        plan = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return plan if isinstance(plan, dict) else None


def pedir(slug: str, progreso=None) -> Escenas:
    """Le pide a Claude las escenas del video y deja escenas.json listo.

    Claude escribe el archivo y corre él mismo la revisión; aquí se vuelve a
    revisar (no vaya a ser que haya respondido sin correrla) y, si queda algo
    mal, se le devuelve la lista. Lo que siga sin existir en el catálogo se
    descarta con instruccion_escenas.limpiar antes de renderizar.
    """
    from dato_mata_gato_bot import claude_runner, fabrica, instruccion_escenas, pipeline

    ruta = ruta_plan(slug)
    try:
        guion = json.loads((pipeline.ANDROID_IN / slug / "guion.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return Escenas(False, f"no se pudo leer el guion: {exc}")

    sesion = str(uuid.uuid4())
    ruta.unlink(missing_ok=True)  # que no se cuele el de una corrida anterior
    mensaje = instruccion_escenas.instruccion(slug, guion)
    problemas: list[str] = []
    for intento in range(INTENTOS + 1):
        if progreso and intento:
            progreso(f"escenas 3D: corrigiendo ({intento}/{INTENTOS})")
        r = claude_runner.run_turn(sesion, mensaje, is_new_session=(intento == 0), ligera=True)
        tokens = fabrica.tokens_de_sesiones([sesion])
        if not r.ok:
            # Sin cuota no sirve insistir: el video sale con el render de antes.
            return Escenas(False, r.text[:400], tokens, sesion)
        plan = _leer(ruta)
        if plan is None:
            problemas = [f"no escribiste {ruta}"]
        else:
            problemas = instruccion_escenas.problemas(plan, guion)
        if not problemas:
            return Escenas(True, instruccion_escenas.resumen_visual(plan), tokens, sesion)
        mensaje = ("La revisión de las escenas marcó esto. Corrígelo TODO de una vez, con Edit y todos "
                   "los Edit en la MISMA respuesta:\n" + "\n".join(f"- {p}" for p in problemas))

    # Se acabaron los intentos: se usa lo que sí existe y se anota lo que se tiró.
    plan = _leer(ruta)
    tokens = fabrica.tokens_de_sesiones([sesion])
    if plan is None:
        return Escenas(False, "; ".join(problemas)[:400], tokens, sesion)
    limpio, tirado = instruccion_escenas.limpiar(plan, guion)
    if not limpio.get("escenas"):
        return Escenas(False, "no quedó ninguna escena utilizable", tokens, sesion)
    ruta.write_text(json.dumps(limpio, ensure_ascii=False, indent=1), encoding="utf-8")
    logger.warning("escenas de %s con %d descartes: %s", slug, len(tirado), "; ".join(tirado[:20]))
    detalle = instruccion_escenas.resumen_visual(limpio)
    if tirado:
        detalle += f" · se descartaron {len(tirado)}: {'; '.join(tirado[:6])}"
    return Escenas(True, detalle, tokens, sesion)


def render(slug: str) -> tuple[bool, str]:
    """Renderiza las escenas y, si sale bien, las deja como final.mp4.

    Igual que pipeline.render_remotion: el final de FFmpeg se guarda como
    final_ffmpeg.mp4, así que si esto falla el video de siempre sigue ahí.
    """
    from dato_mata_gato_bot import pipeline

    salida = TRADICIONES_DIR / "out" / f"{slug}.mp4"
    salida.unlink(missing_ok=True)
    try:
        proc = subprocess.run(
            [pipeline.NARRATOR_PY, str(TRADICIONES_DIR / "scripts" / "escenas.py"), slug],
            cwd=TRADICIONES_DIR, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=TIMEOUT_RENDER, env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        return False, f"el render de escenas se pasó de {TIMEOUT_RENDER // 60} min"
    finally:
        shutil.rmtree(TRADICIONES_DIR / "public" / slug, ignore_errors=True)
    if proc.returncode != 0 or not salida.exists() or salida.stat().st_size < 100_000:
        logger.error("render de escenas falló para %s:\n%s\n%s", slug, proc.stdout[-3000:], proc.stderr[-3000:])
        salida.unlink(missing_ok=True)
        return False, (proc.stderr or proc.stdout)[-1500:]
    proyecto = pipeline.NARRATOR_PROJECTS / slug
    final = proyecto / "final.mp4"
    if final.exists():
        respaldo = proyecto / "final_ffmpeg.mp4"
        respaldo.unlink(missing_ok=True)
        final.rename(respaldo)
    shutil.move(str(salida), str(final))
    detalle = next((ln for ln in proc.stdout.splitlines() if ln.startswith("escenas: ")), "")
    return True, detalle


def generar(slug: str, progreso=None) -> tuple[bool, str]:
    """El paso completo: pedir las escenas, renderizarlas y pegar la portada.

    Devuelve (ok, aviso). Con ok=False el pipeline se va al render de siempre.
    """
    from dato_mata_gato_bot import pipeline

    if progreso:
        progreso("escenas 3D: pidiéndoselas a Claude")
    hechas = pedir(slug, progreso)
    gasto = hechas.tokens.get("total", 0)
    costo = f" · {gasto / 1000:.0f}k tokens" if gasto else ""
    if not hechas.ok:
        return False, f"escenas 3D: {hechas.detalle}{costo}"
    if progreso:
        progreso("render de escenas 3D")
    ok, detalle = render(slug)
    if not ok:
        return False, f"escenas 3D: el render falló ({detalle[-200:]}){costo}"
    if progreso:
        progreso("portada")
    portada = pipeline._portadas(slug, pipeline.NARRATOR_PROJECTS / slug / "final.mp4")
    return True, "; ".join(x for x in (f"render: escenas 3D{costo}", hechas.detalle, detalle, portada) if x)
