"""Manejo de la fábrica de lotes grandes (ver src/dato_mata_gato_bot/fabrica.py).

    python tools\\fabrica.py crear <lote> <cantidad>   # p. ej. crear mil-1 1000
    python tools\\fabrica.py ciclo [<lote>]            # trabaja; sin lote, todas las no terminadas
    python tools\\fabrica.py estado [<lote>]
    python tools\\fabrica.py instalar                  # vigilante en el Programador de tareas
    python tools\\fabrica.py desinstalar

El vigilante corre `ciclo` cada 15 minutos, oculto
(pythonw). Si ya hay un ciclo vivo no hace nada (latido en disco), así que
la tarea se puede disparar las veces que sea.
"""

import logging
import subprocess
import sys
from pathlib import Path

RAIZ_BOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_BOT / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(RAIZ_BOT / ".env")

from dato_mata_gato_bot import fabrica  # noqa: E402

TAREA = "DatoMataGato Fabrica"


def _log(lote: str | None = None) -> None:
    destino = (fabrica.RAIZ / lote / "fabrica.log") if lote else (fabrica.RAIZ / "fabrica.log")
    destino.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=destino, level=logging.INFO, encoding="utf-8",
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def _lotes_activos() -> list[str]:
    if not fabrica.RAIZ.exists():
        return []
    activos = []
    for d in sorted(fabrica.RAIZ.iterdir()):
        try:
            if (d / "estado.json").exists() and not fabrica.leer(d.name)["terminado"]:
                activos.append(d.name)
        except (OSError, ValueError, KeyError):
            continue
    return activos


def main() -> int:
    if hasattr(sys.stdout, "reconfigure") and sys.stdout:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    cmd = args[0]
    if cmd == "crear":
        lote, n = args[1], int(args[2])
        formato = args[3] if len(args) > 3 else "cercania"
        estado = fabrica.crear(lote, n, formato)
        print(f"Fábrica '{lote}' creada: {n} videos, fórmula {formato} -> {estado['carpeta_videos']}")
        return 0
    if cmd == "estado":
        for lote in (args[1:] or _lotes_activos()):
            print(fabrica.resumen(fabrica.leer(lote)))
        return 0
    if cmd == "ciclo":
        lotes = args[1:] or _lotes_activos()
        _log(lotes[0] if len(lotes) == 1 else None)
        for lote in lotes:
            motivo = fabrica.ciclo(lote)
            logging.info("ciclo %s: %s", lote, motivo)
            print(f"{lote}: {motivo}")
            if motivo == "ya hay un ciclo corriendo":
                continue
            if motivo != "terminado":
                break  # una fábrica a la vez: comparten VoiceStudio
        return 0
    if cmd == "instalar":
        pyw = Path(sys.executable).with_name("pythonw.exe")
        accion = f'"{pyw}" "{Path(__file__).resolve()}" ciclo'
        # Solo la de cada 15 min: la de "al iniciar sesión" pide administrador
        # (Acceso denegado, 12/10/2026), y esta también vuelve a correr sola
        # tras un reinicio en cuanto Javier inicia sesión.
        r = subprocess.run(["schtasks", "/create", "/f", "/tn", TAREA, "/tr", accion,
                            "/sc", "minute", "/mo", "15"], capture_output=True, text=True)
        print(TAREA, "->", (r.stdout or r.stderr).strip())
        return 0
    if cmd == "desinstalar":
        r = subprocess.run(["schtasks", "/delete", "/f", "/tn", TAREA], capture_output=True, text=True)
        print(TAREA, "->", (r.stdout or r.stderr).strip())
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
