"""Canales (15/11/2026): qué es de Dato Mata Gato y qué es de papasia.

El motor es uno solo (voz, render, fábrica, IA gratis). Lo que se separa por
canal es lo que antes se cruzaba con dos bots corriendo el mismo código:

- los comandos: cada bot ofrece solo los de su canal;
- el estado del chat y el log: `data/` para Dato Mata Gato, `data/<canal>/`
  para los demás. Los dos bots le escriben al MISMO chat de Javier, así que con
  un solo `sessions.json` compartían conversación con Claude y bandera de
  "generando", y el arranque de uno le apagaba la bandera al otro;
- los avisos de la fábrica: un lote de papasia avisa por el bot de papasia
  aunque lo retome el vigilante de Windows, que arranca con el `.env` base.

El canal vacío ("") es Dato Mata Gato. Este módulo no lee variables de entorno
al importarse, para poder usarlo ANTES de cargar los `.env`.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

RAIZ_BOT = Path(__file__).resolve().parents[2]
VARIABLE = "CANAL_PERFIL"

# Carpetas (15/11/2026): cada canal tiene su entrada y su salida. Dato Mata Gato
# sigue en la raíz (`C:\Android_in`); los demás, en `C:\Android_in\<canal>`, con
# la misma forma por dentro: `<slug>\guion.json`, `fabrica\<lote>`, `lotes\<lote>`.
# Los scripts de render de illustrated-narrator leen la variable ANDROID_IN.
ENTRADA_BASE = Path(r"C:\Android_in")
VARIABLE_ENTRADA = "ANDROID_IN"

NOMBRES = {"": "Dato Mata Gato", "papasia": "papasia"}

# Formatos de la fábrica que NO son de Dato Mata Gato. Lo que no esté aquí es
# del canal base.
_CANAL_DE_FORMATO = {"papasia": "papasia"}


def actual() -> str:
    """El canal de este proceso ("" = Dato Mata Gato)."""
    return os.getenv(VARIABLE, "")


def nombre(canal: str | None = None) -> str:
    canal = actual() if canal is None else canal
    return NOMBRES.get(canal, canal)


def ruta_perfil(canal: str) -> Path:
    return RAIZ_BOT / f".env.{canal}"


def cargar(canal: str) -> str:
    """Carga `.env.<canal>` ENCIMA del entorno y deja marcado el canal del
    proceso (los procesos hijos lo heredan). Con "" no hace nada."""
    if not canal:
        return ""
    ruta = ruta_perfil(canal)
    if not ruta.exists():
        raise SystemExit(f"No existe el perfil {ruta}")
    load_dotenv(ruta, override=True)
    os.environ[VARIABLE] = canal
    # Para los procesos hijos que no son de este paquete (render 3D, portada).
    os.environ[VARIABLE_ENTRADA] = str(entrada(canal))
    return canal


def de_argv(argv: list[str] | None = None) -> str:
    """El canal que pide `--perfil <nombre>` en la línea de comandos, o ""."""
    argv = sys.argv if argv is None else argv
    if "--perfil" not in argv:
        return ""
    i = argv.index("--perfil")
    canal = argv[i + 1] if i + 1 < len(argv) else ""
    if not canal or canal.startswith("-"):
        raise SystemExit("Uso: --perfil <nombre> (p. ej. --perfil papasia)")
    return canal


def de_formato(formato: str | None) -> str:
    """De qué canal es un formato de la fábrica."""
    return _CANAL_DE_FORMATO.get(formato or "", "")


def de_estado(estado: dict) -> str:
    """De qué canal es un lote de la fábrica (por su `estado.json`)."""
    return estado.get("canal") or de_formato(estado.get("formato"))


def es_mio(estado: dict) -> bool:
    return de_estado(estado) == actual()


def canales() -> list[str]:
    """Todos los canales, el base primero."""
    return list(NOMBRES)


def entrada(canal: str | None = None) -> Path:
    """La carpeta de entrada y salida de un canal (guiones, fábrica, lotes)."""
    canal = actual() if canal is None else canal
    return ENTRADA_BASE / canal if canal else ENTRADA_BASE


def raiz_fabrica(canal: str | None = None) -> Path:
    """Donde viven los `estado.json` de los lotes de un canal."""
    return entrada(canal) / "fabrica"


def data_dir() -> Path:
    """Dónde vive el estado del bot de este canal (sesiones del chat, log)."""
    canal = actual()
    return RAIZ_BOT / "data" / canal if canal else RAIZ_BOT / "data"
