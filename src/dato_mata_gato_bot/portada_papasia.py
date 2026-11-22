"""Portada vertical de papasia (22/11/2026), con el estilo del banner de Papás con IA.

Degradado pastel (durazno -> azul cielo), destellos, el logo "PAPÁS con IA"
(letra gruesa blanca con contorno marino, "IA" en amarillo), las 3 a 5
palabras de `plus.portada` (la palabra de `resalta` en una píldora rosa) y una
tarjeta con un cuadro del propio video (el bebé de plastilina).

Antes los videos de papasia llevaban la portada de Dato Mata Gato.

    python -m dato_mata_gato_bot.portada_papasia <guion.json> <video.mp4> <salida.jpg> [segundo]
"""
from __future__ import annotations

import json
import random
import re
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ANCHO, ALTO = 1080, 1920
MARINO = (36, 48, 94)
AMARILLO = (255, 201, 60)
ROSA = (242, 102, 143)
BLANCO = (255, 255, 255)
FUENTE = Path(r"C:\Windows\Fonts\seguibl.ttf")  # Segoe UI Black, la misma del render 3D


def _fuente(tam: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FUENTE), tam)


def _degradado() -> Image.Image:
    """Diagonal durazno -> crema -> azul cielo, como el banner."""
    paradas = [(0.0, (255, 212, 192)), (0.5, (255, 246, 238)), (1.0, (190, 230, 252))]
    chico = Image.new("RGB", (108, 192))
    px = chico.load()
    for y in range(192):
        for x in range(108):
            t = (x / 107 * 0.45 + y / 191 * 0.55)
            for (t0, c0), (t1, c1) in zip(paradas, paradas[1:]):
                if t <= t1:
                    k = (t - t0) / (t1 - t0)
                    px[x, y] = tuple(round(a + (b - a) * k) for a, b in zip(c0, c1))
                    break
    return chico.resize((ANCHO, ALTO), Image.BICUBIC)


def _manchas(lienzo: Image.Image) -> None:
    """Luces suaves de colores, desenfocadas."""
    capa = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    for (x, y, r, c) in [(120, 520, 220, (255, 190, 210, 70)), (980, 380, 260, (175, 220, 255, 60)),
                         (900, 1500, 300, (255, 238, 160, 70)), (140, 1700, 260, (195, 228, 255, 70))]:
        d.ellipse((x - r, y - r, x + r, y + r), fill=c)
    lienzo.alpha_composite(capa.filter(ImageFilter.GaussianBlur(90)))


def _destello(d: ImageDraw.ImageDraw, x: float, y: float, r: float, color) -> None:
    """Estrellita de cuatro puntas."""
    k = r * 0.28
    d.polygon([(x, y - r), (x + k, y - k), (x + r, y), (x + k, y + k),
               (x, y + r), (x - k, y + k), (x - r, y), (x - k, y - k)], fill=color)


def _destellos(lienzo: Image.Image) -> None:
    capa = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    azar = random.Random(7)
    for x, y in [(90, 120), (990, 160), (60, 900), (1020, 820), (110, 1420), (985, 1250), (540, 70), (870, 1820)]:
        r = azar.uniform(18, 34)
        _destello(d, x, y, r, azar.choice([(255, 255, 255, 230), (255, 214, 90, 220), (255, 170, 200, 210)]))
    for _ in range(26):  # puntitos
        x, y, r = azar.uniform(30, ANCHO - 30), azar.uniform(30, ALTO - 30), azar.uniform(4, 9)
        d.ellipse((x - r, y - r, x + r, y + r),
                  fill=azar.choice([(255, 255, 255, 170), (255, 205, 120, 150), (150, 200, 255, 150)]))
    lienzo.alpha_composite(capa)


def _texto(lienzo: Image.Image, xy, texto: str, fuente, relleno, contorno, grosor: int, sombra=True) -> None:
    capa = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    if sombra:
        d.text((xy[0], xy[1] + grosor), texto, font=fuente, fill=(36, 48, 94, 90),
               stroke_width=grosor, stroke_fill=(36, 48, 94, 90))
        capa = capa.filter(ImageFilter.GaussianBlur(6))
        d = ImageDraw.Draw(capa)
    d.text(xy, texto, font=fuente, fill=relleno, stroke_width=grosor, stroke_fill=contorno)
    lienzo.alpha_composite(capa)


def _logo(lienzo: Image.Image, y: int) -> int:
    """'PAPÁS' arriba y 'con IA' abajo, centrados. Devuelve dónde termina."""
    f1, f2, f3 = _fuente(122), _fuente(84), _fuente(122)
    d = ImageDraw.Draw(lienzo)
    w1 = d.textlength("PAPÁS", font=f1)
    _texto(lienzo, ((ANCHO - w1) / 2, y), "PAPÁS", f1, BLANCO, MARINO, 12)
    y2 = y + 128
    wcon, wia = d.textlength("con ", font=f2), d.textlength("IA", font=f3)
    x = (ANCHO - wcon - wia) / 2
    _texto(lienzo, (x, y2 + 32), "con ", f2, BLANCO, MARINO, 10)
    _texto(lienzo, (x + wcon, y2), "IA", f3, AMARILLO, MARINO, 12)
    return y2 + 150


