"""CLI para subir un video ya generado a Drive -- pensado para que Claude
lo invoque cuando toma una escalada del pipeline (reemplaza el viejo "cp a
Android_out" que se hacía a mano). Uso:
    C:\\dato-mata-gato-bot\\.venv\\Scripts\\python.exe -m dato_mata_gato_bot.upload_cli <slug>
"""

import sys

from dotenv import load_dotenv

# Antes del import de pipeline: este script nunca llamaba load_dotenv(),
# así que GOOGLE_DRIVE_FOLDER_ID (y cualquier otra variable de .env) nunca
# llegaba al proceso -- confirmado en una corrida real: "Falta
# GOOGLE_DRIVE_FOLDER_ID en el .env del bot" pese a que el .env sí lo tiene.
load_dotenv()

from dato_mata_gato_bot import pipeline  # noqa: E402


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
