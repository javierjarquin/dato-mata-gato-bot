"""Los formatos de video del canal, y cómo se reparten en un lote.

Hasta el 18/09/2026 el canal tenía dos formatos: crimen y trivia. Revisados
los 107 guiones producidos, **67 de los 69 de crimen abrían exactamente
igual** (`hook_segunda_persona`: "Eres una joven de dieciocho años..."). Hay
49 esqueletos distintos, o sea que el medio del video varía bastante, pero la
entrada no cambia nunca -- y en vertical corto el primer segundo es donde se
decide si se quedan. Para alguien que sigue el canal, el video 5 se siente
igual que el video 1 desde el arranque.

Estos formatos existen para romper eso. Todos comparten las reglas de
`INSTRUCCION_NUEVO_LOTE` (estructura, hechos reales, cierre en bucle, reglas
de riesgo); lo que cambia es el ÁNGULO desde el que se cuenta el caso, y con
él la apertura.

Un formato no es una plantilla nueva de guion.json: es un párrafo que se le
suma a la instrucción base. Agregar uno es sumar una entrada acá.
"""

from dataclasses import dataclass

CRIMEN = "crimen"
TRIVIA = "trivia"
# Mitos y leyendas (25/09/2026). Como la trivia, va aparte de los formatos de
# crimen: tiene su propia instrucción entera (INSTRUCCION_MITO en bot.py), no
# un párrafo que se suma a la de crimen, porque cambia todo -- de tú en vez de
# tercera persona, sonidos en pausas, imágenes sin archivo. Fórmula completa
# en clip_assistance/analisis/formula_mitos.md.
MITO = "mito"


@dataclass(frozen=True)
class Formato:
    clave: str
    descripcion: str          # lo que se le muestra al usuario en Telegram
    instruccion: str          # el párrafo que se suma a INSTRUCCION_NUEVO_LOTE
    peso: int = 1             # cuánto aparece en un lote grande


# El formato de siempre: el caso contado de principio a fin, metiendo al
# espectador en los zapatos de la víctima. Sigue siendo el más fuerte, pero
# deja de ser el único.
_CLASICO = Formato(
    clave=CRIMEN,
    descripcion="de true crime clásico",
    instruccion="",
    peso=3,
)

_FAMOSO = Formato(
    clave="famoso",
    descripcion="de caso famoso con ángulo desconocido",
    instruccion=(
        "FORMATO DE ESTE GUION -- CASO FAMOSO, ÁNGULO DESCONOCIDO.\n"
        "Elegí un caso que MUCHA gente ya conoce de nombre (de los que salieron "
        "en televisión abierta y se volvieron sobrenombre popular) y contá UN "
        "detalle que casi nadie sabe. El gancho NO es presentar el caso: es la "
        "contradicción entre lo que todos creen y lo que pasó. Abrí nombrando "
        "lo que la gente da por sabido y desmintiéndolo en la misma frase.\n"
        "Por qué: los casos oscuros no tienen demanda de búsqueda -- nadie los "
        "busca porque nadie sabe que existen. Uno conocido ya tiene gente "
        "buscándolo, y el dato nuevo es lo que hace que se queden.\n"
        "El p00 empieza con la creencia que vas a romper. Ejemplo: \"Todos saben "
        "que confesó. Casi nadie sabe que lo hizo después de treinta horas sin "
        "dormir.\" El p01 sigue con la fórmula del \"Te imaginas a...\" de la "
        "instrucción base, igual que en todos los formatos.\n"
    ),
    peso=2,
)

_ABIERTO = Formato(
    clave="abierto",
    descripcion="de caso abierto para teorizar",
    instruccion=(
        "FORMATO DE ESTE GUION -- CASO ABIERTO.\n"
        "Elegí un caso REALMENTE sin resolver y contalo dejando la pregunta "
        "viva. El video no cierra con una explicación: cierra con lo que no "
        "encaja. El producto de este formato son los comentarios, así que la "
        "narración tiene que dejar material para teorizar -- dos o tres datos "
        "que se contradicen entre sí, presentados sin resolver.\n"
        "NO inventes teorías ni insinúes culpables: exponé los hechos que no "
        "cierran y dejá que el público los junte. Señalar a una persona real "
        "como responsable de algo no probado es justamente lo que este canal "
        "no hace.\n"
        "El p00 abre con el dato que no encaja, no con la víctima. Ejemplo: "
        "\"La cámara de la esquina grabó todo esa noche. El video desapareció "
        "de la carpeta tres semanas después.\"\n"
    ),
    peso=2,
)

_VERSION_OFICIAL = Formato(
    clave="version_oficial",
    descripcion="de versión oficial contra la evidencia",
    instruccion=(
        "FORMATO DE ESTE GUION -- LA VERSIÓN OFICIAL CONTRA LA EVIDENCIA.\n"
        "El video se estructura en dos columnas: lo que dijeron las "
        "autoridades y lo que mostró la evidencia. Alterná: primero la versión "
        "oficial de un punto, después lo que la contradice. Tres pares "
        "alcanzan.\n"
        "Cada contradicción tiene que ser VERIFICABLE y estar documentada -- un "
        "peritaje, una fecha, una declaración registrada. Si de un punto no "
        "tenés las dos mitades documentadas, no lo uses.\n"
        "El p00 abre con la versión oficial dicha en seco, para que suene "
        "razonable, y la primera contradicción entra enseguida. El llamado a "
        "la acción de este formato es siempre \"¿Le crees a la versión "
        "oficial?\".\n"
    ),
    peso=2,
)

