"""Convención de nombres para imágenes que el usuario manda antes de
/generar: 'p1 [inicio] [1]' -> plano p01, posición inicio, índice 1.
El índice coincide con el que usa el mecanismo elegido_N.* de
illustrated-narrator (ver CLAUDE.md)."""

import re
from dataclasses import dataclass

_PATTERN = re.compile(
    r"p\s*(\d+)\s*\[\s*(inicio|medio|fin)\s*\]\s*\[\s*(\d+)\s*\]", re.IGNORECASE
)


@dataclass(frozen=True)
class ImageSpec:
    plano_id: str  # "p01"
    posicion: str  # "inicio" | "medio" | "fin"
    indice: int


def parse(caption: str) -> ImageSpec | None:
    match = _PATTERN.search(caption or "")
    if not match:
        return None
    numero, posicion, indice = match.groups()
    plano_id = f"p{int(numero):02d}"
    return ImageSpec(plano_id=plano_id, posicion=posicion.lower(), indice=int(indice))


def filename_for(spec: ImageSpec, suffix: str) -> str:
    return f"{spec.plano_id}_{spec.posicion}_{spec.indice}{suffix}"
