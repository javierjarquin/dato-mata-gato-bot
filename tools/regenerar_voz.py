"""Regenera con la voz clonada (VoiceStudio) los videos que salieron con Kokoro.

Los videos de crimen se generaron ANTES del cambio de motor de TTS del
08/09/2026, asi que llevan la voz vieja. Este script, por cada slug:

    1. Vuelve a sintetizar la narracion con el motor actual.
    2. Rearma narracion.wav en el proyecto del narrador (logo, cierre,
       tarjetas y silencios incluidos) reusando `_setup_narrator_project`.
    3. BORRA transcript.json y planos_alineados.json.
    4. Corre `narrator generate`.

El paso 3 es el que no se puede saltear: la voz nueva no dura lo mismo que la
vieja, y si queda la alineacion anterior el narrador la da por buena
(`already_aligned`) y monta el video con los tiempos viejos sobre el audio
nuevo. El resultado no falla -- sale desincronizado de punta a punta.

Las imagenes y los medios NO se vuelven a buscar: siguen cacheados en el
proyecto, y esto solo rehace audio, alineacion, clips y ensamblado.

    python tools/regenerar_voz.py --listar
    python tools/regenerar_voz.py --todos
    python tools/regenerar_voz.py --slug guion-halconazo

Es reanudable: un slug cuyo narracion.wav ya sea posterior al cambio de motor
se saltea, asi que se puede cortar y volver a lanzar sin repetir trabajo.
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# La consola de Windows es cp1252 y la salida de los subprocesos trae acentos y
# caracteres de reemplazo: sin esto, un print del mensaje de error mata el lote
# ENTERO por UnicodeEncodeError, y encima tapa el error original.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv  # noqa: E402

# ANTES de importar pipeline, como en bot.py y upload_cli.py: sin esto no hay
# VOICESTUDIO_VOICE_ID y tts-kokoro corta en el primer slug ("Falta la voz para
# el motor 'voicestudio'").
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from dato_mata_gato_bot import pipeline  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
SCHEDULE = RAIZ / "data" / "publish_schedule.json"

# Momento en que el bot paso a VoiceStudio (commit 779cd02). Un narracion.wav
# anterior a esto lleva la voz de Kokoro.
CORTE = datetime(2026, 9, 8, 20, 11).timestamp()

# Voz de Kokoro: se ignora con VoiceStudio (usa VOICESTUDIO_VOICE_ID), pero
# _generate_audio la pide igual.
VOZ_KOKORO = "am_adam"


def _log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def _slugs_de_crimen() -> list[str]:
    datos = json.loads(SCHEDULE.read_text(encoding="utf-8"))

    def orden(slug: str) -> str:
        f = datos[slug].get("fecha", "")
        return f[4:] + f[2:4] + f[:2] if len(f) == 8 else f

    return sorted((s for s in datos if s.startswith("guion-")), key=orden)


def _wav(slug: str) -> Path:
    return pipeline.NARRATOR_PROJECTS / slug / "narracion.wav"


def _duracion(ruta: Path) -> float:
    try:
        return float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(ruta)],
            capture_output=True, text=True, timeout=60,
        ).stdout.strip())
    except Exception:  # noqa: BLE001 -- informativo
        return 0.0


def ya_tiene_voz_nueva(slug: str) -> bool:
    wav = _wav(slug)
    return wav.exists() and wav.stat().st_mtime >= CORTE


def regenerar(slug: str) -> tuple[bool, str]:
    proyecto = pipeline.NARRATOR_PROJECTS / slug
    if not proyecto.exists():
        return False, f"no existe el proyecto {proyecto}"

    antes = _duracion(_wav(slug))
    _log(f"{slug}: sintetizando ({pipeline.motor_tts()}), narracion vieja {antes:.0f}s")
    inicio = time.time()
    ok, salida = pipeline._generate_audio(slug, VOZ_KOKORO)
    if not ok:
        return False, salida
    _log(f"{slug}: audio listo en {(time.time() - inicio) / 60:.0f} min")

    try:
        pipeline._setup_narrator_project(slug)
    except Exception as exc:  # noqa: BLE001
        return False, f"setup del proyecto fallo: {exc}"

    # La voz nueva no dura lo mismo: sin borrar esto, el narrador reusa la
    # alineacion vieja y el video sale desincronizado sin dar ningun error.
    for nombre in ("transcript.json", "planos_alineados.json", "visemas.json"):
        (proyecto / nombre).unlink(missing_ok=True)

    despues = _duracion(_wav(slug))
    _log(f"{slug}: narracion nueva {despues:.0f}s ({despues - antes:+.0f}s); generando video")
    ok, salida = pipeline._run_narrator_generate(slug)
    if not ok:
        return False, salida

    final = proyecto / "final.mp4"
    if not final.exists() or _duracion(final) <= 0:
        return False, f"narrator termino sin error pero {final} no es un video valido"
    return True, f"{_duracion(final):.0f}s"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slug", action="append", help="uno o varios slugs concretos")
    ap.add_argument("--todos", action="store_true", help="todos los de crimen del schedule")
    ap.add_argument("--listar", action="store_true", help="solo muestra que se haria")
    ap.add_argument("--rehacer", action="store_true",
                    help="rehace tambien los que ya tienen la voz nueva")
    args = ap.parse_args()

    slugs = args.slug or (_slugs_de_crimen() if (args.todos or args.listar) else [])
    if not slugs:
        ap.error("elegí --slug, --todos o --listar")

    pendientes = [s for s in slugs if args.rehacer or not ya_tiene_voz_nueva(s)]

    if args.listar:
        total = 0.0
        for s in slugs:
            dur = _duracion(_wav(s))
            total += dur if s in pendientes else 0.0
            estado = "PENDIENTE" if s in pendientes else "ya con voz nueva"
            print(f"  {s:<42} {dur:6.0f}s  {estado}")
        # VoiceStudio sintetiza a ~13x el largo del audio en esta maquina.
        print(f"\n{len(pendientes)} pendientes, {total / 60:.0f} min de narracion")
        print(f"solo el TTS son ~{total * 13 / 3600:.1f} h; mas el render de cada video")
        return 0

    _log(f"motor: {pipeline.motor_tts()}  |  {len(pendientes)} de {len(slugs)} por regenerar")
    fallos = []
    for i, slug in enumerate(pendientes, 1):
        _log(f"--- {i}/{len(pendientes)}  {slug} ---")
        try:
            ok, detalle = regenerar(slug)
        except Exception as exc:  # noqa: BLE001 -- un slug roto no corta el lote
            ok, detalle = False, repr(exc)
        if ok:
            _log(f"{slug}: LISTO ({detalle})")
        else:
            fallos.append(slug)
            _log(f"{slug}: FALLO -- {detalle[-800:]}")

    _log(f"terminado: {len(pendientes) - len(fallos)} ok, {len(fallos)} con fallo")
    if fallos:
        print("fallaron:", ", ".join(fallos))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
