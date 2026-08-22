"""CLI para subir un video ya generado a Drive -- pensado para que Claude
lo invoque cuando toma una escalada del pipeline (reemplaza el viejo "cp a
Android_out" que se hacía a mano). Uso:
    C:\\dato-mata-gato-bot\\.venv\\Scripts\\python.exe -m dato_mata_gato_bot.upload_cli <slug>
"""

import sys

from dato_mata_gato_bot import pipeline


def main() -> None:
    if len(sys.argv) != 2:
        print("Uso: python -m dato_mata_gato_bot.upload_cli <slug>")
        raise SystemExit(1)
    try:
        detalle = pipeline._upload_to_drive(sys.argv[1])
    except Exception as exc:  # noqa: BLE001 — se reporta tal cual en la terminal
        print(f"Falló la subida a Drive: {exc}")
        raise SystemExit(1) from exc
    print(f"Subido: {detalle}")


if __name__ == "__main__":
    main()
