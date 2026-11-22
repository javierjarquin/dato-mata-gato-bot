"""Manejo de la fábrica de lotes grandes (ver src/dato_mata_gato_bot/fabrica.py).

    python tools\\fabrica.py crear <lote> <cantidad>   # p. ej. crear mil-1 1000
    python tools\\fabrica.py ciclo [<lote>]            # trabaja; sin lote, todas las no terminadas
    python tools\\fabrica.py estado [<lote>]
    python tools\\fabrica.py instalar                  # vigilante en el Programador de tareas
    python tools\\fabrica.py desinstalar
    python tools\\fabrica.py --perfil papasia ciclo <lote>   # un lote de otro canal

Un solo vigilante para los dos canales. Desde el 22/11/2026 trabaja un lote de
cada canal al mismo tiempo: los guiones en paralelo y la voz y el render
turnándose video por video (fabrica.tomar_maquina). El lote de papasia lo
corre un proceso hijo con `--perfil papasia`.

El vigilante corre `ciclo` cada 15 minutos, oculto
(pythonw). Si ya hay un ciclo vivo no hace nada (latido en disco), así que
la tarea se puede disparar las veces que sea.
"""

import json
import logging
import subprocess
import sys
import threading
from pathlib import Path

RAIZ_BOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_BOT / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(RAIZ_BOT / ".env")

from dato_mata_gato_bot import canal  # noqa: E402

# `--perfil papasia` (15/11/2026): el ciclo de un lote de otro canal corre con
# el perfil de ese canal encima, para que sus avisos salgan por SU bot. Antes de
# importar `fabrica`, por lo mismo que en bot.py.
canal.cargar(canal.de_argv())
if "--perfil" in sys.argv:
    _i = sys.argv.index("--perfil")
    del sys.argv[_i:_i + 2]

from dato_mata_gato_bot import fabrica  # noqa: E402

TAREA = "DatoMataGato Fabrica"


def _ciclo_de_otro_canal(lote: str, de_quien: str) -> str:
    """El vigilante de Windows arranca con el `.env` base. Un lote de otro canal
    lo trabaja un proceso hijo con `--perfil`: así el aviso de cada video sale
    por el bot de ese canal y no por el de Dato Mata Gato. Se espera a que
    termine, porque sigue yendo una fábrica a la vez (comparten VoiceStudio)."""
    r = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--perfil", de_quien,
                        "ciclo", lote],
                       cwd=str(RAIZ_BOT), capture_output=True, text=True, encoding="utf-8",
                       errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    for linea in reversed((r.stdout or "").splitlines()):
        if linea.startswith(f"{lote}: "):
            return linea[len(lote) + 2:]
    # Con pythonw el hijo puede no tener salida: lo que manda es el estado en disco.
    if _leer(lote, de_quien)["terminado"]:
        return "terminado"
    return f"el ciclo del canal {de_quien} salió con código {r.returncode}: {(r.stderr or '')[-300:]}"


def _ciclo_de_canal(de_quien: str, lotes: list[str]) -> None:
    """Los lotes de UN canal, uno tras otro (como siempre)."""
    for lote in lotes:
        try:
            if de_quien == canal.actual():
                motivo = fabrica.ciclo(lote)
            else:
                motivo = _ciclo_de_otro_canal(lote, de_quien)
        except Exception:  # noqa: BLE001
            logging.exception("ciclo %s", lote)
            break
        logging.info("ciclo %s: %s", lote, motivo)
        print(f"{lote}: {motivo}", flush=True)
        if motivo == "ya hay un ciclo corriendo":
            continue
        if motivo != "terminado":
            break


