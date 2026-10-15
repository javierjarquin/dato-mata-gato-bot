"""Carga preguntas nuevas al banco desde una planilla CSV.

El banco es lo unico que el generador de trivias NO puede producir solo: las
preguntas las verifica una persona antes de entrar. Esto es para poder cargarlas
de a muchas sin editar el JSON a mano.

    python tools/agregar_preguntas.py --csv preguntas.csv
    python tools/agregar_preguntas.py --plantilla preguntas.csv   (crea el modelo)

Columnas (las cuatro primeras son obligatorias):
    tema, dificultad, pregunta, respuesta,
    dato_extra, texto_pregunta, texto_respuesta, verificacion,
    busqueda_pregunta, busqueda_respuesta, nombre_tema
"""

import argparse
import csv
import json
import sys
import unicodedata
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BANCO = Path(__file__).resolve().parents[1] / "data" / "banco_preguntas.json"
COLUMNAS = ["tema", "dificultad", "pregunta", "respuesta", "dato_extra",
            "texto_pregunta", "texto_respuesta", "verificacion",
            "busqueda_pregunta", "busqueda_respuesta", "nombre_tema"]
DIFICULTADES = {"facil", "media", "dificil"}


def _sin_acentos(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))


def _clave_tema(nombre: str) -> str:
    return _sin_acentos(nombre.strip().lower()).replace(" ", "-")


def plantilla(destino: Path) -> None:
    with destino.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS)
        w.writeheader()
        w.writerow({
            "tema": "volcanes", "dificultad": "facil",
            "pregunta": "¿Cuál es el volcán más activo de México?",
            "respuesta": "El Popocatépetl",
            "dato_extra": "Lleva en erupción continua desde 1994.",
            "texto_pregunta": "¿El volcán más activo de México?",
            "texto_respuesta": "POPOCATÉPETL",
            "verificacion": "Fuente y por qué el dato es correcto. Se arrastra al guion.",
            "busqueda_pregunta": "volcano crater smoke aerial",
            "busqueda_respuesta": "snow capped volcano plume",
            "nombre_tema": "volcanes",
        })
    print(f"Plantilla escrita en {destino}. Llenala y corré --csv.")


def cargar(csv_path: Path, banco_path: Path) -> tuple[int, list[str]]:
    datos = json.loads(banco_path.read_text(encoding="utf-8")) if banco_path.exists() else {}
    temas = datos.setdefault("temas", {})
    ya = {q["id"] for e in temas.values() for q in e.get("preguntas", [])}

    agregadas, problemas = 0, []
    # utf-8-sig: Excel guarda los CSV con BOM y sin esto la primera columna
    # sale llamandose "﻿tema" y no matchea nunca.
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        for i, fila in enumerate(csv.DictReader(f), start=2):
            fila = {k.strip(): (v or "").strip() for k, v in fila.items() if k}
            faltan = [c for c in ("tema", "dificultad", "pregunta", "respuesta") if not fila.get(c)]
            if faltan:
                problemas.append(f"fila {i}: falta {', '.join(faltan)}")
                continue
            dif = _sin_acentos(fila["dificultad"].lower())
            if dif not in DIFICULTADES:
                problemas.append(f"fila {i}: dificultad '{fila['dificultad']}' (usá facil/media/dificil)")
                continue

            clave = _clave_tema(fila["tema"])
            entrada = temas.setdefault(clave, {"nombre": fila.get("nombre_tema") or fila["tema"], "preguntas": []})
            # El id lleva la dificultad y un correlativo: dos preguntas del
            # mismo tema y dificultad no se pisan.
            n = sum(1 for q in entrada["preguntas"] if q.get("dificultad") == dif) + 1
            qid = f"{clave}-{dif}-{n:02d}"
            while qid in ya:
                n += 1
                qid = f"{clave}-{dif}-{n:02d}"
            ya.add(qid)

            entrada["preguntas"].append({
                "id": qid,
                "dificultad": dif,
                "pregunta": fila["pregunta"],
                "respuesta": fila["respuesta"],
                "dato_extra": fila.get("dato_extra", ""),
                "texto_pregunta": fila.get("texto_pregunta") or fila["pregunta"],
                "texto_respuesta": fila.get("texto_respuesta") or fila["respuesta"].upper(),
                "verificacion": fila.get("verificacion", ""),
                "pregunta_visual": {"descripcion": "", "prompt_ia": "",
                                    "busqueda_medios": fila.get("busqueda_pregunta", "")},
                "respuesta_visual": {"descripcion": "", "prompt_ia": "",
                                     "busqueda_medios": fila.get("busqueda_respuesta", "")},
            })
            agregadas += 1

    if agregadas:
        banco_path.parent.mkdir(parents=True, exist_ok=True)
        banco_path.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    return agregadas, problemas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path)
    ap.add_argument("--plantilla", type=Path)
    ap.add_argument("--banco", type=Path, default=BANCO)
    args = ap.parse_args()

    if args.plantilla:
        plantilla(args.plantilla)
        return 0
    if not args.csv:
        ap.error("pasá --csv <archivo> o --plantilla <archivo>")
    if not args.csv.exists():
        print(f"No existe {args.csv}")
        return 1

    agregadas, problemas = cargar(args.csv, args.banco)
    print(f"{agregadas} pregunta(s) agregadas al banco")
    for p in problemas:
        print(f"  OJO: {p}")
    return 1 if problemas and not agregadas else 0


if __name__ == "__main__":
    sys.exit(main())
