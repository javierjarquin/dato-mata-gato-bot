"""¿Lo que dice el guion está en sus fuentes? Sin IA y sin tokens (22/11/2026).

Auditoría del 22/11: papasia comprueba cada dato palabra por palabra contra la
página de donde salió; Dato Mata Gato solo revisaba la forma del guion
(preguntas, vigencia, registro) y la regla "verificar cada dato" dependía de
Claude. Los métodos publicados (FActScore, SAFE, VeriScore) separan el texto en
afirmaciones comprobables y buscan cada una en la evidencia; aquí se hace lo
mismo con lo que se puede comprobar sin un modelo:

- números (en cifras o en palabras: "setenta y dos años", "dos mil veintiuno",
  "treinta y tres punto seis por ciento");
- nombres propios (dos o más palabras con mayúscula: personas, lugares,
  instituciones);
- citas textuales (entre comillas).

Cada uno se busca en el texto de las fuentes del propio guion: las piezas de
`evidencia` con liga que son nota o documento (prensa, documento). Las fichas
(`tipo: ficha`) son afirmaciones que salen en pantalla: se revisan igual que la
narración. El texto de cada fuente se guarda en `<slug>\\_fuentes\\` para no
bajarlo dos veces.

No bloquea el video: lo que no aparece va al aviso de Telegram, para revisarlo
antes de publicar. Una fuente con muro de pago o que no se deja leer se reporta
aparte (no es un dato falso, es un dato que no se pudo comprobar).

    python -m dato_mata_gato_bot.verificar_datos <slug> [<slug> ...]
"""

import json
import logging
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

TIPOS_CON_TEXTO = ("prensa", "documento")
CARPETA = "_fuentes"
MINIMO_NUMERO = 10      # "dos hijos", "tres días": demasiado comunes para dar señal
COBERTURA_CITA = 0.6    # parte de las palabras de una cita que debe estar en las fuentes

# ------------------------------------------------------------------ normalizar


def normal(texto: str) -> str:
    """Minúsculas y sin acentos (la ñ queda como n: da igual para buscar)."""
    t = unicodedata.normalize("NFKD", texto or "").lower()
    return "".join(c for c in t if not unicodedata.combining(c))


def _palabras(texto: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:[.,][0-9]+)*", normal(texto))


# --------------------------------------------------------- números en palabras

_UNIDADES = {"cero": 0, "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
             "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12,
             "trece": 13, "catorce": 14, "quince": 15, "dieciseis": 16, "diecisiete": 17,
             "dieciocho": 18, "diecinueve": 19, "veinte": 20, "veintiun": 21, "veintiuno": 21,
             "veintiuna": 21, "veintidos": 22, "veintitres": 23, "veinticuatro": 24,
             "veinticinco": 25, "veintiseis": 26, "veintisiete": 27, "veintiocho": 28,
             "veintinueve": 29, "treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60,
             "setenta": 70, "ochenta": 80, "noventa": 90, "cien": 100, "ciento": 100,
             "doscientos": 200, "doscientas": 200, "trescientos": 300, "trescientas": 300,
             "cuatrocientos": 400, "cuatrocientas": 400, "quinientos": 500, "quinientas": 500,
             "seiscientos": 600, "seiscientas": 600, "setecientos": 700, "setecientas": 700,
             "ochocientos": 800, "ochocientas": 800, "novecientos": 900, "novecientas": 900}
_MULTIPLOS = {"mil": 1000, "millon": 10**6, "millones": 10**6}


def _cabe(actual: int, valor: int, tras_y: bool) -> bool:
    """¿La palabra que vale `valor` sigue al número que va en `actual` (dentro de
    un grupo de mil)? Así "dos mil veinte doce" son dos números (2020 y 12),
    no 2032: después de "veinte" solo cabe "y" + unidad o "mil"."""
    resto = actual % 1000
    if valor >= 100:
        return resto == 0
    if valor >= 10:
        return resto % 100 == 0
    if tras_y:
        return resto % 10 == 0 and resto % 100 >= 30
    return resto % 100 == 0


