"""Migra un guion.json al formato de apertura nuevo (27/08/2026).

Antes: p00 era un plano `identidad_apertura` (logo del canal sobre negro) y
el contenido real empezaba en p01. Ahora ese plano se elimina y el título
del caso se narra al arranque del primer plano de contenido, sobre imagen
real -- así el gancho se escucha desde el segundo cero. Ver CLAUDE.md de
illustrated-narrator.

Los planos se renumeran para que el primero de contenido quede como p00.
El plano de cierre (`identidad_cierre`) NO se toca.

    python tools/migrar_guion_sin_apertura.py <slug> [<slug> ...]
    python tools/migrar_guion_sin_apertura.py --salida <slug-destino> <slug-origen>
"""

import argparse
import json
import shutil
from pathlib import Path

ANDROID_IN = Path(r"C:\Android_in")


def migrar(guion: dict) -> tuple[dict, str]:
    """Devuelve (guion_migrado, mensaje). No muta el original."""
    guion = json.loads(json.dumps(guion))  # copia profunda
    planos = guion.get("planos", [])

    apertura = [p for p in planos if p.get("seccion") == "identidad_apertura"]
    if not apertura:
        return guion, "ya estaba en el formato nuevo (sin identidad_apertura)"

    titulo = (guion.get("titulo") or "").strip()
    if not titulo:
        raise ValueError("el guion no tiene 'titulo' -- no hay qué narrar al inicio")

    resto = [p for p in planos if p.get("seccion") != "identidad_apertura"]
    if not resto:
        raise ValueError("el guion se quedaría sin planos")

    primero = resto[0]
    # El título se dice tal cual y después arranca el hook. Se separa con un
    # punto y espacio para que Kokoro haga la pausa natural entre ambos.
    titulo_narrado = titulo if titulo.endswith((".", "?", "!", "…")) else titulo + "."
    primero["narracion"] = f"{titulo_narrado} {primero['narracion']}".strip()

    # Renumerar: el primer plano de contenido pasa a ser p00. Los ids son la
    # clave de los WAV (narracion/<id>.wav) y de media/<id>/, así que tienen
    # que quedar consistentes con el orden final.
    for i, p in enumerate(resto):
        p["id"] = f"p{i:02d}"

    guion["planos"] = resto

    identidad = guion.get("_schema", {}).get("identidad_canal")
    if isinstance(identidad, dict):
        identidad.pop("frase_apertura", None)
        identidad["regla"] = (
            "Solo frase_cierre es fija. El arranque ya no lleva plano de identidad: "
            "el titulo del caso se narra al inicio del primer plano de contenido."
        )

    return guion, f"apertura eliminada, titulo agregado al inicio de {resto[0]['id']}"


def _procesar(origen: Path, destino: Path) -> None:
    guion = json.loads(origen.read_text(encoding="utf-8"))
    migrado, msg = migrar(guion)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(migrado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{destino}: {msg}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slugs", nargs="+", help="slugs en C:\\Android_in a migrar")
    parser.add_argument(
        "--salida",
        help="slug destino (no pisa el original). Solo válido con UN slug de origen.",
    )
    args = parser.parse_args()

    if args.salida:
        if len(args.slugs) != 1:
            parser.error("--salida solo admite un slug de origen")
        _procesar(
            ANDROID_IN / args.slugs[0] / "guion.json",
            ANDROID_IN / args.salida / "guion.json",
        )
        return

    for slug in args.slugs:
        path = ANDROID_IN / slug / "guion.json"
        shutil.copy(path, path.with_suffix(".json.bak"))
        _procesar(path, path)


if __name__ == "__main__":
    main()
