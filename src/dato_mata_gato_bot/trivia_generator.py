"""Arma guiones de trivia desde el banco de preguntas. SIN Claude, sin IA.

Las 27 trivias publicadas comparten UNA sola estructura (verificado: 27 de 27)
y dos de sus planos son idénticos palabra por palabra en las 27. O sea que un
guion de trivia es una plantilla con huecos, y los huecos son datos: tema, tres
preguntas con su respuesta, y las búsquedas de imagen.

Lo que este módulo NO hace es inventar preguntas. Salen del banco
(`data/banco_preguntas.json`), que se llena a mano o se importa de una planilla
— es a propósito: en un canal que se llama Dato Mata Gato, el dato lo verifica
una persona antes de entrar, no un generador.
"""

import json
import logging
import random
import unicodedata
from pathlib import Path

logger = logging.getLogger(__name__)

RAIZ = Path(__file__).resolve().parent.parent.parent
BANCO_PATH = RAIZ / "data" / "banco_preguntas.json"
USADAS_PATH = RAIZ / "data" / "trivia_usadas.json"

# Sprites del gato, uno por tema (el gato con bata en quimica, con casco en
# espacio...). Si no existe la carpeta del tema, el guion no declara mascota y
# el pipeline usa la del entorno -- el gato de siempre.
MASCOTAS_DIR = Path("C:/illustrated-narrator/assets")
MASCOTA_BASE = "mascota_gato"

DIFICULTADES = ("facil", "media", "dificil")

# Cuántas preguntas lleva el video y con qué dificultad va cada una. El orden
# importa: la rampa de fácil a imposible, anunciada desde el segundo cero, es
# lo que sostiene la permanencia.
RAMPAS = {
    3: ("facil", "media", "dificil"),
    6: ("facil", "facil", "media", "media", "dificil", "dificil"),
}
PREGUNTAS_POR_DEFECTO = 6

# Conectores. Cortos a propósito en el formato de 6: con los de 3 ("Y la que
# casi nadie saca") el video se iba a ~95s, y arriba de ~80 la finalización
# se cae. Medido: 129 palabras + 3 pausas = 52s; seis preguntas con los
# conectores largos daban 230 palabras + 6 pausas.
_ENTRADA_LARGA = {"facil": "La fácil.", "media": "La media.", "dificil": "Y la que casi nadie saca."}
_ENTRADA_CORTA = {"facil": "Fácil.", "media": "Media.", "dificil": "Difícil."}

_FRASE_CIERRE = "Aquí el dato mata al gato… y la historia mata el sueño."

# El cierre de identidad tiene que PEDIR algo, igual que en los guiones de
# crimen (18/09/2026). La firma sola son tres segundos que no convierten. Acá
# el pedido es el número de aciertos, que es lo natural de una trivia y además
# se contesta con una palabra -- el comentario más fácil de dejar que existe.
_CIERRE_CON_PEDIDO = (
    "Aquí el dato mata al gato. ¿Cuántas sacaste? Ponelo en los comentarios."
)

# Texto grande de apertura. Corto a propósito: máximo 35 caracteres, igual que
# el `gancho` de los guiones de crimen.
_GANCHO_PANTALLA = "¿CUÁNTAS SACÁS?"

# Tope del título, en caracteres. Mismo criterio que los guiones de crimen.
_TITULO_MAX = 30


def _titulo_corto(tema: str) -> str:
    """'fugas-carceles' -> 'Trivia: Fugas Carceles'."""
    limpio = _sin_acentos(tema).replace("-", " ").replace("_", " ").strip().title()
    titulo = f"Trivia: {limpio}"
    return titulo if len(titulo) <= _TITULO_MAX else titulo[:_TITULO_MAX].rstrip()
# El cierre en bucle, sin el número (que depende del total). Solo se usa para
# presupuestar palabras.
_CIERRE_BASE = "¿Cuántas de las sacaste? Pon tu número aquí abajo. ¿Y la primera te pareció fácil?"