def _numero_de(palabras: list[str], i: int) -> tuple[float | None, int]:
    """Lee un número escrito en palabras desde palabras[i]. Devuelve (valor, cuántas
    palabras ocupó) o (None, 0)."""
    total, actual, j, visto = 0, 0, i, False
    while j < len(palabras):
        p = palabras[j]
        if p in _UNIDADES:
            if visto and not _cabe(actual, _UNIDADES[p], palabras[j - 1] == "y"):
                break
            actual += _UNIDADES[p]
        elif p in _MULTIPLOS:
            m = _MULTIPLOS[p]
            if m == 1000:
                total += (actual or 1) * 1000
            elif not visto:
                break  # "millones de vistas": sin número delante no es un dato
            else:
                total = (total + (actual or 1)) * m
            actual = 0
        elif p == "y" and visto and j + 1 < len(palabras) and palabras[j + 1] in _UNIDADES:
            pass
        elif p == "de" and visto and _MULTIPLOS.get(palabras[j - 1]) == 10**6:
            pass  # "dos millones de pesos"
        else:
            break
        visto = True
        j += 1
    if not visto:
        return None, 0
    if j < len(palabras) and palabras[j - 1] == "de":
        j -= 1
    valor: float = total + actual
    # "treinta y tres punto seis": decimales dígito por dígito o como número.
    if j + 1 < len(palabras) and palabras[j] == "punto":
        dec, k = _numero_de(palabras, j + 1)
        if dec is not None:
            valor = float(f"{int(valor)}.{int(dec)}")
            j += 1 + k
    return valor, j - i


def _de_cifra(token: str) -> set[float]:
    """'1,105,547' -> 1105547; '2.500' -> 2500 y 2.5 (no se sabe cuál); '33.6' -> 33.6."""
    valores: set[float] = set()
    limpio = token.strip(".,")
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", limpio):
        valores.add(float(re.sub(r"[.,]", "", limpio)))
    if re.fullmatch(r"\d+[.,]\d+", limpio):
        valores.add(float(limpio.replace(",", ".")))
    if re.fullmatch(r"\d+", limpio):
        valores.add(float(limpio))
    return valores


def numeros(texto: str, minimo: float = 0) -> list[tuple[str, float]]:
    """Los números de un texto, en cifras o en palabras, con el pedazo de texto
    que los dijo. "283 mil" cuenta como 283000."""
    pal = _palabras(texto)
    salida: list[tuple[str, float]] = []
    i = 0
    while i < len(pal):
        p = pal[i]
        if p[0].isdigit():
            sig = pal[i + 1] if i + 1 < len(pal) else ""
            tras = pal[i + 2] if i + 2 < len(pal) else ""
            for v in _de_cifra(p):
                dicho = p
                if sig in _MULTIPLOS:
                    v *= _MULTIPLOS[sig]
                    dicho += f" {sig}"
                    # "3 mil 301" (así escriben algunas notas) es 3301.
                    if sig == "mil" and re.fullmatch(r"\d{1,3}", tras):
                        v += int(tras)
                        dicho += f" {tras}"
                if v >= minimo:
                    salida.append((dicho, v))
            i += len(dicho.split())
            continue
        if p == "ciento" and i and pal[i - 1] == "por":
            i += 1   # "por ciento" no es el número cien
            continue
        valor, largo = _numero_de(pal, i)
        if valor is not None and largo:
            if valor >= minimo:
                salida.append((" ".join(pal[i:i + largo]), valor))
            i += largo
            continue
        i += 1
    return salida


# --------------------------------------------------------------- nombres y citas

_CONECTORES = {"de", "del", "la", "las", "los", "y", "el"}
# Mayúsculas que no son un dato: arranques de frase comunes, la marca, meses y días.
# Mayúsculas que no son un dato: arranques de frase comunes, la marca, meses y días
# (sin acentos: se comparan con normal()).
_NO_NOMBRE = {"dato", "mata", "gato", "te", "tu", "yo", "el", "ella", "ellos", "ellas", "la", "los",
              "las", "un", "una", "eso", "esto", "esta", "este", "pero", "y", "o", "si", "no", "ni",
              "que", "por", "porque", "cuando", "como", "donde", "ahi", "hoy", "ayer", "segun", "todo",
              "toda", "todos", "todas", "nadie", "quedan", "queda", "tambien", "mientras", "luego",
              "despues", "antes", "entonces", "aqui", "asi", "nunca", "siempre", "cada", "otro", "otra",
              "sin", "con", "para", "en", "al", "lo", "le", "se", "su", "sus", "mi", "ya", "mas", "solo",
              "hay", "fue", "era", "es", "son",
              "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
              "octubre", "noviembre", "diciembre", "lunes", "martes", "miercoles", "jueves", "viernes",
              "sabado", "domingo"}
