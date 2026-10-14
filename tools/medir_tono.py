"""Mide qué tan explosivo suena un lote de guiones, antes de gastar la máquina.

El tono es lo que retiene: un video de true crime que suena a boletín de
prensa pierde al espectador en el primer segundo aunque los datos sean
correctos. Esto no juzga la veracidad (eso es `verificar_antes_de_publicar`),
juzga cómo está DICHO.

Cinco cosas, todas contables -- nada de "se siente flojo":

1. **Sujeto abstracto.** "Un operativo militar terminó liberando al detenido"
   no tiene a nadie adentro. Los sujetos burocráticos ("un operativo", "la
   responsabilidad", "las autoridades") le sacan la cara al hecho.
2. **Cobertura.** Verbos y sustantivos de prensa que suavizan: "se vino
   abajo" en vez de "se cayó", "perdió la vida" en vez de "murió", "resultó
   con lesiones". El canal no los usa.
3. **Relleno de ensayo.** "en cambio", "con claridad", "cabe mencionar",
   "de alguna manera". Cada uno son palabras que no aportan un dato y sí
   ocupan segundos.
4. **Remate del gancho.** El p00 tiene que TERMINAR en la palabra que golpea.
   Si cierra con un complemento ("...con gente adentro de los vagones") el
   golpe queda a mitad de la frase.
5. **Aperturas repetidas.** Si diez guiones abren con "Un/Una + sustantivo",
   el lote se siente igual aunque los casos sean distintos. Es el mismo
   problema que mataron los formatos, corrido un renglón.

Uso:
    python tools/medir_tono.py                 # el lote pendiente del chat
    python tools/medir_tono.py guion-x guion-y
    python tools/medir_tono.py --todos         # todo lo que haya en Android_in
"""

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

ANDROID_IN = Path(r"C:\Android_in")


def _pelado(texto: str) -> str:
    sin = "".join(c for c in unicodedata.normalize("NFKD", texto)
                  if not unicodedata.combining(c))
    return sin.lower()


# Sujetos sin cara: el hecho le pasa a una abstracción, no a alguien.
ABSTRACTOS = [
    "un operativo", "el operativo", "un dispositivo", "la responsabilidad",
    "las autoridades", "la autoridad", "el gobierno federal", "la dependencia",
    "la institucion", "las instituciones", "el sistema", "la investigacion",
    "el proceso", "la situacion", "el caso", "un hecho", "los hechos",
    "la version oficial", "el expediente", "la carpeta", "un inmueble",
    "el detenido", "los involucrados", "las partes", "el suceso",
]

# Lenguaje de boletín: dice lo mismo, pero acolchonado.
COBERTURA = [
    "perdio la vida", "perdieron la vida", "resulto con", "resultaron con",
    "se vino abajo", "se dio a conocer", "fue dado a conocer", "tuvo lugar",
    "se llevo a cabo", "llevaron a cabo", "presuntamente", "presunto",
    "presunta", "supuestamente", "al parecer", "se presume", "habria",
    "trascendio", "se registro", "se suscito", "fue reportado",
    "de acuerdo con las autoridades", "segun las autoridades",
    "privado de la vida", "sin vida", "lamentables hechos", "deceso",
]

# Relleno de ensayo: ocupa segundos y no trae un dato.
RELLENO = [
    "en cambio", "sin embargo", "no obstante", "cabe mencionar",
    "cabe destacar", "es importante", "de alguna manera", "de cierta forma",
    "con claridad", "de manera clara", "en cierto modo", "por su parte",
    "asimismo", "en este sentido", "dicho esto", "vale la pena",
    "en definitiva", "a fin de cuentas", "de hecho", "practicamente",
]

# Voseo: el canal es mexicano y se narra de tú. El lote del 22/09/2026 salió
# con "Decímelo" y "¿Creés?" en los 20 cierres, y nadie lo midió porque esta
# herramienta no lo buscaba. Se compara la palabra CON acento (el acento es lo
# que distingue "caminás" de "caminas"), así que no se pela antes.
VOSEO = re.compile(
    r"\b(decímelo|decime|contame|contámelo|mirá|fijate|fíjate|andá|vení|hacé|poné|"
    r"tomá|dejá|pedí|elegí|revisá|creés|tenés|podés|querés|sabés|sentís|venís|"
    r"caminás|escuchás|mirás|pensás|volteás|corrés|comentá|comentalo|contás|llevás|jugás|sacás|"
    r"imaginás|sos)\b",
    re.IGNORECASE,
)


# Cola colgada: la última frase del gancho mete una coma y después un
# complemento que matiza en vez de golpear. El golpe queda a mitad de frase.
#
#   mal: "...se vino abajo en plena hora pico, CON GENTE ADENTRO DE LOS VAGONES."
#   bien: "...se partió en hora pico. Adentro iba gente."
#
# Se mira SOLO lo que va después de la última coma, y solo cuenta si arranca
# con preposición o con gerundio: eso es lo que convierte el remate en una
# aclaración. Una coma seguida de "y ..." no es el problema, es ritmo.
#
# La primera versión buscaba la preposición en cualquier parte del final de la
# frase y sin \b, así que la "a" de "la cámara" o de "la cárcel" contaba como
# preposición: marcó 15 de 20 ganchos, la mayoría mal. Los otros números de
# esa medición (aperturas repetidas, frases de 30+ palabras, cierres
# calcados) no dependían de esto y sí eran reales.
_PREPOS = r"con|sin|de|desde|hacia|entre|para|por|en|ante|tras|a"
COLA_COLGADA = re.compile(rf"^(?:{_PREPOS})\b\s+\S+(?:\s+\S+)+$|^\S+(?:ando|endo)\b\s+\S+")