# Bajada de 2.5 a 2.0: con seis preguntas, medio segundo de más por pausa son
# tres segundos de silencio extra en el video.
PAUSA_PREGUNTA_SEG = 2.0

# Presupuesto de palabras del video entero. La narracion se lee a ~170 palabras
# por minuto, asi que 200 palabras + 12s de pausas dan ~82s. Medido el
# 14/09/2026: sin tope, un lote real salio de 316 palabras = 124 segundos, mas
# largo que los videos de crimen que acababamos de acortar.
PRESUPUESTO_PALABRAS = 200


class BancoInsuficiente(RuntimeError):
    """No hay preguntas sin usar para armar lo pedido."""


def _sin_acentos(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))


def cargar_banco(path: Path = BANCO_PATH) -> dict[str, list]:
    if not path.exists():
        raise BancoInsuficiente(f"No existe el banco en {path}")
    return json.loads(path.read_text(encoding="utf-8")).get("temas", {})


def cargar_usadas(path: Path = USADAS_PATH) -> set[str]:
    if not path.exists():
        return set()
    return set(json.loads(path.read_text(encoding="utf-8")).get("usadas", []))


def marcar_usadas(ids: list[str], path: Path = USADAS_PATH) -> None:
    usadas = cargar_usadas(path) | set(ids)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"usadas": sorted(usadas)}, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def _preguntas_de(entrada) -> list[dict]:
    """Las preguntas de un tema. Acepta el formato viejo (lista pelada) y el
    nuevo ({"nombre":..., "preguntas":[...]}), así un banco a medio migrar no
    tumba la generación."""
    return entrada.get("preguntas", []) if isinstance(entrada, dict) else (entrada or [])


def _nombre_de(entrada, tema: str) -> str:
    if isinstance(entrada, dict) and entrada.get("nombre"):
        return entrada["nombre"]
    return tema.replace("-", " ")


def rampa_de(cantidad: int) -> tuple[str, ...]:
    """Dificultades en orden para un video de `cantidad` preguntas."""
    if cantidad in RAMPAS:
        return RAMPAS[cantidad]
    raise ValueError(f"No hay rampa definida para {cantidad} preguntas: {sorted(RAMPAS)}")


def _seleccion(preguntas: list[dict], usadas: set[str], rampa: tuple[str, ...]) -> list[dict] | None:
    """Preguntas sin usar que cubren la rampa, o None si el tema no alcanza.

    Se van descontando a medida que se eligen: una rampa con dos 'facil'
    necesita DOS preguntas fáciles distintas, no la misma repetida.
    """
    tomadas: set[str] = set()
    elegidas = []
    for dif in rampa:
        libres = [
            q for q in preguntas
            if q.get("dificultad") == dif and q["id"] not in usadas and q["id"] not in tomadas
        ]
        if not libres:
            return None
        elegidas.append(libres[0])
        tomadas.add(libres[0]["id"])
    return elegidas


def temas_disponibles(
    banco: dict, usadas: set[str], cantidad: int = PREGUNTAS_POR_DEFECTO
) -> list[str]:
    """Temas que todavía tienen preguntas sin usar para llenar la rampa."""
    rampa = rampa_de(cantidad)
    return sorted(
        t for t, e in banco.items() if _seleccion(_preguntas_de(e), usadas, rampa) is not None
    )


def _slug_libre(tema: str, existentes: set[str]) -> str:
    base = f"trivia-{_sin_acentos(tema).lower().replace(' ', '-')}"
    n = 1
    while f"{base}-{n:02d}" in existentes:
        n += 1
    return f"{base}-{n:02d}"


_ETIQUETA = {"facil": "FÁCIL", "media": "MEDIA", "dificil": "DIFÍCIL"}