_COMILLAS = r"[\"“”«»]"
_PALABRA_NOMBRE = r"[A-ZÁÉÍÓÚÑ][a-záéíóúñü]+"


def nombres(texto: str) -> list[str]:
    """Secuencias de dos o más palabras con mayúscula inicial ('Reyna González',
    'Estado de México', 'Richard Hart'). Una sola palabra con mayúscula no
    cuenta (en español casi siempre es arranque de frase), ni las palabras
    TODO EN MAYÚSCULAS (son textos en pantalla, no nombres)."""
    salida = []
    for m in re.finditer(_PALABRA_NOMBRE + r"(?:\s+(?:(?:de|del|la|las|los|y|el)\s+)*" + _PALABRA_NOMBRE + ")+",
                         texto or ""):
        palabras = m.group(0).split()
        while palabras and normal(palabras[0]) in _NO_NOMBRE:
            palabras.pop(0)   # "Según Noticaribe", "Quedan Ariadna": el arranque no es nombre
        partes = [p for p in palabras if p.lower() not in _CONECTORES and normal(p) not in _NO_NOMBRE]
        if len(partes) >= 2:
            salida.append(" ".join(palabras))
    return salida


def citas(texto: str) -> list[str]:
    return [c.strip() for c in re.findall(_COMILLAS + r"([^\"“”«»]{12,})" + _COMILLAS, texto or "")]


# ----------------------------------------------------------------- las fuentes


def _ruta_texto(carpeta: Path, pieza: dict) -> Path:
    return carpeta / CARPETA / f"{pieza.get('id', 'x')}.txt"


def leer_completo(url: str) -> str | None:
    """Como `expediente.leer`, pero sin tope y con favor_recall: con favor_precision
    trafilatura dejaba fuera párrafos con datos (en la nota de Milenio del pan no
    salía "Cámara"). Aquí sobra texto: solo se busca en él."""
    import httpx
    import trafilatura

    from dato_mata_gato_bot import expediente

    try:
        r = httpx.get(url, headers=expediente.NAVEGADOR, timeout=20, follow_redirects=True)
        r.raise_for_status()
    except httpx.HTTPError:
        return None
    if r.content[:5] == b"%PDF-" or "pdf" in r.headers.get("content-type", ""):
        return expediente._de_pdf(r.content)
    return trafilatura.extract(r.text, include_comments=False, include_tables=True, favor_recall=True)


def textos_de_fuentes(guion: dict, carpeta: Path, leer=None) -> tuple[dict[str, str], list[str]]:
    """{id: texto} de las fuentes legibles y la lista de las que no se dejaron leer.
    `leer(url)` devuelve el texto o None."""
    leer = leer or leer_completo
    textos: dict[str, str] = {}
    fallidas: list[str] = []
    for pieza in guion.get("evidencia") or []:
        if pieza.get("tipo") not in TIPOS_CON_TEXTO or not pieza.get("url"):
            continue
        ruta = _ruta_texto(carpeta, pieza)
        if ruta.exists():
            texto = ruta.read_text(encoding="utf-8")
        else:
            try:
                texto = leer(pieza["url"]) or ""
            except Exception as exc:  # noqa: BLE001 -- una fuente rota no tumba la revisión
                logger.warning("verificar_datos: %s: %s", pieza["url"], exc)
                texto = ""
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_text(texto, encoding="utf-8")
        if texto.strip():
            textos[pieza.get("id", "?")] = texto
        else:
            fallidas.append(f"{pieza.get('id', '?')} ({pieza.get('fuente') or pieza['url']})")
    return textos, fallidas


# --------------------------------------------------------------- la revisión


@dataclass
class Dato:
    plano: str
    tipo: str      # numero | nombre | cita
    texto: str
    encontrado: bool