def _programar_en_zernio() -> None:
    """Para cada canal con calendario de publicación (tools/programar_zernio.py),
    los videos nuevos toman el siguiente lugar libre en Zernio. Lo corre el
    vigilante en cada vuelta (cada 15 min); sin videos nuevos no llama a Zernio.
    Un fallo aquí no detiene la fábrica."""
    py = Path(sys.executable).with_name("python.exe")
    for c in canal.canales():
        if not (canal.entrada(c) / "zernio_calendario.json").exists():
            continue
        nombre = c or "datomatagato"
        try:
            r = subprocess.run([str(py), str(Path(__file__).with_name("programar_zernio.py")),
                                "--canal", nombre, "--confirmar"],
                               cwd=str(RAIZ_BOT), capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=3600,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            resumen = [l for l in (r.stdout or "").splitlines() if l.startswith(("  subiendo", "  ✗", "  !"))]
            if resumen or r.returncode:
                logging.info("zernio %s (código %s): %s %s", nombre, r.returncode, " | ".join(resumen),
                             (r.stderr or "")[-300:])
        except Exception:  # noqa: BLE001
            logging.exception("zernio %s falló", nombre)


def _leer(lote: str, de_quien: str) -> dict:
    """El estado de un lote de cualquier canal (`fabrica.leer` solo ve los de este)."""
    ruta = canal.raiz_fabrica(de_quien) / lote / "estado.json"
    return json.loads(ruta.read_text(encoding="utf-8"))


def _canal_de(lote: str) -> str | None:
    """En la carpeta de qué canal vive un lote: primero este, luego los demás."""
    for c in [canal.actual()] + [c for c in canal.canales() if c != canal.actual()]:
        if (canal.raiz_fabrica(c) / lote / "estado.json").exists():
            return c
    return None


def _log(lote: str | None = None) -> None:
    # El log por lote solo si el lote es de este canal: el de otro canal lo
    # escribe su proceso hijo, en su carpeta.
    propio = lote and fabrica.ruta_estado(lote).exists()
    destino = (fabrica.RAIZ / lote / "fabrica.log") if propio else (fabrica.RAIZ / "fabrica.log")
    destino.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=destino, level=logging.INFO, encoding="utf-8",
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # httpx escribe la URL completa de cada consulta, y la de Gemini trae la API
    # key (la de Telegram, el token del bot): quedaban en claro en el log.
    logging.getLogger("httpx").setLevel(logging.WARNING)


def _lotes_activos() -> list[str]:
    """Los lotes sin terminar. El vigilante (canal base) ve los de todos los
    canales, porque va una fábrica a la vez; un proceso con `--perfil`, solo
    los suyos."""
    return [e["lote"] for e in fabrica.activas_de_todos()
            if not canal.actual() or e["canal"] == canal.actual()]


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
        if (de_quien := canal.de_formato(formato)) != canal.actual():
            print(f"El formato {formato} es del canal {canal.nombre(de_quien)}: "
                  + (f"agrega --perfil {de_quien}" if de_quien else "quita --perfil"))
            return 1
        estado = fabrica.crear(lote, n, formato)
        print(f"Fábrica '{lote}' creada: {n} videos, fórmula {formato} -> {estado['carpeta_videos']}")
        return 0
    if cmd == "estado":
        for lote in (args[1:] or _lotes_activos()):
            if (de_quien := _canal_de(lote)) is None:
                print(f"{lote}: no existe")
                continue
            print(fabrica.resumen(_leer(lote, de_quien)))
        return 0
    if cmd == "ciclo":
        lotes = args[1:] or _lotes_activos()
        _log(lotes[0] if len(lotes) == 1 else None)
        por_canal: dict[str, list[str]] = {}
        for lote in lotes:
            de_quien = _canal_de(lote)
            if de_quien is None:
                print(f"{lote}: no existe")
            elif de_quien == canal.actual() or not canal.actual():
                # un proceso de papasia no toca los lotes de Dato Mata Gato
                por_canal.setdefault(de_quien, []).append(lote)
        # Un lote por canal a la vez, y los dos canales al mismo tiempo
        # (22/11/2026): los guiones se escriben en paralelo y la máquina (voz y
        # render) se turna video por video (fabrica.tomar_maquina).
        hilos = [threading.Thread(target=_ciclo_de_canal, args=(c, ls)) for c, ls in por_canal.items()]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()
        if not canal.actual():
            _programar_en_zernio()
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