def _entrada(dif: str, n: int, total: int) -> str:
    """Lo que se dice antes de la pregunta n de total."""
    if n == total:
        return "Y la última, la que casi nadie saca."
    return (_ENTRADA_CORTA if total > 3 else _ENTRADA_LARGA)[dif]


def _empujon(n: int, total: int) -> str:
    """El marcador hablado. Es el motor de retención del formato: el
    espectador acumula puntaje y se queda a ver si llega al final."""
    if n == total:
        return ""
    if n == total - 1:
        return "Si las llevas todas, la que sigue duele."
    return f"Vas {n} de {total}."


def _plano_pregunta(idx: int, q: dict, inicio: int, n: int, total: int) -> dict:
    vis = q.get("pregunta_visual") or {}
    return {
        "id": f"p{idx:02d}",
        "seccion": "pregunta",
        "inicio_aprox": f"0:{inicio:02d}",
        "duracion_seg": 4,
        "pausa_despues_seg": PAUSA_PREGUNTA_SEG,
        "narracion": f"{_entrada(q['dificultad'], n, total)} {q['pregunta']}".strip(),
        "texto_grande": q.get("texto_pregunta") or q["pregunta"],
        "visual": {
            "tipo": "imagen_ia",
            "descripcion": vis.get("descripcion", ""),
            "prompt_ia": vis.get("prompt_ia", ""),
            "busqueda_medios": vis.get("busqueda_medios", ""),
        },
        "texto_en_pantalla": f"{n} DE {total} · {_ETIQUETA[q['dificultad']]}",
        "audio": {"musica": "tension breve", "sfx": "reloj"},
    }


def _plano_respuesta(idx: int, q: dict, inicio: int, n: int, total: int,
                    con_extra: bool = True) -> dict:
    vis = q.get("respuesta_visual") or {}
    extra = q.get("dato_extra", "") if con_extra else ""
    partes = [q["respuesta"].rstrip("."), extra, _empujon(n, total)]
    narracion = ". ".join(p.strip().rstrip(".") for p in partes if p.strip()) + "."
    return {
        "id": f"p{idx:02d}",
        "seccion": "respuesta",
        "inicio_aprox": f"0:{inicio:02d}",
        "duracion_seg": 4,
        "narracion": narracion,
        "texto_grande": q.get("texto_respuesta") or q["respuesta"].upper(),
        "visual": {
            "tipo": "imagen_ia",
            "descripcion": vis.get("descripcion", ""),
            "prompt_ia": vis.get("prompt_ia", ""),
            "busqueda_medios": vis.get("busqueda_medios", ""),
        },
        "audio": {"musica": "resolucion breve", "sfx": "campana"},
    }


def _palabras(*textos) -> int:
    return sum(len(t.split()) for t in textos if t)


def _extras_que_entran(trio: list[dict], gancho: str, total: int) -> list[bool]:
    """Que datos extra caben en el presupuesto, de la ultima hacia atras."""
    base = _palabras(gancho, _CIERRE_BASE, _FRASE_CIERRE)
    for n, q in enumerate(trio, start=1):
        base += _palabras(_entrada(q["dificultad"], n, total), q["pregunta"],
                          q["respuesta"], _empujon(n, total))

    entran = [False] * len(trio)
    for i in reversed(range(len(trio))):
        extra = _palabras(trio[i].get("dato_extra", ""))
        if not extra:
            continue
        if base + extra > PRESUPUESTO_PALABRAS:
            break
        base += extra
        entran[i] = True
    return entran


