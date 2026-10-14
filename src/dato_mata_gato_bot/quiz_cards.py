"""Tarjetas visuales para el formato de preguntas.

Los guiones de trivia no necesitan fotos documentales: necesitan la pregunta
grande en pantalla y después la respuesta. Buscar eso en Pexels/Wikimedia
cae justo en el patrón que ya sabemos que falla (consultas genéricas que
ninguna búsqueda real satisface, y que terminan escalando a Claude).

En vez de eso se generan las tarjetas acá y se dejan como
`media/<plano_id>/elegido.png` en el proyecto de illustrated-narrator.
`research_plano_media._manual_override` las detecta ANTES de buscar y saltea
la búsqueda por completo -- el mismo mecanismo probado del logo y el cierre.

Paleta tomada del sitio del canal (dato-mata-gato-site/estilo.css).
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ANCHO, ALTO = 1080, 1920

FONDO = (13, 13, 18)
FONDO_CLARO = (22, 22, 29)
TEXTO = (232, 230, 224)
ACENTO = (212, 180, 131)
BORDE = (42, 42, 52)

MARGEN = 90

# Secciones que llevan tarjeta generada. El resto de los planos (identidad,
# cierre) siguen el camino normal.
SECCIONES_PREGUNTA = {"pregunta"}
SECCIONES_RESPUESTA = {"respuesta"}


def _fuente(tam: int, negrita: bool = False):
    from PIL import ImageFont

    nombres = ("segoeuib.ttf", "arialbd.ttf") if negrita else ("segoeui.ttf", "arial.ttf")
    for nombre in nombres:
        try:
            return ImageFont.truetype(nombre, tam)
        except OSError:
            continue
    return ImageFont.load_default(size=tam)


def _envolver(draw, texto: str, fuente, ancho_max: int) -> list[str]:
    """Corta el texto en líneas midiendo el ancho REAL de cada una.

    Estimar los caracteres por línea a partir del ancho de una 'M' subestima
    cuántos entran (la 'M' es de las más anchas), y textwrap terminaba
    partiendo palabras al medio: se vio "3 PREGUNT / AS." en una tarjeta
    real. Midiendo con textlength las palabras nunca se cortan.
    """
    palabras = texto.split()
    if not palabras:
        return [""]

    lineas: list[str] = []
    actual = palabras[0]
    for palabra in palabras[1:]:
        tentativa = f"{actual} {palabra}"
        if draw.textlength(tentativa, font=fuente) <= ancho_max:
            actual = tentativa
        else:
            lineas.append(actual)
            actual = palabra
    lineas.append(actual)
    return lineas


def _texto_centrado(draw, texto: str, y: int, fuente, color, ancho_max: int) -> int:
    """Dibuja texto envuelto y centrado. Devuelve la Y donde terminó."""
    lineas = _envolver(draw, texto, fuente, ancho_max)
    alto_linea = int(fuente.size * 1.35)
    for i, linea in enumerate(lineas):
        ancho = draw.textlength(linea, font=fuente)
        draw.text(((ANCHO - ancho) / 2, y + i * alto_linea), linea, font=fuente, fill=color)
    return y + len(lineas) * alto_linea


def _lienzo():
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (ANCHO, ALTO), FONDO)
    draw = ImageDraw.Draw(img)
    # Panel central sutil, para que el texto no flote sobre negro plano.
    draw.rounded_rectangle(
        [(MARGEN - 30, ALTO * 0.22), (ANCHO - MARGEN + 30, ALTO * 0.78)],
        radius=40, fill=FONDO_CLARO, outline=BORDE, width=2,
    )
    return img, draw


def _ajustar(draw, texto: str, tam_inicial: int, ancho_max: int, alto_max: int) -> int:
    """Baja el tamaño de fuente hasta que el texto entre en el alto dado.
    Sin esto, una pregunta larga se sale de la tarjeta."""
    tam = tam_inicial
    while tam > 34:
        fuente = _fuente(tam, negrita=True)
        lineas = _envolver(draw, texto, fuente, ancho_max)
        # Además del alto, ninguna línea puede pasarse de ancho: con una
        # palabra muy larga (sin espacios donde cortar) hay que bajar el
        # tamaño aunque el alto entre.
        cabe_alto = len(lineas) * int(fuente.size * 1.35) <= alto_max
        cabe_ancho = all(draw.textlength(l, font=fuente) <= ancho_max for l in lineas)
        if cabe_alto and cabe_ancho:
            return tam
        tam -= 6
    return tam


def tarjeta_pregunta(texto: str, numero: int | None, destino: Path) -> Path:
    img, draw = _lienzo()
    ancho_max = ANCHO - MARGEN * 2

    if numero is not None:
        etiqueta = f"PREGUNTA {numero}"
        f_et = _fuente(46, negrita=True)
        ancho = draw.textlength(etiqueta, font=f_et)
        draw.text(((ANCHO - ancho) / 2, ALTO * 0.27), etiqueta, font=f_et, fill=ACENTO)

    tam = _ajustar(draw, texto, 92, ancho_max, int(ALTO * 0.34))
    _texto_centrado(draw, texto, int(ALTO * 0.38), _fuente(tam, negrita=True), TEXTO, ancho_max)

    destino.parent.mkdir(parents=True, exist_ok=True)
    img.save(destino, "PNG")
    return destino


def tarjeta_respuesta(texto: str, destino: Path) -> Path:
    img, draw = _lienzo()
    ancho_max = ANCHO - MARGEN * 2

    etiqueta = "RESPUESTA"
    f_et = _fuente(46, negrita=True)
    ancho = draw.textlength(etiqueta, font=f_et)
    draw.text(((ANCHO - ancho) / 2, ALTO * 0.27), etiqueta, font=f_et, fill=ACENTO)

    tam = _ajustar(draw, texto, 100, ancho_max, int(ALTO * 0.34))
    _texto_centrado(draw, texto, int(ALTO * 0.38), _fuente(tam, negrita=True), ACENTO, ancho_max)

    destino.parent.mkdir(parents=True, exist_ok=True)
    img.save(destino, "PNG")
    return destino


def tarjeta_simple(texto: str, destino: Path) -> Path:
    """Tarjeta sin etiqueta: para el gancho inicial y el cierre que invita a
    comentar."""
    img, draw = _lienzo()
    ancho_max = ANCHO - MARGEN * 2
    tam = _ajustar(draw, texto, 96, ancho_max, int(ALTO * 0.40))
    _texto_centrado(draw, texto, int(ALTO * 0.35), _fuente(tam, negrita=True), TEXTO, ancho_max)
    destino.parent.mkdir(parents=True, exist_ok=True)
    img.save(destino, "PNG")
    return destino


def escribir_alineacion_exacta(guion: dict, wav_dir: Path, dest_dir: Path) -> int:
    """Escribe `planos_alineados.json` con los tiempos calculados a partir de
    la duración real de cada WAV, y devuelve cuántos planos escribió.

    Por qué no se usa el alineador normal: ese transcribe el audio completo
    con Whisper y busca cada plano por coincidencia de palabras. Con
    silencios largos entre planos, Whisper directamente SE SALTEA tramos --
    confirmado en una corrida real de trivia: la tercera respuesta ("El
    murciélago...") desapareció del transcript y su plano quedó sin alinear,
    así que no se renderizó y la respuesta no salía en el video. El mismo
    audio, aislado, Whisper lo transcribe perfecto: el problema es el
    archivo largo con silencios.

    Acá no hace falta adivinar nada: el audio se genera plano por plano, así
    que las posiciones se conocen con exactitud. `load_planos_state` las lee
    y `generate_narration_video` saltea la transcripción y la alineación
    (`already_aligned`), lo que además ahorra el paso más lento del pipeline.
    """
    import wave

    filas = []
    cursor = 0.0
    for plano in guion.get("planos", []):
        wav = wav_dir / f"{plano['id']}.wav"
        if not wav.exists():
            logger.warning("Falta %s; no se puede alinear exacto", wav)
            return 0
        with wave.open(str(wav)) as w:
            duracion = w.getnframes() / float(w.getframerate())

        inicio = cursor
        fin = cursor + duracion
        filas.append({
            "id": plano["id"],
            "inicio_real_seg": round(inicio, 3),
            "fin_real_seg": round(fin, 3),
            "estado": "pendiente",
            "imagen_path": None,
            "clip_path": None,
        })
        # El silencio va DESPUÉS de este plano: corre el cursor sin extender
        # su fin. El tiempo extra en pantalla lo da render_timeline, que
        # estira el clip hasta el inicio del siguiente plano.
        cursor = fin + _pausa_de(plano)

    destino = dest_dir / "planos_alineados.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(filas, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Alineación exacta escrita para %s planos (sin Whisper)", len(filas))
    return len(filas)


def _pausa_de(plano: dict) -> float:
    """Misma lectura que pipeline._pausa_despues_seg: en el plano o dentro de
    "audio". Si los dos leyeran distinto, el audio tendría la pausa y los
    tiempos de los planos no, y los subtítulos quedarían corridos."""
    crudo = plano.get("pausa_despues_seg")
    if crudo is None:
        crudo = (plano.get("audio") or {}).get("pausa_despues_seg")
    try:
        return max(0.0, float(crudo or 0))
    except (TypeError, ValueError):
        return 0.0


def generar_tarjetas(guion: dict, dest_dir: Path) -> int:
    """Genera las tarjetas de un guion de preguntas en el proyecto de
    illustrated-narrator. Devuelve cuántas generó.

    Se genera para TODO plano que declare `tarjeta`, no solo preguntas y
    respuestas: un plano de trivia sin tarjeta cae en la búsqueda de medios,
    que para este formato no tiene nada útil que encontrar y termina
    escalando a Claude. `identidad_cierre` queda afuera a propósito -- ese
    usa el logo del canal vía _apply_cierre.
    """
    generadas = 0
    numero = 0
    for plano in guion.get("planos", []):
        seccion = plano.get("seccion", "")
        if seccion == "identidad_cierre":
            continue

        # `tarjeta` permite un texto distinto al narrado: la voz puede decir
        # una frase larga y la pantalla mostrar solo lo esencial.
        texto = (plano.get("tarjeta") or "").strip()
        if not texto:
            continue

        destino = dest_dir / "media" / plano["id"] / "elegido.png"
        if seccion in SECCIONES_PREGUNTA:
            numero += 1
            tarjeta_pregunta(texto, numero, destino)
        elif seccion in SECCIONES_RESPUESTA:
            tarjeta_respuesta(texto, destino)
        else:
            tarjeta_simple(texto, destino)
        generadas += 1

    if generadas:
        logger.info("Tarjetas de preguntas generadas: %s", generadas)
    return generadas
