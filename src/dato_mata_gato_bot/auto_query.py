"""Deriva palabras clave de búsqueda automáticamente a partir de un plano
del guion -- título del video + nombres propios de la narración. Puro
texto, sin red, sin Claude."""

import re

_PROPER_NOUN_RE = re.compile(
    r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){0,2}\b"
)
# Palabras que salen en mayúscula solo por ir al inicio de una oración,
# no porque sean nombres propios -- se descartan como candidato.
_STOPWORD_INICIO = {
    "El", "La", "Los", "Las", "Un", "Una", "Y", "Pero", "Con", "Su", "Sus",
    "En", "De", "Del", "Al", "Este", "Esta", "Ese", "Esa", "Cada", "Ahí",
    "Aquí", "Cuando", "Como", "Por", "Para", "Ya", "No", "Sí",
}


def extract_keywords(narracion: str, max_terminos: int = 2) -> list[str]:
    """Nombres propios (secuencias de palabras con mayúscula inicial) de
    una narración, en orden de aparición, sin repetidos."""
    candidatos = _PROPER_NOUN_RE.findall(narracion or "")
    vistos: list[str] = []
    for c in candidatos:
        primera_palabra = c.split()[0]
        if primera_palabra in _STOPWORD_INICIO:
            continue
        if c not in vistos:
            vistos.append(c)
    return vistos[:max_terminos]


def build_query(titulo_guion: str, narracion: str) -> str:
    terminos = extract_keywords(narracion)
    partes = ([titulo_guion] if titulo_guion else []) + terminos
    return " ".join(partes).strip()
