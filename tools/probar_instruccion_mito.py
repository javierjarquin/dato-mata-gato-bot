"""Corre INSTRUCCION_MITO de verdad contra Claude y valida lo que escribe.

Los tests fijan que la instrucción DIGA lo correcto; esto mide si, leída por
Claude, produce un guion que cumple la fórmula. Usa una sesión nueva, así no
ensucia la conversación del chat del usuario.

Uso:  python tools/probar_instruccion_mito.py [cantidad]
"""

import json
import sys
import uuid
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "tools"))
sys.path.insert(0, r"C:\illustrated-narrator\src")

from dato_mata_gato_bot import bot, formatos  # noqa: E402
from dato_mata_gato_bot.claude_runner import run_turn  # noqa: E402
from illustrated_narrator.domain.services.script_loader import load_guion  # noqa: E402
from illustrated_narrator.domain.services.sfx_taxonomy import EVENTOS, sfx_kinds  # noqa: E402
from medir_tono import VOSEO, analizar  # noqa: E402

ANDROID_IN = Path(r"C:\Android_in")


def validar(slug: str) -> list[str]:
    """Lo que el guion hace MAL. Lista vacía = cumple."""
    ruta = ANDROID_IN / slug / "guion.json"
    malo = []
    if not ruta.exists():
        return [f"no escribió {ruta}"]
    crudo = json.loads(ruta.read_text(encoding="utf-8"))
    try:
        load_guion(ruta)
    except Exception as exc:  # noqa: BLE001
        malo.append(f"el narrador no lo puede leer: {exc}")
    planos = crudo.get("planos", [])
    if crudo.get("formato") != "mito":
        malo.append("falta \"formato\": \"mito\"")
    if len(crudo.get("titulo", "")) > 30:
        malo.append(f"título de {len(crudo['titulo'])} caracteres")
    if len(crudo.get("gancho", "")) > 35:
        malo.append(f"gancho de {len(crudo['gancho'])} caracteres")
    if not crudo.get("fuentes"):
        malo.append("sin fuentes")
    senales = [p for p in planos if str(p.get("seccion", "")).startswith("senal")]
    if not 2 <= len(senales) <= 4:
        malo.append(f"{len(senales)} señales (van de 2 a 4)")
    for p in senales:
        # Misma lectura que el pipeline: en el plano o dentro de "audio".
        if not (p.get("pausa_despues_seg") or (p.get("audio") or {}).get("pausa_despues_seg")):
            malo.append(f"{p['id']}: señal sin pausa para su sonido")
        sfx = (p.get("audio", {}).get("sfx") or "").lower()
        # Una señal puede ser un silencio ("los pájaros se cortan"): es válido.
        es_silencio = any(v in sfx for v in ("callan", "calla", "se corta", "se detiene",
                                              "dejan de", "se apaga"))
        if not [k for k in sfx_kinds(sfx) if k in EVENTOS] and not es_silencio:
            malo.append(f"{p['id']}: la señal no pide un sonido que exista "
                        f"({p.get('audio', {}).get('sfx')!r})")
    if not any(p.get("seccion") == "identidad_cierre" for p in planos):
        malo.append("sin plano de identidad_cierre")
    for p in planos:
        v = p.get("visual", {})
        if v.get("busqueda_medios"):
            malo.append(f"{p['id']}: busqueda_medios no vacía")
        if "eyes" in (v.get("prompt_ia") or "").lower():
            malo.append(f"{p['id']}: prompt con 'eyes' (arrastra una cara)")
    voseo = sorted({m.group(0) for p in planos for m in VOSEO.finditer(p.get("narracion", ""))})
    if voseo:
        malo.append(f"voseo: {', '.join(voseo)}")
    tono = analizar(slug)
    if tono and tono["frase_larga"] > 20:
        malo.append(f"una frase de {tono['frase_larga']} palabras")
    return malo


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    antes = {d.name for d in ANDROID_IN.glob("mito-*")}
    print(f"pidiendo {n} mito(s) a Claude (sesión nueva)...", flush=True)
    r = run_turn(str(uuid.uuid4()), bot.INSTRUCCION_MITO.format(n=n), True)
    if not r.ok:
        raise SystemExit(f"Claude falló: {r.text[:1500]}")
    guiones = bot._parse_lote_response(r.text) or []
    bot._asegurar_formato_mito(g.get("slug") for g in guiones)
    nuevos = sorted({d.name for d in ANDROID_IN.glob("mito-*")} - antes)
    print(f"\nrespondió {len(guiones)} guion(es); carpetas nuevas: {nuevos}\n")
    for g in guiones:
        slug = g.get("slug", "?")
        malo = validar(slug)
        print(f"{slug}  |  {g.get('titulo')}")
        print(f"   {g.get('resumen_hechos', '')}")
        print("   CUMPLE LA FÓRMULA" if not malo else "   PROBLEMAS:\n     - " + "\n     - ".join(malo))
        print()


if __name__ == "__main__":
    main()
