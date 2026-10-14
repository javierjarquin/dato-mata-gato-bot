"""Pone a Javier presentando el video desde la esquina, con los labios
sincronizados a la narración.

Es el paso extra del modo "vaca morada": el video sale del pipeline normal y
acá se le agrega el presentador encima. Son tres herramientas de
clip_assistance, en este orden:

    poc_avatar.py          MuseTalk mueve la boca de la placa según el audio
    poc_avatar_recorte.py  MediaPipe saca el fondo del cuarto
    poc_avatar_overlay.py  compone el recorte sobre el video final

Cuesta unos 35 MINUTOS por video: 32 de sincronizado de labios (26.5x
tiempo real, medido en la Radeon con DirectML sobre 72s de audio), 13
segundos de recorte y 18 de composición. Ese número depende de que el caché
de landmarks exista -- sin él son 17 minutos más, y fue lo que hizo creer al
principio que esto costaba dos horas y media.

Lo que hay que saber antes de tocar esto:

- **La placa es canónica y no se toca.** `assets/avatar/placa_25.mp4`, a 25
  fps porque es lo que MuseTalk espera; con una placa a 30 fps la boca deriva
  un 20% y no sincroniza. La detección de landmarks sobre esa placa tarda ~17
  min y queda cacheada en `salidas/_trabajo_musetalk/placa_25.pkl`. Si cambiás
  la placa (otro recorte, otra resolución, otros fps) ese caché deja de servir
  y se vuelve a pagar.
- **La salida va SIEMPRE a la misma carpeta**, no a la del proyecto. Es a
  propósito: poc_avatar.py deja el caché de landmarks junto a la salida, y si
  cambiara de carpeta por slug se recalcularía en cada video.
- **La GPU tiene que estar libre.** Con un juego abierto la inferencia muere
  con "not enough GPU video memory" -- pasó con Gears 5 llevándose 3.9 de los
  8 GB. El float16 da margen pero no hace milagros.
"""

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

CLIP_ASSISTANCE = Path(r"C:\clip_assistance")
CLIP_PY = CLIP_ASSISTANCE / ".venv" / "Scripts" / "python.exe"
HERRAMIENTAS = CLIP_ASSISTANCE / "tools"

AVATAR_DIR = Path(r"C:\illustrated-narrator\assets\avatar")
SALIDAS = AVATAR_DIR / "salidas"

# Los avatares disponibles, por número. El 0 es el que se usa cuando no se pide
# ninguno -- o sea, /vacamorada a secas. Agregar uno es dejar su placa acá (a
# 25 fps, ver más arriba) y sumar una entrada; el caché de landmarks se calcula
# solo la primera vez que se use.
PLACAS = {
    0: AVATAR_DIR / "placa_25.mp4",    # escritorio con monitores
    1: AVATAR_DIR / "placa1_25.mp4",   # estudio con micrófono de brazo
    2: AVATAR_DIR / "placa2_25.mp4",   # pared clara, micrófono de solapa
}
PLACA_POR_DEFECTO = 0


def placa_de(numero: int | None) -> Path:
    """La placa del avatar pedido. Sin número, la de siempre."""
    return PLACAS[PLACA_POR_DEFECTO if numero is None else numero]


def avatares_disponibles() -> list[int]:
    return sorted(n for n, p in PLACAS.items() if p.exists())

# 0.55 del ancho: lo eligió el usuario comparando 30/42/55 sobre un frame real.
# Más grande no tiene sentido -- el recorte útil de la placa mide 430 px de
# ancho, así que a partir de acá se empiezan a inventar píxeles.
ANCHO_REL = 0.55

# Con el presentador ocupando la esquina inferior, los subtítulos a la altura
# de siempre le pasan por encima. A 0.55 el avatar llega hasta 0.275 del alto.
SUBS_MARGEN = "0.32"


class AvatarError(RuntimeError):
    pass


def disponible(avatar: int | None = None) -> str:
    """Devuelve '' si se puede correr, o el motivo por el que no."""
    if not CLIP_PY.exists():
        return f"Falta el intérprete de clip_assistance en {CLIP_PY}"
    if avatar is not None and avatar not in PLACAS:
        opciones = ", ".join(str(n) for n in avatares_disponibles())
        return f"No existe el avatar {avatar}. Disponibles: {opciones}"
    placa = placa_de(avatar)
    if not placa.exists():
        return f"Falta la placa del presentador en {placa}"
    for nombre in ("poc_avatar.py", "poc_avatar_recorte.py", "poc_avatar_overlay.py"):
        if not (HERRAMIENTAS / nombre).exists():
            return f"Falta {nombre} en {HERRAMIENTAS}"
    unet = HERRAMIENTAS / "MuseTalk" / "models" / "musetalkV15" / "unet.pth"
    if not unet.exists():
        return f"Falta el modelo de MuseTalk en {unet}"
    return ""