def _limpio(t: str) -> str:
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z0-9]", "", t)


def _titulo(lienzo: Image.Image, y: int, texto: str, resalta: list[str], ancho_max: int = 940) -> int:
    """Las palabras de plus.portada en marino con contorno blanco; las de `resalta`,
    en blanco sobre una píldora rosa. Achica la letra hasta caber en 3 renglones."""
    marcadas = {_limpio(w) for r in resalta for w in str(r).split()}
    palabras = texto.upper().split()
    d = ImageDraw.Draw(lienzo)
    for tam in range(124, 60, -6):
        f = _fuente(tam)
        esp = d.textlength(" ", font=f) * 1.1
        renglones, actual, w_act = [], [], 0.0
        for p in palabras:
            w = d.textlength(p, font=f) + (tam * 0.5 if _limpio(p) in marcadas else 0)
            if actual and w_act + esp + w > ancho_max:
                renglones.append((actual, w_act))
                actual, w_act = [], 0.0
            w_act += (esp if actual else 0) + w
            actual.append((p, w))
        renglones.append((actual, w_act))
        if len(renglones) <= 3:
            break
    alto_r = tam * 1.22
    for fila, w_fila in renglones:
        x = (ANCHO - w_fila) / 2
        for p, w in fila:
            if _limpio(p) in marcadas:
                capa = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 0))
                dc = ImageDraw.Draw(capa)
                dc.rounded_rectangle((x, y + tam * 0.02, x + w, y + tam * 1.26), radius=tam * 0.32,
                                     fill=ROSA + (255,))
                sombra = capa.filter(ImageFilter.GaussianBlur(10))
                lienzo.alpha_composite(Image.eval(sombra, lambda v: v // 3))
                lienzo.alpha_composite(capa)
                _texto(lienzo, (x + tam * 0.25, y - tam * 0.04), p, f, BLANCO, BLANCO, 0, sombra=False)
            else:
                _texto(lienzo, (x, y - tam * 0.04), p, f, MARINO, BLANCO, 9, sombra=False)
            x += w + esp
        y += alto_r
    return round(y)


def _cuadro(video: Path, segundo: float) -> Image.Image:
    with tempfile.TemporaryDirectory() as tmp:
        jpg = Path(tmp) / "cuadro.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(segundo), "-i", str(video),
                        "-frames:v", "1", str(jpg)], check=True)
        return Image.open(jpg).convert("RGB").copy()


def _tarjeta(lienzo: Image.Image, cuadro: Image.Image, y: int, y_max: int) -> None:
    """El centro del cuadro (donde está el bebé) en una tarjeta redondeada con borde blanco."""
    w, h = cuadro.size
    recorte = cuadro.crop((round(w * 0.10), round(h * 0.235), round(w * 0.90), round(h * 0.80)))
    alto = max(300, y_max - y)
    ancho = min(round(alto * recorte.width / recorte.height), 760)
    alto = round(ancho * recorte.height / recorte.width)
    recorte = recorte.resize((ancho, alto), Image.LANCZOS)
    x = (ANCHO - ancho) // 2
    borde, radio = 16, 56
    capa = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    d.rounded_rectangle((x - borde, y - borde + 18, x + ancho + borde, y + alto + borde + 18), radius=radio + borde,
                        fill=(120, 90, 140, 90))
    lienzo.alpha_composite(capa.filter(ImageFilter.GaussianBlur(22)))
    d = ImageDraw.Draw(lienzo)
    d.rounded_rectangle((x - borde, y - borde, x + ancho + borde, y + alto + borde), radius=radio + borde, fill=BLANCO)
    mascara = Image.new("L", (ancho, alto), 0)
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, ancho - 1, alto - 1), radius=radio, fill=255)
    lienzo.paste(recorte, (x, y), mascara)


def armar(guion: dict, video: Path, salida: Path, segundo: float = 1.0) -> Path:
    p = (guion.get("plus") or {}).get("portada") or {}
    texto = str(p.get("texto") or guion.get("titulo") or "").strip()
    resalta = p.get("resalta") or []
    resalta = [resalta] if isinstance(resalta, str) else list(resalta)

    lienzo = _degradado().convert("RGBA")
    _manchas(lienzo)
    _destellos(lienzo)
    y = _logo(lienzo, 90)
    y = _titulo(lienzo, y + 40, texto, resalta)
    _tarjeta(lienzo, _cuadro(video, segundo), y + 50, ALTO - 150)
    salida.parent.mkdir(parents=True, exist_ok=True)
    lienzo.convert("RGB").save(salida, quality=92)
    return salida


if __name__ == "__main__":
    g = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print(armar(g, Path(sys.argv[2]), Path(sys.argv[3]), float(sys.argv[4]) if len(sys.argv) > 4 else 1.0))
