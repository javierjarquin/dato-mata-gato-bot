"""Mueve lo de papasia a la carpeta de su canal (15/11/2026).

Hasta hoy todo vivía revuelto en C:\\Android_in. Cada canal tiene ahora su
carpeta, con la misma forma por dentro (ver `canal.entrada`):

    C:\\Android_in\\guion-papasia-*         ->  C:\\Android_in\\papasia\\guion-papasia-*
    C:\\Android_in\\lotes\\papasia-*         ->  C:\\Android_in\\papasia\\lotes\\papasia-*
    C:\\Android_in\\fabrica\\papasia-*       ->  C:\\Android_in\\papasia\\fabrica\\papasia-*
    C:\\Android_in\\fabrica\\papasia_tokens.csv -> C:\\Android_in\\papasia\\fabrica\\

    python tools\\migrar_carpetas_papasia.py            # solo dice qué movería
    python tools\\migrar_carpetas_papasia.py --aplicar  # lo mueve

Solo mueve: no borra ni pisa nada. Si un destino ya existe, o hay un lote de
papasia sin terminar, se detiene sin tocar nada. Se puede correr dos veces.
"""

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dato_mata_gato_bot import canal  # noqa: E402

CANAL = "papasia"


def movimientos(base: Path, destino: Path) -> list[tuple[Path, Path]]:
    pares = [(d, destino / d.name) for d in sorted(base.glob(f"guion-{CANAL}-*")) if d.is_dir()]
    for sub in ("lotes", "fabrica"):
        pares += [(d, destino / sub / d.name) for d in sorted((base / sub).glob(f"{CANAL}-*")) if d.is_dir()]
    bitacora = base / "fabrica" / f"{CANAL}_tokens.csv"
    if bitacora.exists():
        pares.append((bitacora, destino / "fabrica" / bitacora.name))
    return pares


def problemas(pares: list[tuple[Path, Path]]) -> list[str]:
    out = [f"ya existe {b}" for _, b in pares if b.exists()]
    for a, _ in pares:
        estado = a / "estado.json"
        if a.parent.name == "fabrica" and estado.exists():
            if not json.loads(estado.read_text(encoding="utf-8")).get("terminado"):
                out.append(f"el lote {a.name} no ha terminado: espera o detenlo con /pararfabrica")
    return out


def corregir_estado(ruta: Path, base: Path, destino: Path) -> None:
    """El estado guarda la carpeta de los videos con la ruta completa."""
    estado = json.loads(ruta.read_text(encoding="utf-8"))
    vieja = Path(estado.get("carpeta_videos", ""))
    if vieja.parent == base / "lotes":
        estado["carpeta_videos"] = str(destino / "lotes" / vieja.name)
    estado.setdefault("canal", CANAL)
    ruta.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure") and sys.stdout:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    aplicar = "--aplicar" in sys.argv
    base, destino = canal.ENTRADA_BASE, canal.entrada(CANAL)
    pares = movimientos(base, destino)
    if not pares:
        print(f"Nada que mover: no queda nada de {CANAL} en {base}.")
        return 0
    if malos := problemas(pares):
        print("No muevo nada:\n" + "\n".join(f"- {m}" for m in malos))
        return 1
    for a, b in pares:
        print(f"{'muevo' if aplicar else 'movería'}  {a}  ->  {b}")
        if aplicar:
            b.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(a), str(b))
            if (b / "estado.json").exists():
                corregir_estado(b / "estado.json", base, destino)
    print(f"\n{len(pares)} " + ("movidos." if aplicar else "por mover. Para hacerlo: --aplicar"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