def _correr(args: list[str], paso: str, timeout: int) -> str:
    logger.info("avatar/%s: %s", paso, " ".join(args))
    proc = subprocess.run(
        args, cwd=str(CLIP_ASSISTANCE), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout,
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
    )
    salida = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        # Al log completo antes de escalar: el mensaje que llega a Telegram va
        # recortado y después no queda forma de saber por qué falló.
        logger.error("avatar/%s falló:\n%s", paso, salida)
        raise AvatarError(f"{paso} falló:\n{salida[-1500:]}")
    return salida


def componer(final_mp4: Path, progreso=None, avatar: int | None = None) -> Path:
    """Agrega el presentador a `final_mp4`. Devuelve el video nuevo.

    No pisa el original: deja `final_sin_avatar.mp4` al lado. Si algo falla a
    mitad de camino, el video del pipeline sigue intacto y publicable.
    """
    def avisar(paso: str) -> None:
        logger.info("avatar: %s", paso)
        if progreso:
            progreso(paso)

    motivo = disponible(avatar)
    if motivo:
        raise AvatarError(motivo)
    if not final_mp4.exists():
        raise AvatarError(f"No existe {final_mp4}")

    placa = placa_de(avatar)
    SALIDAS.mkdir(parents=True, exist_ok=True)
    slug = final_mp4.parent.name
    # El número de avatar va en el nombre: dos corridas del mismo guion con
    # avatares distintos no se pisan, y se ve de cuál es cada archivo.
    etq = f"{slug}_av{PLACA_POR_DEFECTO if avatar is None else avatar}"
    audio = SALIDAS / f"{slug}_audio.wav"
    sincronizado = SALIDAS / f"{etq}_sync.mp4"
    mascara = SALIDAS / f"{etq}_mascara.mkv"
    destino = final_mp4.parent / "final_con_avatar.mp4"

    # 1. El audio sale del final.mp4, no de narracion.wav: el video ya tiene
    # silencios, tarjetas y desplazamientos que narracion.wav no refleja, y la
    # boca tiene que seguir lo que realmente se escucha.
    avisar("extrayendo el audio del video")
    _correr(["ffmpeg", "-y", "-v", "error", "-i", str(final_mp4),
             "-vn", "-ac", "1", "-ar", "16000", str(audio)],
            "extracción de audio", timeout=600)

    avisar(f"sincronizando labios con MuseTalk, avatar {avatar or 0} (~30 min)")
    _correr([str(CLIP_PY), str(HERRAMIENTAS / "poc_avatar.py"),
             "--placa", str(placa), "--audio", str(audio),
             "--out", str(sincronizado),
             "--dispositivo", "dml", "--fp16", "--batch-size", "1"],
            "MuseTalk", timeout=6 * 3600)

    # La máscara se calcula sobre la salida de MuseTalk y no sobre la placa: la
    # salida repite los fotogramas de la placa para cubrir el audio, y calcular
    # la máscara acá evita tener que reproducir ese mismo ciclado. Son 21
    # segundos, no vale la pena optimizarlo.
    avisar("recortando el fondo")
    _correr([str(CLIP_PY), str(HERRAMIENTAS / "poc_avatar_recorte.py"),
             "--avatar", str(sincronizado), "--out", str(mascara)],
            "recorte de fondo", timeout=1800)

    avisar("componiendo el presentador sobre el video")
    _correr([str(CLIP_PY), str(HERRAMIENTAS / "poc_avatar_overlay.py"),
             "--video", str(final_mp4), "--avatar", str(sincronizado),
             "--mascara", str(mascara), "--sin-ovalo",
             "--ancho", str(ANCHO_REL), "--pos", "abajo-derecha",
             "--out", str(destino)],
            "composición", timeout=1800)

    if not destino.exists():
        raise AvatarError("la composición terminó sin escribir el video")

    # El que se sube a Drive es final.mp4, así que el compuesto ocupa ese
    # nombre y el original queda guardado al lado por si hay que volver atrás.
    respaldo = final_mp4.parent / "final_sin_avatar.mp4"
    respaldo.unlink(missing_ok=True)
    final_mp4.rename(respaldo)
    destino.rename(final_mp4)
    logger.info("avatar: listo, original guardado en %s", respaldo)
    return final_mp4
