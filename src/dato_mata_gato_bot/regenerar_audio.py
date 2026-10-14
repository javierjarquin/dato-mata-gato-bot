"""Rehace el audio de un video con el motor y la voz del canal.

    python -m dato_mata_gato_bot.regenerar_audio <slug>

Existe para que una escalación a Claude NUNCA tenga que generar el audio a
mano. El 14/09/2026 pasó: el contenedor de VoiceStudio estaba caído, el paso
de audio falló, y al resolverlo se sintetizó sin el profile de la voz clonada
-- cada plano salió con una voz distinta, de 95 a 210 Hz. Más de una octava de
diferencia dentro del mismo video.

Reusa `_generate_audio` y `_setup_narrator_project` del pipeline, así que el
motor, la voz y el rearmado de narracion.wav (silencios y tarjetas incluidos)
son exactamente los del lote normal.
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

# Antes de importar pipeline: sus constantes de entorno se leen al importar.
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from dato_mata_gato_bot import pipeline, sessions  # noqa: E402

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def regenerar(slug: str, voz: str | None = None) -> int:
    falta = pipeline.motor_tts_listo()
    if falta:
        print(f"FALLÓ: {falta}")
        return 1

    # Con VoiceStudio la voz sale de VOICESTUDIO_VOICE_ID y este nombre se
    # ignora; solo importa cuando el motor es Kokoro.
    voz = voz or sessions.DEFAULT_VOICE
    print(f"Motor: {pipeline.motor_tts()}  |  slug: {slug}")

    ok, salida = pipeline._generate_audio(slug, voz)
    if not ok:
        print(f"FALLÓ la síntesis:\n{salida[-2000:]}")
        return 1

    try:
        pipeline._setup_narrator_project(slug)
    except Exception as exc:  # noqa: BLE001 -- el mensaje es para quien corre esto
        print(f"FALLÓ el rearmado del proyecto: {exc}")
        return 1

    wav = pipeline.NARRATOR_PROJECTS / slug / "narracion.wav"
    proyecto = pipeline.NARRATOR_PROJECTS / slug
    # La alineación vieja no sirve: el audio nuevo no dura lo mismo, y el
    # narrador la daría por buena (already_aligned) montando el video con los
    # tiempos anteriores sobre la voz nueva, sin error alguno.
    for nombre in ("transcript.json", "planos_alineados.json", "visemas.json"):
        (proyecto / nombre).unlink(missing_ok=True)

    print(f"LISTO: {wav} ({wav.stat().st_size / 1e6:.1f} MB)")
    print("Alineación borrada: el próximo narrator generate la rehace sobre el audio nuevo.")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    return regenerar(sys.argv[1])


if __name__ == "__main__":
    sys.exit(main())
