"""Alta de preguntas en el banco de trivias, con su registro legible.

El banco (JSON) es lo que lee el generador. Al lado se escribe un txt con lo
aprobado y su verificación, para poder repasar de dónde salió cada dato sin
abrir el JSON.

Al banco SOLO entra lo aprobado: es lo que garantiza que el generador nunca
arme un video con un dato que nadie miró.
"""

import json
import unicodedata
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
BANCO_PATH = RAIZ / "data" / "banco_preguntas.json"
REGISTRO_PATH = RAIZ / "data" / "preguntas_aprobadas.txt"

DIFICULTADES = ("facil", "media", "dificil")


def _sin_acentos(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))


def clave_tema(nombre: str) -> str:
    return _sin_acentos(nombre.strip().lower()).replace(" ", "-")


def normalizar(q: dict) -> dict | None:
    """Una propuesta de Claude en la forma que espera el banco, o None si le
    falta algo esencial."""
    pregunta = (q.get("pregunta") or "").strip()
    respuesta = (q.get("respuesta") or "").strip()
    tema = (q.get("tema") or "").strip()
    dif = _sin_acentos((q.get("dificultad") or "").strip().lower())
    if not (pregunta and respuesta and tema and dif in DIFICULTADES):
        return None
    return {
        "tema": tema,
        "dificultad": dif,
        "pregunta": pregunta,
        "respuesta": respuesta,
        "dato_extra": (q.get("dato_extra") or "").strip(),
        "texto_pregunta": (q.get("texto_pregunta") or pregunta).strip(),
        "texto_respuesta": (q.get("texto_respuesta") or respuesta.upper()).strip(),
        "verificacion": (q.get("verificacion") or "").strip(),
        "busqueda_pregunta": (q.get("busqueda_pregunta") or "").strip(),
        "busqueda_respuesta": (q.get("busqueda_respuesta") or "").strip(),
    }


def agregar(preguntas: list[dict], banco_path: Path = BANCO_PATH,
            registro_path: Path = REGISTRO_PATH) -> int:
    """Mete las preguntas al banco y las anota en el registro. Devuelve cuántas."""
    datos = json.loads(banco_path.read_text(encoding="utf-8")) if banco_path.exists() else {}
    temas = datos.setdefault("temas", {})
    usados = {q["id"] for e in temas.values() for q in e.get("preguntas", [])}

    lineas, n = [], 0
    for cruda in preguntas:
        q = normalizar(cruda)
        if q is None:
            continue
        clave = clave_tema(q["tema"])
        entrada = temas.setdefault(clave, {"nombre": q["tema"], "preguntas": []})
        # El id lleva tema y dificultad: dos preguntas del mismo par no se pisan.
        i = sum(1 for x in entrada["preguntas"] if x.get("dificultad") == q["dificultad"]) + 1
        qid = f"{clave}-{q['dificultad']}-{i:02d}"
        while qid in usados:
            i += 1
            qid = f"{clave}-{q['dificultad']}-{i:02d}"
        usados.add(qid)

        entrada["preguntas"].append({
            "id": qid,
            "dificultad": q["dificultad"],
            "pregunta": q["pregunta"],
            "respuesta": q["respuesta"],
            "dato_extra": q["dato_extra"],
            "texto_pregunta": q["texto_pregunta"],
            "texto_respuesta": q["texto_respuesta"],
            "verificacion": q["verificacion"],
            "pregunta_visual": {"descripcion": "", "prompt_ia": "",
                                "busqueda_medios": q["busqueda_pregunta"]},
            "respuesta_visual": {"descripcion": "", "prompt_ia": "",
                                 "busqueda_medios": q["busqueda_respuesta"]},
        })
        lineas.append(
            f"[{qid}] ({q['dificultad']})\n"
            f"  P: {q['pregunta']}\n"
            f"  R: {q['respuesta']}"
            + (f" — {q['dato_extra']}" if q["dato_extra"] else "")
            + (f"\n  Verificación: {q['verificacion']}" if q["verificacion"] else "")
        )
        n += 1

    if n:
        banco_path.parent.mkdir(parents=True, exist_ok=True)
        banco_path.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
        with registro_path.open("a", encoding="utf-8") as f:
            f.write(f"\n=== {datetime.now():%d/%m/%Y %H:%M} — {n} aprobada(s) ===\n")
            f.write("\n".join(lineas) + "\n")
    return n