@dataclass
class Reporte:
    datos: list[Dato] = field(default_factory=list)
    fuentes: list[str] = field(default_factory=list)
    ilegibles: list[str] = field(default_factory=list)

    @property
    def sin_respaldo(self) -> list[Dato]:
        return [d for d in self.datos if not d.encontrado]

    def resumen(self) -> str:
        if not self.fuentes:
            if self.ilegibles:
                return ("🔎 Datos: no pude leer ninguna fuente para comprobarlos ("
                        + ", ".join(self.ilegibles[:4]) + ").")
            return ""
        total = len(self.datos)
        linea = f"🔎 Datos: {total - len(self.sin_respaldo)} de {total} están en las fuentes"
        if self.sin_respaldo:
            linea += "; revisa antes de publicar:\n" + "\n".join(
                f"- {d.plano} ({d.tipo}): {d.texto[:80]}" for d in self.sin_respaldo[:12])
            if len(self.sin_respaldo) > 12:
                linea += f"\n- … y {len(self.sin_respaldo) - 12} más"
        else:
            linea += "."
        if self.ilegibles:
            linea += "\nFuentes que no se dejaron leer: " + ", ".join(self.ilegibles[:4])
        return linea


def _afirmaciones(guion: dict) -> list[tuple[str, str]]:
    """(dónde, texto) de lo que el video afirma: narración, texto en pantalla y fichas."""
    salida = []
    for plano in guion.get("planos") or []:
        pid = plano.get("id", "?")
        for clave in ("narracion", "texto_en_pantalla"):
            if plano.get(clave):
                salida.append((pid, str(plano[clave])))
    for pieza in guion.get("evidencia") or []:
        if pieza.get("tipo") == "ficha":
            # Cada renglón por separado: pegados, "Reyna" de un renglón y "Sonó" del
            # siguiente parecían un nombre.
            for renglon in [pieza.get("titulo") or "", *(pieza.get("renglones") or [])]:
                if renglon:
                    salida.append((f"ficha {pieza.get('id', '?')}", str(renglon)))
    return salida


def _valores(textos: list[str]) -> set[float]:
    return {v for t in textos for _, v in numeros(t)}


def revisar(guion: dict, textos: dict[str, str]) -> Reporte:
    reporte = Reporte(fuentes=list(textos))
    fuentes = [normal(t) for t in textos.values()]
    unidas = "\n".join(fuentes)
    palabras_fuentes = set(_palabras(unidas))
    valores = _valores(list(textos.values()))
    vistos: set[tuple[str, str]] = set()

    def anotar(plano: str, tipo: str, texto: str, ok: bool) -> None:
        clave = (tipo, normal(texto))
        if clave in vistos:
            return
        vistos.add(clave)
        reporte.datos.append(Dato(plano, tipo, texto, ok))

    este_anio = datetime.now().year
    for plano, texto in _afirmaciones(guion):
        for dicho, valor in numeros(texto, MINIMO_NUMERO):
            if valor == este_anio:
                continue  # "hoy, en 2026": contexto, no un dato que comprobar
            anotar(plano, "numero", dicho, valor in valores)
        for nombre in nombres(texto):
            partes = [normal(p) for p in nombre.split() if p.lower() not in _CONECTORES
                      and normal(p) not in _NO_NOMBRE]
            # 3 de cada 4 palabras basta: las notas dicen "Ariadna Fernanda López" y
            # el guion el nombre completo, con "Díaz".
            ok = normal(nombre) in unidas or (
                bool(partes) and sum(p in palabras_fuentes for p in partes) / len(partes) >= 0.75)
            anotar(plano, "nombre", nombre, ok)
        for cita in citas(texto):
            llenas = [p for p in _palabras(cita) if len(p) > 3]
            ok = bool(llenas) and sum(p in palabras_fuentes for p in llenas) / len(llenas) >= COBERTURA_CITA
            anotar(plano, "cita", cita, ok)
    return reporte


def revisar_slug(slug: str, entrada: Path | None = None, leer=None) -> Reporte:
    from dato_mata_gato_bot import pipeline

    carpeta = (entrada or pipeline.ANDROID_IN) / slug
    guion = json.loads((carpeta / "guion.json").read_text(encoding="utf-8"))
    textos, ilegibles = textos_de_fuentes(guion, carpeta, leer)
    reporte = revisar(guion, textos)
    reporte.ilegibles = ilegibles
    return reporte


def aviso(slug: str) -> str:
    """La línea para el aviso de Telegram; nunca lanza (no debe tumbar un video)."""
    try:
        return revisar_slug(slug).resumen()
    except Exception as exc:  # noqa: BLE001
        logger.warning("verificar_datos %s: %s", slug, exc)
        return ""


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for s in sys.argv[1:]:
        r = revisar_slug(s)
        print(f"== {s}")
        print(r.resumen() or "(sin fuentes de texto en la evidencia)")