def _frases(texto: str) -> list[str]:
    return [f.strip() for f in re.split(r"(?<=[.!?])\s+", texto.strip()) if f.strip()]


def _cuenta(texto: str, lexico: list[str]) -> list[str]:
    p = _pelado(texto)
    return [t for t in lexico if t in p]


def analizar(slug: str, entrada: Path = ANDROID_IN) -> dict | None:
    ruta = entrada / slug / "guion.json"
    if not ruta.exists():
        return None
    g = json.loads(ruta.read_text(encoding="utf-8"))
    planos = g.get("planos", [])
    if not planos:
        return None

    contenido = [p for p in planos if p.get("seccion") != "identidad_cierre"]
    texto = " ".join(p.get("narracion", "") for p in contenido)
    todo = " ".join(p.get("narracion", "") for p in planos)
    p00 = contenido[0].get("narracion", "") if contenido else ""
    cierre = contenido[-1].get("narracion", "") if contenido else ""

    frases = _frases(texto)
    largos = [len(f.split()) for f in frases] or [0]

    # El remate: lo que va después de la última coma de la última frase.
    ultima = _frases(p00)[-1] if _frases(p00) else p00
    cola = _pelado(ultima).rstrip(".!?").rsplit(",", 1)
    remate_flojo = len(cola) == 2 and bool(COLA_COLGADA.match(cola[1].strip()))

    return {
        "slug": slug,
        "titulo": g.get("titulo", slug),
        "gancho": g.get("gancho", ""),
        "p00": p00,
        "cierre": cierre,
        "palabras": len(texto.split()),
        "frase_larga": max(largos),
        "frase_media": sum(largos) / len(largos),
        "abstractos": _cuenta(texto, ABSTRACTOS),
        "cobertura": _cuenta(texto, COBERTURA),
        "relleno": _cuenta(texto, RELLENO),
        "voseo": sorted({m.group(0) for m in VOSEO.finditer(todo)}),
        "remate_flojo": remate_flojo,
        "abre_con": " ".join(_pelado(p00).split()[:2]),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("slugs", nargs="*")
    ap.add_argument("--todos", action="store_true")
    ap.add_argument("--entrada", type=Path, default=ANDROID_IN)
    args = ap.parse_args()

    if args.slugs:
        slugs = args.slugs
    elif args.todos:
        slugs = sorted(d.name for d in args.entrada.iterdir()
                       if (d / "guion.json").exists())
    else:
        from dato_mata_gato_bot import sessions
        estado = json.loads(sessions.SESSIONS_PATH.read_text(encoding="utf-8"))
        slugs = next((v["pending_batch"] for v in estado.values()
                      if v.get("pending_batch")), [])

    filas = [f for f in (analizar(s, args.entrada) for s in slugs) if f]
    if not filas:
        raise SystemExit("no encontré guiones para medir")

    print(f"{len(filas)} guiones\n")
    print(f"{'guion':<34}{'pal':>4}{'frase+':>7}{'abstr':>6}"
          f"{'cobert':>7}{'rell':>5}{'voseo':>6}{'remate':>8}")
    print("-" * 77)
    for f in filas:
        print(f"{f['slug'][:33]:<34}{f['palabras']:>4}{f['frase_larga']:>7}"
              f"{len(f['abstractos']):>6}{len(f['cobertura']):>7}"
              f"{len(f['relleno']):>5}{len(f['voseo']):>6}"
              f"{('FLOJO' if f['remate_flojo'] else 'ok'):>8}")

    tot_abs = sum(len(f["abstractos"]) for f in filas)
    tot_cob = sum(len(f["cobertura"]) for f in filas)
    tot_rel = sum(len(f["relleno"]) for f in filas)
    flojos = sum(f["remate_flojo"] for f in filas)
    tot_vos = sum(len(f["voseo"]) for f in filas)
    print("-" * 77)
    print(f"{'TOTAL':<34}{'':>4}{'':>7}{tot_abs:>6}{tot_cob:>7}{tot_rel:>5}"
          f"{tot_vos:>6}{flojos:>8}")
    if tot_vos:
        print("\nVOSEO (el canal es mexicano, va de tú):")
        for f in filas:
            if f["voseo"]:
                print(f"   {f['slug']}: {', '.join(f['voseo'])}")

    print(f"\nganchos con el remate a mitad de frase: {flojos}/{len(filas)}")
    aperturas = Counter(f["abre_con"].split()[0] for f in filas if f["abre_con"])
    print("primera palabra del gancho hablado:")
    for palabra, n in aperturas.most_common(6):
        marca = "  <-- repetida" if n >= max(3, len(filas) // 5) else ""
        print(f"   {palabra:<12} {n:>2}{marca}")

    peores = sorted(filas, key=lambda f: -(len(f["abstractos"]) * 2
                                           + len(f["cobertura"]) * 2
                                           + len(f["relleno"])
                                           + f["remate_flojo"]))[:6]
    print("\nlos que más lo necesitan:")
    for f in peores:
        problemas = (f["abstractos"] + f["cobertura"] + f["relleno"] + f["voseo"]
                     + (["remate a mitad de frase"] if f["remate_flojo"] else []))
        if not problemas:
            continue
        print(f"\n  {f['slug']}")
        print(f"    p00: {f['p00']}")
        print(f"    cierre: {f['cierre']}")
        print(f"    marcas: {', '.join(problemas)}")


if __name__ == "__main__":
    main()
