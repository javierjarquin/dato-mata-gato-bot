"""Evidencia real para un true crime, sin imágenes de IA (29/09/2026).

Claude investiga el caso UNA vez, al escribir el guion, y deja en guion.json
una lista `evidencia` (qué pieza, de dónde) y en cada plano `visual.evidencia`
(qué piezas van ahí). Este módulo hace el resto SIN volver a llamar a Claude:
baja, captura y arma cada pieza, y la deja como imagen manual del plano.

Tipos de pieza, cada uno con su base para poder usarlo:

  lugar / persona  foto de Wikimedia Commons (licencia libre, con autor). Persona
                   solo para funcionarios o figuras públicas: nunca víctimas ni
                   acusados sin sentencia.
  documento        texto oficial: página de un PDF o captura de una página web
                   (CNDH, fiscalía, sentencia). LFDA art. 14 fracc. VIII: los
                   textos administrativos y judiciales no tienen derechos.
  prensa           captura SOLO del titular y la fecha de una nota, con la fuente
                   en pantalla. Cita, LFDA art. 148. Se corta antes de la primera
                   imagen: la foto de la nota no se usa.
  ficha            un dato escrito con su fuente. No es una foto de nadie.

Nació del POC de Tierra Blanca (28/09/2026): 16 de 18 true crime recientes
tenían todas sus imágenes hechas por IA, y la audiencia decía que los videos
parecían cuentos.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from itertools import cycle, islice
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

ENTRADA = Path(r"C:\Android_in")
UA = {"User-Agent": "DatoMataGato-evidencia/1.0 (javier.jarquin.chooc@gmail.com)"}
ANCHO, ALTO = 1080, 1920
# Zona segura: el movimiento de cámara del narrador recorta los costados. Con
# 40 px de margen, el primer render de Tierra Blanca se comía el final de cada
# renglón de las fichas.
MARGEN = 170
TOMAS_POR_PLANO = 5  # de sobra: el narrador pide entre 1 y 4 según el largo
FONDO, AMARILLO, BLANCO, GRIS = (14, 14, 16), (235, 200, 60), (240, 240, 240), (150, 150, 150)
# Piezas con texto: el plano va con movimiento "calm" (zoom máx. 1.18 en vez
# de 1.30), si no el acercamiento se come letras del borde.
CON_TEXTO = {"documento", "prensa", "ficha"}
REALES = {"lugar", "persona", "documento", "prensa"}


@dataclass
class Reporte:
    piezas: dict[str, str] = field(default_factory=dict)   # id -> tipo
    fallidas: dict[str, str] = field(default_factory=dict)  # id -> motivo
    planos_prestados: list[str] = field(default_factory=list)

    @property
    def reales(self) -> int:
        return sum(1 for t in self.piezas.values() if t in REALES)

    def resumen(self) -> str:
        tipos = {}
        for t in self.piezas.values():
            tipos[t] = tipos.get(t, 0) + 1
        txt = ", ".join(f"{n} {t}" for t, n in sorted(tipos.items())) or "ninguna"
        if self.fallidas:
            txt += f"; fallaron {len(self.fallidas)}"
        return f"evidencia: {txt}"


def tiene_evidencia(guion: dict) -> bool:
    return bool(guion.get("evidencia"))


# --- dibujo -----------------------------------------------------------------

def _fuente(tam: int, negrita: bool = True):
    try:
        return ImageFont.truetype("arialbd.ttf" if negrita else "arial.ttf", tam)
    except OSError:
        return ImageFont.load_default()


def _envolver(d, texto: str, fuente, ancho: int) -> list[str]:
    lineas, linea = [], ""
    for palabra in texto.split():
        prueba = (linea + " " + palabra).strip()
        if d.textlength(prueba, font=fuente) > ancho and linea:
            lineas.append(linea)
            linea = palabra
        else:
            linea = prueba
    return lineas + [linea] if linea else lineas


def _lienzo() -> Image.Image:
    return Image.new("RGB", (ANCHO, ALTO), FONDO)


def dibujar_ficha(titulo: str, renglones: list[str], fuente: str, destino: Path) -> Path:
    im = _lienzo()
    d = ImageDraw.Draw(im)
    x, ancho, y = MARGEN, ANCHO - 2 * MARGEN, 600
    for linea in _envolver(d, titulo.upper(), _fuente(72), ancho):
        d.text((x, y), linea, fill=AMARILLO, font=_fuente(72))
        y += 86
    y += 30
    d.line([(x, y), (x + ancho, y)], fill=AMARILLO, width=4)
    y += 50
    for r in renglones:
        for linea in _envolver(d, r, _fuente(46, False), ancho):
            d.text((x, y), linea, fill=BLANCO, font=_fuente(46, False))
            y += 60
        y += 22
    for linea in _envolver(d, f"FUENTE: {fuente.upper()}", _fuente(30), ancho):
        d.text((x, y + 40), linea, fill=GRIS, font=_fuente(30))
        y += 40
    im.save(destino, quality=92)
    return destino


def montar_tarjeta(recorte: Image.Image, fuente: str, destino: Path) -> Path:
    """Un recorte (titular, página de documento) centrado, con la fuente abajo."""
    ancho = ANCHO - 2 * MARGEN
    recorte = recorte.convert("RGB")
    recorte = recorte.resize((ancho, round(recorte.height * ancho / recorte.width)),
                             Image.LANCZOS)
    im = _lienzo()
    y = max(80, (ALTO - recorte.height) // 2 - 60)
    im.paste(recorte, (MARGEN, y))
    d = ImageDraw.Draw(im)
    for i, linea in enumerate(_envolver(d, f"FUENTE: {fuente.upper()}", _fuente(30), ancho)):
        d.text((MARGEN, y + recorte.height + 36 + i * 40), linea, fill=AMARILLO, font=_fuente(30))
    im.save(destino, quality=92)
    return destino


# --- fuentes ----------------------------------------------------------------

_API_COMMONS = "https://commons.wikimedia.org/w/api.php"


def _titulo_wikimedia(pieza: dict) -> str | None:
    if pieza.get("wikimedia"):
        t = pieza["wikimedia"]
        return t if t.startswith("File:") else f"File:{t}"
    q = pieza.get("buscar_wikimedia")
    if not q:
        return None
    # Si la búsqueda completa no trae nada, se prueba con menos palabras:
    # "Temixco Morelos palacio municipal" no encontró nada (29/09/2026), pero
    # "Temixco Morelos" sí trae fotos del municipio.
    palabras = q.split()
    for n in range(len(palabras), 0, -1):
        r = requests.get(_API_COMMONS, headers=UA, timeout=30, params={
            "action": "query", "list": "search", "srnamespace": 6, "srlimit": 5,
            "format": "json", "srsearch": " ".join(palabras[:n])}).json()
        for hit in r.get("query", {}).get("search", []):
            if re.search(r"\.(jpe?g|png)$", hit["title"], re.IGNORECASE):
                return hit["title"]
        if n <= 1 or n <= len(palabras) - 2:
            break  # dos recortes como mucho: más corto ya trae cualquier cosa
    return None


def bajar_wikimedia(pieza: dict, destino: Path) -> dict:
    titulo = _titulo_wikimedia(pieza)
    if not titulo:
        raise ValueError("sin archivo en Wikimedia")
    info = requests.get(_API_COMMONS, headers=UA, timeout=30, params={
        "action": "query", "titles": titulo, "prop": "imageinfo",
        "iiprop": "url|extmetadata", "iiurlwidth": ANCHO, "format": "json"}).json()
    pagina = next(iter(info["query"]["pages"].values()))
    if "imageinfo" not in pagina:
        raise ValueError(f"{titulo} no existe")
    ii = pagina["imageinfo"][0]
    meta = ii.get("extmetadata", {})
    crudo = requests.get(ii.get("thumburl") or ii["url"], headers=UA, timeout=60)
    crudo.raise_for_status()
    destino.write_bytes(crudo.content)
    Image.open(destino).convert("RGB").save(destino, quality=92)
    return {"fuente": ii["descriptionurl"],
            "licencia": meta.get("LicenseShortName", {}).get("value", "?"),
            "autor": re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "?"))[:120]}


def pagina_pdf(pieza: dict, destino: Path) -> dict:
    import pymupdf

    r = requests.get(pieza["url"], headers=UA, timeout=120)
    r.raise_for_status()
    doc = pymupdf.open(stream=r.content, filetype="pdf")
    num = max(1, int(pieza.get("pagina", 1)))
    if num > len(doc):
        raise ValueError(f"el PDF tiene {len(doc)} páginas, no {num}")
    pag = doc[num - 1]
    # La mitad de arriba: en una recomendación o sentencia ahí está el título,
    # el número y la fecha, que es lo que se lee en un celular.
    # "desde" corta también por arriba, para cuando el dato está a media página
    # (informe de Aguakan, p. 7: los 185 pozos están al 72% del alto).
    alto = pag.rect.height * float(pieza.get("fraccion", 0.55))
    arriba = pag.rect.height * float(pieza.get("desde", 0))
    png = pag.get_pixmap(dpi=150, clip=pymupdf.Rect(0, arriba, pag.rect.width, alto))
    from io import BytesIO
    montar_tarjeta(Image.open(BytesIO(png.tobytes("png"))), pieza.get("fuente", ""), destino)
    return {"fuente": pieza["url"], "pagina": num}


_COMUNES = {"viejo", "vieja", "nuevo", "nueva", "unico", "unica", "villa", "santa", "santo",
            "grande", "blanco", "blanca", "negro", "negra", "verde", "campo", "monte",
            "puerto", "mayor", "menor", "general", "nacional", "estatal", "municipal"}


def claves_del_caso(guion: dict) -> list[str]:
    """Palabras que una página TIENE que mencionar para ser evidencia de este
    caso: apellidos, nombres completos y lugares del guion (sin acentos).

    Nace de guion-gisela-mota-temixco (29/09/2026): el enlace de Milenio ya no
    llevaba a la nota y la captura tomó otro artículo ("Jalisco despenalizó el
    aborto..."), que habría salido en pantalla con "FUENTE: MILENIO".
    """
    from dato_mata_gato_bot import revision_guion

    claves = set()
    for nombre in revision_guion.nombres_de_persona(guion):
        partes = revision_guion._sin_acentos(nombre).split()
        claves.add(" ".join(partes))
        # Los apellidos solos, no el nombre de pila: "José" sale en cualquier
        # nota. Y ni cortos ni palabras comunes: "Pueblo Viejo" y "Mando Único"
        # dejaban como clave "viejo" y "unico", que aparecen en cualquier página.
        claves.update(p for p in partes[1:] if len(p) >= 5 and p not in _COMUNES)
    for lugar in revision_guion.lugares_exactos(guion):
        claves.add(revision_guion._sin_acentos(lugar))
    # El nombre del caso también vale: "Declara Ieqroo validez de consulta
    # contra Aguakán" es del caso aunque no nombre a ninguna persona ni lugar
    # del guion (Caso Aguakan, 05/10/2026).
    # Desde 4 letras: "Tren Maya" quedaba fuera con el mínimo de 5, y la
    # captura de El Diario tomó otra nota que nombraba a Sheinbaum (05/10/2026).
    for palabra in revision_guion._sin_acentos(guion.get("titulo", "")).split():
        if len(palabra) >= 4 and palabra not in _COMUNES and palabra not in _VACIAS:
            claves.add(palabra)
    # Y las que el guion declare: "asur" y "aeropuerto" para una nota de la
    # tala de ASUR dentro de un video sobre Punta Nizuc.
    claves.update(revision_guion._sin_acentos(c) for c in guion.get("claves", []))
    return sorted(claves)


_VACIAS = {"caso", "para", "como", "entre", "sobre", "desde", "hasta", "contra"}


_JS_LIMPIAR = """() => {
  for (const e of document.querySelectorAll('body *')) {
    const pos = getComputedStyle(e).position;
    if (pos === 'fixed' || pos === 'sticky') e.remove();
  }
  document.querySelectorAll(
    'iframe, ins, video, [id*="google_ads"], [id*="div-gpt"], [class*="publicidad"], ' +
    '[class*="advert"], [class*="banner"], [id*="banner"], [class*="ads-"], [class*="-ads"]'
  ).forEach(e => e.remove());
}"""


_JS_BUSCAR = """([claves, soloTitulos]) => {
  const plano = s => s.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase();
  const menciona = t => claves.some(k => new RegExp('\\\\b' + k + '\\\\b').test(plano(t)));
  const visible = e => { const r = e.getBoundingClientRect();
    return r.width > 40 && r.height > 8 && getComputedStyle(e).visibility !== 'hidden'; };
  // Titulares: primero los h1 y después los h2, y nunca un texto corto -- en
  // La Palabra del Caribe la etiqueta de sección "CANCÚN" (un h2) ganaba al
  // titular de la nota (Caso Aguakan, 05/10/2026).
  const candidatos = soloTitulos
    ? [...document.querySelectorAll('h1'), ...document.querySelectorAll('h2')]
    : [...document.querySelectorAll('h1, h2, h3, p, li, td')];
  for (const e of candidatos) {
    if ((e.innerText || '').trim().length < 25) continue;
    if (visible(e) && menciona(e.innerText || '')) {
      e.scrollIntoView({block: 'center'});
      const r = e.getBoundingClientRect();
      return {y: r.top, h: r.height, tag: e.tagName, texto: (e.innerText || '').slice(0, 160)};
    }
  }
  return null;
}"""


def capturar_titular(paginas, pieza: dict, destino: Path, claves: list[str]) -> dict:
    """El titular (y lo que tiene justo debajo: fecha, autor), SOLO si habla
    del caso. La página entera trae anuncios y, a veces, fotos de las víctimas.

    Prensa: el titular tiene que nombrar a alguien o algún lugar del caso; si
    no, la nota no es la que se buscaba. Documento: si el titular no lo
    nombra, vale el primer párrafo que sí (una Gaceta Parlamentaria es una
    lista, y el punto del caso está en el medio).
    """
    pagina = paginas.new_page()
    try:
        resp = pagina.goto(pieza["url"], wait_until="domcontentloaded", timeout=45000)
        if resp is not None and resp.status >= 400:
            raise ValueError(f"HTTP {resp.status}")
        pagina.wait_for_timeout(3000)
        for texto in ("Aceptar", "Acepto", "Entendido", "Cerrar", "No, gracias"):
            try:
                pagina.get_by_role("button", name=texto).first.click(timeout=600)
            except Exception:  # noqa: BLE001
                pass
        # Fuera lo que flota y la publicidad ANTES de buscar: en el Caso Aguakan
        # (05/10/2026) una barra fija con el autor tapaba el titular de La
        # Palabra del Caribe, un anuncio de gobierno el de La Jornada, y uno de
        # apuestas se colaba debajo del de La Silla Rota.
        pagina.evaluate(_JS_LIMPIAR)
        es_documento = pieza.get("tipo") == "documento"
        hallado = pagina.evaluate(_JS_BUSCAR, [claves, True])
        if hallado is None and es_documento:
            hallado = pagina.evaluate(_JS_BUSCAR, [claves, False])
        if hallado is None:
            raise ValueError("la página no menciona el caso (ni nombres ni lugares del guion)")
        titular = hallado["texto"].strip()
        # Una página que "existe" pero dice 404 (visto en la CNDH, 28/09/2026).
        if re.search(r"\b404\b|no encontr", titular, re.IGNORECASE):
            raise ValueError(f"sin titular válido ({titular[:40]!r})")
        pagina.wait_for_timeout(400)
        caja = {"y": hallado["y"], "height": min(hallado["h"], 420)}
        arriba = max(0, caja["y"] - 30)
        img_top = pagina.evaluate(
            """(fondo) => { const t = [...document.images]
                 .map(i => i.getBoundingClientRect())
                 .filter(r => r.top > fondo && r.width > 60 && r.height > 40)
                 .map(r => r.top); return t.length ? Math.min(...t) : null; }""",
            caja["y"] + caja["height"])
        abajo = caja["y"] + caja["height"] + 110
        if img_top is not None:
            abajo = min(abajo, img_top - 6)
        crudo = destino.with_suffix(".captura.png")
        pagina.screenshot(path=str(crudo), clip={"x": 0, "y": arriba, "width": 430,
                                                 "height": max(40, abajo - arriba)})
        montar_tarjeta(Image.open(crudo), pieza.get("fuente", ""), destino)
        crudo.unlink(missing_ok=True)
        return {"fuente": pieza["url"], "titular": titular[:160]}
    finally:
        pagina.close()


# --- armado -----------------------------------------------------------------

def _es_pdf(url: str) -> bool:
    return url.lower().split("?")[0].endswith(".pdf")


def preparar(slug: str, entrada: Path | None = None) -> Reporte:
    """Construye la evidencia del guion y la deja como imágenes manuales.

    Modifica el guion.json de entrada: los planos con piezas de texto quedan
    con `visual.motion = "calm"`. Reanudable: una pieza ya armada no se rehace.
    """
    base = (entrada or ENTRADA) / slug
    ruta_guion = base / "guion.json"
    guion = json.loads(ruta_guion.read_text(encoding="utf-8"))
    piezas = {p["id"]: p for p in guion.get("evidencia", []) if p.get("id")}
    carpeta = base / "evidencia"
    carpeta.mkdir(parents=True, exist_ok=True)
    manifest_path = carpeta / "manifest.json"
    # utf-8-sig: un manifest guardado desde PowerShell trae BOM y json lo rechaza.
    manifest = (json.loads(manifest_path.read_text(encoding="utf-8-sig"))
                if manifest_path.exists() else {})
    reporte = Reporte()
    claves = claves_del_caso(guion)

    necesitan_navegador = [p for p in piezas.values()
                           if p.get("tipo") in ("documento", "prensa")
                           and p.get("url") and not _es_pdf(p["url"])]
    ctx = nav = pw = None
    if necesitan_navegador:
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        nav = pw.chromium.launch()
        ctx = nav.new_context(viewport={"width": 430, "height": 760}, device_scale_factor=2.5,
                              locale="es-MX", user_agent=(
                                  "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 "
                                  "(KHTML, like Gecko) Chrome/151.0 Mobile Safari/537.36"))
    try:
        for pid, p in piezas.items():
            tipo = p.get("tipo", "")
            destino = carpeta / f"{pid}.jpg"
            if destino.exists() and pid in manifest:
                reporte.piezas[pid] = tipo
                continue
            try:
                if tipo in ("lugar", "persona"):
                    meta = bajar_wikimedia(p, destino)
                elif tipo == "ficha":
                    dibujar_ficha(p.get("titulo", ""), p.get("renglones", []),
                                  p.get("fuente", ""), destino)
                    meta = {"fuente": p.get("fuente", "")}
                elif tipo in ("documento", "prensa") and p.get("url"):
                    meta = (pagina_pdf(p, destino) if _es_pdf(p["url"])
                            else capturar_titular(ctx, p, destino, claves))
                else:
                    raise ValueError(f"tipo desconocido o sin url: {tipo!r}")
                manifest[pid] = {"tipo": tipo, **meta}
                reporte.piezas[pid] = tipo
            except Exception as exc:  # noqa: BLE001 -- una pieza caída no tira el resto
                destino.unlink(missing_ok=True)
                reporte.fallidas[pid] = str(exc)[:200]
                logger.warning("%s: pieza %s (%s) falló: %s", slug, pid, tipo, exc)
    finally:
        if nav is not None:
            nav.close()
        if pw is not None:
            pw.stop()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    _asignar(guion, carpeta, base, reporte)
    ruta_guion.write_text(json.dumps(guion, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("%s: %s", slug, reporte.resumen())
    return reporte


def _asignar(guion: dict, carpeta: Path, base: Path, reporte: Reporte) -> None:
    manuales = base / "imagenes_manuales"
    manuales.mkdir(exist_ok=True)
    for viejo in manuales.glob("*"):
        viejo.unlink()
    listas = [p["id"] for p in guion.get("evidencia", []) if p.get("id") in reporte.piezas]
    ultimas: list[str] = listas[:3]
    for plano in guion.get("planos", []):
        if plano.get("seccion") == "identidad_cierre":
            continue  # el cartel del canal lo pone el bot (pipeline._apply_cierre)
        visual = plano.setdefault("visual", {})
        propias = [e for e in visual.get("evidencia", []) if e in reporte.piezas]
        if not propias:
            # Sin pieza propia (se cayó o Claude no asignó): se reusa la del
            # plano anterior. Repetir evidencia real es mejor que inventar.
            propias = ultimas or listas
            if not propias:
                continue
            reporte.planos_prestados.append(plano["id"])
        ultimas = propias
        for n, pid in enumerate(islice(cycle(propias), TOMAS_POR_PLANO), start=1):
            Image.open(carpeta / f"{pid}.jpg").convert("RGB").save(
                manuales / f"{plano['id']}_1_{n}.jpg", quality=92)
        if any(reporte.piezas[pid] in CON_TEXTO for pid in propias):
            visual["motion"] = "calm"