def armar_guion(tema: str, trio: list[dict], slug: str, video_id: int,
                nombre: str | None = None) -> dict:
    total = len(trio)
    dificil = trio[-1]
    nombre = nombre or tema.replace("-", " ")
    numero = {3: "Tres", 6: "Seis"}.get(total, str(total))
    # El gancho anuncia la rampa y adelanta la ÚLTIMA pregunta sin responderla:
    # es la promesa que sostiene la permanencia hasta el final.
    gancho = (
        f"{numero} preguntas de {nombre}, de fácil a imposible. "
        f"La última casi nadie la saca: {dificil['pregunta'].strip('¿?').lower()}."
    )
    planos = [{
        "id": "p00",
        "seccion": "hook_preguntas",
        "inicio_aprox": "0:00",
        "duracion_seg": 8,
        "narracion": gancho,
        "visual": {
            "tipo": "imagen_ia",
            "descripcion": (dificil.get("pregunta_visual") or {}).get("descripcion", ""),
            "prompt_ia": (dificil.get("pregunta_visual") or {}).get("prompt_ia", ""),
            "busqueda_medios": (dificil.get("pregunta_visual") or {}).get("busqueda_medios", ""),
        },
        "texto_en_pantalla": f"{total} PREGUNTAS",
        "audio": {"musica": "tension breve", "sfx": "un golpe seco"},
    }]
    # Los datos extra son lo primero que se cae si el video se pasa de largo:
    # suman color pero no son la pregunta. Se conservan en las ULTIMAS, que es
    # donde el espectador ya invirtio tiempo y el dato remata.
    con_extra = _extras_que_entran(trio, gancho, total)

    idx, inicio = 1, 8
    for n, q in enumerate(trio, start=1):
        planos.append(_plano_pregunta(idx, q, inicio, n, total))
        idx, inicio = idx + 1, inicio + 7
        planos.append(_plano_respuesta(idx, q, inicio, n, total, con_extra=con_extra[n - 1]))
        idx, inicio = idx + 1, inicio + 5
    planos.append({
        "id": f"p{idx:02d}",
        "seccion": "cierre_interaccion",
        "inicio_aprox": f"0:{inicio:02d}",
        "duracion_seg": 4,
        # Cierre en BUCLE: devuelve a la frase de apertura para que al repetirse
        # el video se sienta continuo. El re-visionado es de las señales de
        # distribución más fuertes en Shorts.
        "narracion": f"¿Cuántas de las {total} sacaste? Pon tu número aquí abajo. "
                     f"¿Y la primera te pareció fácil?",
        "texto_grande": f"COMENTÁ TU NÚMERO: 0 A {total}",
        "visual": {
            "tipo": "imagen_ia",
            "descripcion": "Manos escribiendo en la pantalla de un telefono, primer plano.",
            "prompt_ia": "Hands typing on a phone screen, close up.",
            "busqueda_medios": "hands typing phone screen close up",
        },
        "audio": {"musica": "tension breve", "sfx": "ninguno"},
    })
    planos.append({
        "id": f"p{idx + 1:02d}",
        "seccion": "identidad_cierre",
        "inicio_aprox": f"0:{inicio + 4:02d}",
        "duracion_seg": 4,
        "narracion": _CIERRE_CON_PEDIDO,
        "frase_cierre": _CIERRE_CON_PEDIDO,
        "visual": {
            "tipo": "grafico_movimiento",
            "descripcion": "Logo del canal pequeno y centrado sobre negro puro, sin brillo ni particulas.",
            "prompt_ia": "Small channel logo centered on pure black, no glow, no particles.",
        },
        "texto_en_pantalla": "DATO MATA GATO",
        "audio": {"musica": "una sola nota grave que se apaga", "sfx": "ninguno"},
    })

    etiqueta = _sin_acentos(tema).title().replace("-", "")
    guion = {
        "_schema": {
            "como_usarlo": (
                "Formato de preguntas generado por trivia_generator.py (sin IA). "
                "`pausa_despues_seg` inserta silencio despues del plano: la pregunta queda en "
                "pantalla mientras el espectador piensa. `texto_grande` la dibuja grande y "
                "centrada sobre la foto."
            ),
            "identidad_canal": {
                "nombre": "Dato Mata Gato",
                "frase_cierre": _FRASE_CIERRE,
                "regla": "Solo frase_cierre es fija. El arranque no lleva plano de identidad.",
            },
        },
        "video_id": video_id,
        "version": f"TRIVIA-{_sin_acentos(tema)}-auto",
        # El título nombra, no cuenta (misma regla que los guiones de crimen
        # desde el 17/09/2026). Antes era la pregunta difícil entera y salían
        # de 49 caracteres -- "queciudadsegunlaleyendaincendiounavaca.mp4" como
        # nombre de archivo, y el titular llenando la pantalla si faltaba
        # gancho. Ahora es el tema.
        "titulo": _titulo_corto(tema),
        # Texto GRANDE de los primeros segundos. Sin esto el video muestra el
        # título entero justo en los segundos que deciden la retención.
        "gancho": _GANCHO_PANTALLA,
        "duracion_estimada": "0:55",
        "hashtags": ["#DatoMataGato", "#Trivia", "#CulturaGeneral", f"#{etiqueta}", "#Preguntas"],
        "planos": planos,
        # Se arrastra la verificación de cada pregunta: es lo que permite
        # re-chequear el dato sin volver a investigarlo desde cero.
        "verificar_antes_de_publicar": [q.get("verificacion", "") for q in trio],
    }
    # `mascota` va en la RAIZ: script_loader mezcla los campos sueltos de la
    # raiz con los de `meta`, y los guiones de este canal no traen objeto meta.
    disfraz = MASCOTAS_DIR / f"{MASCOTA_BASE}_{_sin_acentos(tema)}"
    if disfraz.is_dir():
        guion["mascota"] = {"modo": "mascota", "ruta": str(disfraz)}
    return guion


