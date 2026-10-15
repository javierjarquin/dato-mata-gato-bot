"""Genera el cartel de cierre de los mitos a partir del cartel del canal.

El cartel de siempre dice "¿QUÉ OPINAS DE ESTE CASO?" y "SÍGUEME PARA MÁS
CASOS". En un mito "caso" suena a error: no es un caso, es una leyenda. Todo
lo demás (el gato, el logo, la arroba) queda igual, para que se siga viendo
como el cierre del canal.

Las coordenadas son las del cartel original de 720x1280, medidas sobre la
imagen (25/09/2026). Si se cambia el cartel del canal, hay que volver a
medirlas.

Uso:  python tools/cartel_cierre_mito.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ORIGEN = Path(r"C:\illustrated-narrator\assets\dato_mata_gato_cierre.jpg")
DESTINO = ORIGEN.with_name("dato_mata_gato_cierre_mito.png")

FUENTE_PREGUNTA = r"C:\Windows\Fonts\ariblk.ttf"   # Arial Black, la del canal
FUENTE_BOTON = r"C:\Windows\Fonts\arialbd.ttf"

PREGUNTA = ["¿CONOCÍAS ESTA LEYENDA?", "CUÉNTAMELO EN LOS COMENTARIOS"]
BOTON = "PARA MÁS LEYENDAS"
LEMA = "UNA HISTORIA NUEVA CADA SEMANA"

# Banda de la pregunta: bajo la regla horizontal, antes del botón. Se tapa
# con una franja vacía del mismo fondo (618-706, entre el logo y la regla),
# porque el fondo tiene textura de estrellas y un color liso se notaría.
BANDA = (0, 750, 720, 838)
FONDO_VACIO_Y = 618
CREMA = (232, 220, 190)

# Segunda línea del botón dorado ("PARA MÁS CASOS"): filas 952-971. Se queda
# adentro de las columnas 180-540 para no tocar las esquinas redondeadas.
LINEA_BOTON = (180, 948, 540, 975)
DORADO = (214, 174, 111)
TEXTO_BOTON = (40, 30, 20)

# Lema de abajo ("UN CASO NUEVO CADA SEMANA"): filas 1091-1104. Se tapa con la
# franja vacía de justo abajo (1108-1138), que conserva el filo del marco a
# los costados.
LEMA_FILAS = (1088, 1107)
LEMA_FONDO_Y = 1110
LEMA_COLOR = (190, 176, 140)


def _centrado(lienzo, y, texto, fuente, color, ancho=720):
    w = lienzo.textlength(texto, font=fuente)
    lienzo.text(((ancho - w) / 2, y), texto, font=fuente, fill=color)


def _fuente_que_entre(ruta, textos, tamano, ancho_max):
    """Achica la letra hasta que la línea más larga entre en el ancho."""
    lienzo = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    while tamano > 12:
        f = ImageFont.truetype(ruta, tamano)
        if max(lienzo.textlength(t, font=f) for t in textos) <= ancho_max:
            return f
        tamano -= 1
    return ImageFont.truetype(ruta, tamano)


def main() -> None:
    carta = Image.open(ORIGEN).convert("RGB")
    lienzo = ImageDraw.Draw(carta)

    alto = BANDA[3] - BANDA[1]
    vacio = carta.crop((0, FONDO_VACIO_Y, 720, FONDO_VACIO_Y + alto))
    carta.paste(vacio, (0, BANDA[1]))
    fuente = _fuente_que_entre(FUENTE_PREGUNTA, PREGUNTA, 30, 640)
    alto_linea = 40
    y = BANDA[1] + (alto - alto_linea * len(PREGUNTA)) // 2
    for linea in PREGUNTA:
        _centrado(lienzo, y, linea, fuente, CREMA)
        y += alto_linea

    lienzo.rectangle(LINEA_BOTON, fill=DORADO)
    _centrado(lienzo, 951, BOTON, ImageFont.truetype(FUENTE_BOTON, 20), TEXTO_BOTON)

    alto_lema = LEMA_FILAS[1] - LEMA_FILAS[0]
    carta.paste(carta.crop((0, LEMA_FONDO_Y, 720, LEMA_FONDO_Y + alto_lema)),
                (0, LEMA_FILAS[0]))
    _centrado(lienzo, 1090, LEMA, ImageFont.truetype(FUENTE_BOTON.replace("arialbd", "arial"), 15),
              LEMA_COLOR)

    carta.save(DESTINO)
    print("escrito", DESTINO)


if __name__ == "__main__":
    main()
