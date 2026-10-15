"""Migra los guiones 2-5 del lote del 26/08/2026 al formato de apertura
nuevo (ver CLAUDE.md de illustrated-narrator):

  - se elimina el plano `identidad_apertura` (logo + "Dato mata gato")
  - los planos se renumeran, el hook pasa a ser p00
  - la narracion de p00 EMPIEZA con el dato mas fuerte del caso

El dato de apertura de cada caso NO es inventado: sale de un plano posterior
del propio guion (normalmente el `bucle_abierto`), adelantado al arranque.
Se conserva el `texto_en_pantalla` original del hook (lugar · fecha), que
complementa la frase hablada en vez de repetirla.

El primer video del lote (guion-poquianchis) NO se toca: ya esta publicado.

    python tools/migrar_lote_27ago.py [--dry-run]
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from migrar_guion_sin_apertura import migrar  # noqa: E402

ANDROID_IN = Path(r"C:\Android_in")

# slug -> frase de apertura (el dato mas fuerte, tomado del propio guion)
APERTURAS = {
    "guion-campo-algodonero": (
        "Ocho mujeres y niñas aparecieron muertas en un campo algodonero de Ciudad Juárez."
    ),
    "guion-ingrid-escamilla": (
        "Un periódico puso en su portada las fotografías de la escena del crimen "
        "de una mujer asesinada."
    ),
    "guion-masacre-camargo": (
        "Encontraron una camioneta incendiada con diecinueve cuerpos adentro. "
        "Los primeros señalados no fueron un cartel: fueron policías del estado."
    ),
    "guion-guarderia-abc": (
        "Cuarenta y nueve niños murieron en una guardería. Más de una década después, "
        "casi ningún responsable había pisado la cárcel."
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="solo muestra, no escribe")
    args = parser.parse_args()

    for slug, apertura in APERTURAS.items():
        path = ANDROID_IN / slug / "guion.json"
        guion = json.loads(path.read_text(encoding="utf-8"))

        # Guardar la narracion del hook ANTES de migrar: migrar() le antepone
        # el titulo, y acá queremos el dato fuerte en su lugar.
        hook_original = next(
            p for p in guion["planos"] if p.get("seccion") != "identidad_apertura"
        )["narracion"]

        migrado, _ = migrar(guion)
        p00 = migrado["planos"][0]
        p00["narracion"] = f"{apertura} {hook_original}"

        print("=" * 78)
        print(slug)
        print("  p00:", p00["narracion"][:150], "...")
        print("  cartel:", p00.get("texto_en_pantalla"))
        print("  planos:", len(migrado["planos"]), "| cierre:", migrado["planos"][-1]["seccion"])

        if args.dry_run:
            continue

        shutil.copy(path, path.with_suffix(".json.bak"))
        path.write_text(
            json.dumps(migrado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    if args.dry_run:
        print("\n(dry-run: no se escribio nada)")


if __name__ == "__main__":
    main()