def generar(
    cantidad: int,
    destino: Path,
    banco_path: Path = BANCO_PATH,
    usadas_path: Path = USADAS_PATH,
    semilla: int | None = None,
    preguntas: int = PREGUNTAS_POR_DEFECTO,
) -> list[str]:
    """Escribe `cantidad` guiones de trivia en `destino`. Devuelve los slugs."""
    rampa = rampa_de(preguntas)
    banco = cargar_banco(banco_path)
    usadas = cargar_usadas(usadas_path)
    disponibles = temas_disponibles(banco, usadas, preguntas)
    if len(disponibles) < cantidad:
        raise BancoInsuficiente(
            f"Pedidas {cantidad} trivias de {preguntas} preguntas, pero solo "
            f"{len(disponibles)} tema(s) tienen suficientes preguntas sin usar "
            f"({', '.join(disponibles) or 'ninguno'}). Cargá más al banco: "
            "python tools/agregar_preguntas.py --csv <archivo>"
        )

    azar = random.Random(semilla)
    elegidos = azar.sample(disponibles, cantidad)
    destino.mkdir(parents=True, exist_ok=True)
    existentes = {p.name for p in destino.iterdir() if p.is_dir()}

    slugs, gastadas = [], []
    for i, tema in enumerate(elegidos):
        trio = _seleccion(_preguntas_de(banco[tema]), usadas | set(gastadas), rampa)
        if trio is None:  # otro tema se llevó las preguntas en esta misma tanda
            continue
        slug = _slug_libre(tema, existentes)
        existentes.add(slug)
        guion = armar_guion(tema, trio, slug, video_id=1000 + i,
                            nombre=_nombre_de(banco[tema], tema))
        carpeta = destino / slug
        carpeta.mkdir(parents=True, exist_ok=True)
        (carpeta / "guion.json").write_text(
            json.dumps(guion, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        slugs.append(slug)
        gastadas += [q["id"] for q in trio]
        logger.info("Trivia generada: %s (tema %s)", slug, tema)

    # Recién al final: si algo explota a mitad, las preguntas no quedan
    # quemadas sin guion que las use.
    marcar_usadas(gastadas, usadas_path)
    return slugs
