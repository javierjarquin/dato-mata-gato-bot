"""Arma el banco de preguntas a partir de las trivias ya publicadas.

Las 27 trivias que hay en illustrated-narrator/projects comparten una sola
estructura (verificado: 27 de 27), asi que sus preguntas se pueden extraer sin
ambiguedad. Son preguntas que YA salieron al aire, o sea ya verificadas -- es
la semilla mas barata y mas confiable que hay para el banco.

    python tools/extraer_banco.py --out data/banco_preguntas.json
"""

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROYECTOS = Path(r"C:\illustrated-narrator\projects")

# Conectores fijos que el generador vuelve a poner solo: se quitan para que el
# banco guarde la pregunta y la respuesta limpias, no la frase armada.
_PREFIJOS_PREGUNTA = ("La fácil.", "La media.", "Y la que casi nadie saca.",
                      "La difícil.", "Y la imposible.")
_SUFIJOS_RESPUESTA = ("Vas una de tres.", "Si vas dos de dos, la que sigue duele.",
                      "Vas dos de tres.")
_DIFICULTADES = ("facil", "media", "dificil")


def _pelar(texto: str, fijos: tuple[str, ...]) -> str:
    t = (texto or "").strip()
    for f in fijos:
        if t.startswith(f):
            t = t[len(f):].strip()
        if t.endswith(f):
            t = t[: -len(f)].strip()
    return t


def _partir_respuesta(texto: str) -> tuple[str, str]:
    """Separa la respuesta corta del dato extra que a veces la acompaña.

    Se parte en el primer punto SOLO si lo de antes es corto: si no, una
    respuesta larga de una sola frase quedaría cortada al medio.
    """
    if "." not in texto:
        return texto, ""
    corte = texto.index(".")
    cabeza, cola = texto[:corte].strip(), texto[corte + 1:].strip()
    if not cola or len(cabeza) > 60:
        return texto, ""
    return cabeza, cola


def _tema_de(slug: str) -> str:
    # trivia-cuerpo-humano-01 -> cuerpo-humano
    m = re.match(r"trivia-(.+?)(?:-\d+)?$", slug)
    return m.group(1) if m else slug


def _sin_acentos(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))


def extraer(guion_path: Path) -> dict | None:
    g = json.loads(guion_path.read_text(encoding="utf-8"))
    planos = g.get("planos", [])
    secciones = [p.get("seccion") for p in planos]
    if secciones.count("pregunta") != 3 or secciones.count("respuesta") != 3:
        return None

    preguntas = [p for p in planos if p.get("seccion") == "pregunta"]
    respuestas = [p for p in planos if p.get("seccion") == "respuesta"]
    verificaciones = g.get("verificar_antes_de_publicar") or []
    slug = guion_path.parent.name
    salida = []
    for i, (q, a) in enumerate(zip(preguntas, respuestas)):
        texto_a, extra = _partir_respuesta(_pelar(a.get("narracion"), _SUFIJOS_RESPUESTA))
        vq, va = (q.get("visual") or {}), (a.get("visual") or {})
        salida.append({
            "id": f"{slug}-{i + 1}",
            "dificultad": _DIFICULTADES[i],
            "pregunta": _pelar(q.get("narracion"), _PREFIJOS_PREGUNTA),
            "respuesta": texto_a,
            "dato_extra": extra,
            "texto_pregunta": q.get("texto_grande") or "",
            "texto_respuesta": a.get("texto_grande") or "",
            # El respaldo factual de la pregunta. Va en el banco porque es lo
            # que permite re-verificarla sin volver a investigar el tema.
            "verificacion": verificaciones[i] if i < len(verificaciones) else "",
            "pregunta_visual": {
                "descripcion": vq.get("descripcion") or "",
                "prompt_ia": vq.get("prompt_ia") or "",
                "busqueda_medios": vq.get("busqueda_medios") or "",
            },
            "respuesta_visual": {
                "descripcion": va.get("descripcion") or "",
                "prompt_ia": va.get("prompt_ia") or "",
                "busqueda_medios": va.get("busqueda_medios") or "",
            },
        })
    return {
        "tema": _tema_de(slug),
        # Del gancho original, que SI lleva acentos: el slug no los tiene y
        # "geografia" sin tilde el TTS lo pronuncia mal.
        "nombre": _nombre_del_gancho(planos) or _tema_de(slug).replace("-", " "),
        "origen": slug,
        "preguntas": salida,
    }


def _nombre_del_gancho(planos: list) -> str:
    """'Tres preguntas de quimica, de facil a...' -> 'quimica' (con acentos)."""
    for p in planos:
        if p.get("seccion") == "hook_preguntas":
            m = re.search(r"[Tt]res preguntas de (.+?),", p.get("narracion") or "")
            if m:
                return m.group(1).strip()
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--proyectos", type=Path, default=PROYECTOS)
    args = ap.parse_args()

    temas: dict[str, list] = {}
    leidos = saltados = 0
    for guion in sorted(args.proyectos.glob("trivia-*/guion.json")):
        try:
            datos = extraer(guion)
        except Exception as exc:  # noqa: BLE001 -- un guion raro no corta la extraccion
            print(f"  salteado {guion.parent.name}: {exc}")
            saltados += 1
            continue
        if datos is None:
            saltados += 1
            continue
        leidos += 1
        entrada = temas.setdefault(datos["tema"], {"nombre": datos["nombre"], "preguntas": []})
        entrada["preguntas"].extend(datos["preguntas"])

    total = sum(len(v["preguntas"]) for v in temas.values())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps({"temas": temas}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"{leidos} trivias leidas, {saltados} salteadas")
    print(f"{len(temas)} temas, {total} preguntas -> {args.out}")
    for tema, v in sorted(temas.items(), key=lambda x: -len(x[1]["preguntas"])):
        print(f"  {tema:20} {len(v['preguntas']):2}  ({v['nombre']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