_CULPABLE = Formato(
    clave="culpable",
    descripcion="de ¿culpable o inocente? con votación",
    instruccion=(
        "FORMATO DE ESTE GUION -- ¿CULPABLE O INOCENTE?\n"
        "Elegí un caso donde hubo una condena discutida o una absolución "
        "discutida. Presentá la evidencia de los dos lados de forma pareja: "
        "tres datos que apuntan a culpable, tres que apuntan a inocente, sin "
        "inclinar la balanza con adjetivos.\n"
        "NO reveles el fallo judicial en el cuerpo del video. El último plano "
        "de contenido pide la votación, y el fallo real queda para el video "
        "siguiente -- así el bucle cruza de un video a otro y la gente vuelve "
        "al perfil.\n"
        "El llamado a la acción de este formato es la votación: \"¿Culpable o "
        "inocente? Decímelo en los comentarios.\"\n"
        "Poné en `que_medir` que este guion espera una segunda parte con el "
        "fallo.\n"
    ),
    peso=1,
)

_DATO_15 = Formato(
    clave="dato_15",
    descripcion="de dato de 15 segundos",
    instruccion=(
        "FORMATO DE ESTE GUION -- DATO DE QUINCE SEGUNDOS.\n"
        "Un solo dato, contado entero, en TRES PLANOS y 35 A 45 PALABRAS EN "
        "TOTAL. Ignorá el presupuesto de 170-200 palabras: este formato es "
        "deliberadamente corto.\n"
        "Estructura: p00 el dato en una frase, p01 el detalle que lo vuelve "
        "increíble, p02 identidad_cierre con el llamado a la acción. Sin "
        "contexto y sin desarrollo.\n"
        "   Es el ÚNICO formato sin plano de contexto, así que tampoco lleva la "
        "fórmula del \"Te imaginas a...\": no hay lugar para presentar a nadie en "
        "cuarenta palabras. El p01 sigue en tercera persona y en pasado, igual "
        "que el resto.\n"
        "Existe para poder PROBAR ganchos rápido: un video normal cuesta "
        "quince minutos de máquina y uno con presentador casi una hora, y con "
        "ese costo no se puede experimentar. Diez de estos por semana enseñan "
        "más que dos videos largos.\n"
        "El dato tiene que aguantar solo, sin explicación previa.\n"
    ),
    peso=2,
)

FORMATOS = {f.clave: f for f in (_CLASICO, _FAMOSO, _ABIERTO, _VERSION_OFICIAL,
                                 _CULPABLE, _DATO_15)}

# Los de crimen, en el orden en que se reparten. La trivia va aparte porque no
# pasa por Claude: sale del banco de preguntas.
ORDEN = [_CLASICO, _FAMOSO, _ABIERTO, _VERSION_OFICIAL, _DATO_15, _CULPABLE]


def instruccion_de(clave: str) -> str:
    """El párrafo de formato que se suma a la instrucción base."""
    f = FORMATOS.get(clave)
    return f.instruccion if f else ""


def descripcion_de(clave: str) -> str:
    f = FORMATOS.get(clave)
    return f.descripcion if f else clave


def repartir_fish3(n: int) -> list[tuple[str, str, int]]:
    """El lote de /lotefish3 (29/09/2026): solo true crime con evidencia real.

    Sin trivias ni mitos, y sin el dato de 15 segundos: en ~40 palabras no
    entran los tres nombres con apellido y el lugar exacto que exige
    revision_guion, así que casi todos saldrían del lote.
    """
    if n <= 0:
        return []
    bloques = [f for f in ORDEN if f.clave != "dato_15"]
    total = sum(f.peso for f in bloques)
    crudo = [n * f.peso / total for f in bloques]
    cant = [int(c) for c in crudo]
    for i in sorted(range(len(bloques)), key=lambda i: (crudo[i] - cant[i], bloques[i].peso),
                    reverse=True)[:n - sum(cant)]:
        cant[i] += 1
    return [(f.clave, f.descripcion, c) for f, c in zip(bloques, cant) if c > 0]


def repartir(n: int, con_trivia: bool = False, con_mito: bool = True) -> list[tuple[str, str, int]]:
    """Reparte `n` videos entre los formatos, proporcional a su peso.

    Devuelve tramos (clave, descripción, cantidad) en el mismo formato que
    espera `_pedir_lote`. El reparto es determinístico: el mismo n da siempre
    el mismo lote, así que se puede repetir una corrida que se cortó.

    Sin trivias por defecto desde el 28/09/2026: el usuario las sacó del lote
    grande. Siguen existiendo por su comando propio; `con_trivia=True` las
    vuelve a meter.
    """
    if n <= 0:
        return []
    bloques = list(ORDEN)
    pesos = [f.peso for f in bloques]
    if con_trivia:
        # La trivia pesa como el formato clásico: es la mitad del canal hoy.
        bloques.append(Formato(TRIVIA, "de trivia", "", 3))
        pesos.append(3)
    if con_mito:
        # Pesa 2 y no 3: cada mito dura el doble que un video de crimen (unos
        # 2:15) y lleva el triple de imágenes, así que con el mismo peso que
        # el clásico se comería la mitad de las once horas de un lote grande.
        bloques.append(Formato(MITO, "de mitos y leyendas", "", 2))
        pesos.append(2)

    total = sum(pesos)
    # Reparto proporcional, y el resto va a los formatos de mayor peso: con
    # lotes chicos (5) eso deja el clásico y la trivia, que es lo que el canal
    # ya venía haciendo; el resto aparece recién cuando el lote da para más.
    crudo = [(n * p) / total for p in pesos]
    cant = [int(c) for c in crudo]
    resto = n - sum(cant)
    for i in sorted(range(len(bloques)), key=lambda i: (crudo[i] - cant[i], pesos[i]),
                    reverse=True)[:resto]:
        cant[i] += 1
    return [(b.clave, b.descripcion, c) for b, c in zip(bloques, cant) if c > 0]
