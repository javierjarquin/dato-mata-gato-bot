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

from __future__ import annotations

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
# Lo mismo con la IA gratis: cada intento es una llamada suelta, sin costo de Claude.
INTENTOS_GRATIS = 3
# Si tras limpiar lo inventado queda menos de esto con escena de verdad, no
# sirve: se le piden a Claude.
MINIMO_UTIL = 0.8


def activas() -> bool:
    """ESCENAS_3D (default 1): 0 deja el canal con el render plus de antes."""
    return (os.getenv("ESCENAS_3D") or "1").strip() != "0"


MOTORES = ("claude", "gratis", "claude_herramientas")


def motor() -> str:
    """Quién escribe las escenas (ESCENAS_MOTOR, 12/11/2026):
    - "claude" (default): Claude contesta el JSON directo, sin herramientas ni el
      system prompt de Claude Code; la revisión la corre este código.
    - "gratis": Gemini y sus respaldos, y Claude si no sirven. Pasan la revisión
      pero se ven más pobres (analisis/escenas_gratis en clip_assistance).
    - "claude_herramientas": lo del 11/11, Claude escribe el archivo y corre la
      revisión él mismo (~100k tokens por video)."""
    valor = (os.getenv("ESCENAS_MOTOR") or "claude").strip().lower()
    return valor if valor in MOTORES else "claude"


SISTEMA_JSON = ("Eres el director de arte de un canal de videos cortos en español. Contestas SOLO con el "
                "objeto JSON que se te pide, completo, sin texto antes ni después y sin ```.")


def _json_de(texto: str):
    """El objeto JSON de una respuesta, aunque venga con ``` o una línea de más."""
    texto = (texto or "").strip()
    try:
        return json.loads(texto)
    except ValueError:
        pass
    inicio, fin = texto.find("{"), texto.rfind("}")
    if inicio < 0 or fin <= inicio:
        return None
    try:
        return json.loads(texto[inicio:fin + 1])
    except ValueError:
        return None


def _cerrar(slug: str, guion: dict, plan: dict, problemas: list[str], quien: str, tokens: dict,
            sesion: str = "") -> Escenas | None:
    """Lo común al terminar: limpia lo que quedó mal, descarta si ya no sirve
    (None) y deja escenas.json."""
    from dato_mata_gato_bot import instruccion_escenas

    tirado: list[str] = []
    if problemas:
        plan, tirado = instruccion_escenas.limpiar(plan, guion)
    if instruccion_escenas.escenas_utiles(plan, guion) < MINIMO_UTIL:
        logger.warning("escenas de %s por %s: inservibles (%s)", slug, quien, "; ".join(problemas[:10]))
        return None
    ruta_plan(slug).write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    detalle = f"{instruccion_escenas.resumen_visual(plan)} · {quien}"
    if tirado:
        logger.warning("escenas de %s con %d descartes: %s", slug, len(tirado), "; ".join(tirado[:20]))
        detalle += f" · se descartaron {len(tirado)}: {'; '.join(tirado[:6])}"
    return Escenas(True, detalle, tokens, sesion)


def pedir_claude_json(slug: str, guion: dict, progreso=None) -> Escenas:
    """Claude sin herramientas: contesta el JSON y aquí se revisa. Las
    correcciones van en la misma sesión, solo con la lista de lo que falló."""
    from dato_mata_gato_bot import claude_runner, fabrica, instruccion_escenas

    sesion = str(uuid.uuid4())
    mensaje = instruccion_escenas.instruccion_json(slug, guion)
    plan, problemas, tokens = None, [], {}
    for intento in range(INTENTOS + 1):
        if progreso and intento:
            progreso(f"escenas 3D: corrigiendo ({intento}/{INTENTOS})")
        r = claude_runner.run_turn(sesion, mensaje, is_new_session=(intento == 0), ligera=True,
                                   herramientas="", sistema=SISTEMA_JSON)
        tokens = fabrica.tokens_de_sesiones([sesion])
        if not r.ok:
            # Sin cuota no sirve insistir: el video sale con el render de antes.
            return Escenas(False, r.text[:400], tokens, sesion)
        respuesta = _json_de(r.text)
        if isinstance(respuesta, dict):
            plan = respuesta
            problemas = instruccion_escenas.problemas(plan, guion)
        else:
            problemas = ['tu respuesta no fue UN objeto JSON {"ambiente": ..., "escenas": {...}}']
        if not problemas:
            break
        mensaje = ("La revisión de las escenas marcó esto. Corrígelo TODO y responde otra vez el JSON "
                   "COMPLETO (todas las escenas, no solo las corregidas):\n" + "\n".join(f"- {p}" for p in problemas))
    if plan is None:
        return Escenas(False, "; ".join(problemas)[:400], tokens, sesion)
    hechas = _cerrar(slug, guion, plan, problemas, "Claude sin herramientas", tokens, sesion)
    return hechas or Escenas(False, "no quedó ninguna escena utilizable", tokens, sesion)


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


def pedir_gratis(slug: str, guion: dict, progreso=None) -> Escenas | None:
    """Las escenas con la IA gratis (ia_gratis.pedir), revisadas con el mismo
    código que las de Claude. None = no contestó nadie o salió inservible, y
    quien llama se las pide a Claude."""
    from dato_mata_gato_bot import ia_gratis, instruccion_escenas

    base =instruccion_escenas.instruccion_json(slug, guion)
    prompt, plan, problemas = base, None, []
    ia_gratis.reiniciar_usados()
    for intento in range(INTENTOS_GRATIS + 1):
        if progreso and intento:
            progreso(f"escenas 3D (IA gratis): corrigiendo ({intento}/{INTENTOS_GRATIS})")
        try:
            # Sin Ollama: el modelo local de 7b no da para un prompt así.
            respuesta = ia_gratis.pedir(prompt, local=False)
        except ia_gratis.SinIA as exc:
            logger.warning("escenas de %s: la IA gratis no contestó (%s)", slug, str(exc)[:300])
            break
        if isinstance(respuesta, dict):
            plan = respuesta
            problemas = instruccion_escenas.problemas(plan, guion)
        else:
            problemas = ['la respuesta tiene que ser UN objeto JSON {"ambiente": ..., "escenas": {...}}']
        if not problemas:
            break
        prompt = instruccion_escenas.correccion_json(base, plan if plan is not None else respuesta, problemas)

    if plan is None:
        return None
    return _cerrar(slug, guion, plan, problemas, f"sin Claude ({', '.join(sorted(ia_gratis.usados())) or 'IA gratis'})", {})


def pedir(slug: str, progreso=None) -> Escenas:
    """Las escenas del video con el motor de ESCENAS_MOTOR (ver motor())."""
    from dato_mata_gato_bot import pipeline

    elegido = motor()
    if elegido == "claude_herramientas":
        return pedir_claude(slug, progreso)
    try:
        guion = json.loads((pipeline.ANDROID_IN / slug / "guion.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return Escenas(False, f"no se pudo leer el guion: {exc}")
    ruta_plan(slug).unlink(missing_ok=True)  # que no se cuele el de una corrida anterior
    if elegido == "gratis":
        if (hechas := pedir_gratis(slug, guion, progreso)) is not None:
            return hechas
        if progreso:
            progreso("escenas 3D: la IA gratis no sirvió, se las pido a Claude")
    return pedir_claude_json(slug, guion, progreso)


def pedir_claude(slug: str, progreso=None) -> Escenas:
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
        progreso("escenas 3D: pidiéndoselas a " + ("la IA gratis" if motor() == "gratis" else "Claude"))
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
