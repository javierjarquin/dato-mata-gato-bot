"""IA gratis para quitarle carga a Claude (27/10/2026).

Medido el 22/10: cada guion gastaba de 0.7 a 5.3 M tokens, y casi todo era
investigar (30 a 60 WebSearch por guion, cada resultado releído en los pasos
que siguen). Lo que no pide la pluma de Claude se hace aquí:

- Gemini por la API (GEMINI_API_KEY del .env, capa gratis) para lo que pide
  criterio: escoger temas y sacar datos de una nota. El 27/10 la CLI `gemini`
  se colgó 9 min y acabó en 503; la API contestó en 1 a 23 s.
- Ollama local (qwen2.5-coder:7b en la RX 5500 XT, ~24 tok/s) solo como
  respaldo y para tareas mecánicas: su juicio en español es flojo (le dio 2/5
  a "sube 30 % el agua"). keep_alive=0 suelta la VRAM al terminar, porque la
  misma tarjeta la usan el render y MuseTalk.

Nada de aquí escribe guiones: eso sigue siendo de Claude.
"""

import json
import logging
import os
import time

import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Los 2.5 ya no se dan a cuentas nuevas (404 el 27/10/2026).
GEMINI_FUERTE = os.getenv("GEMINI_MODELO") or "gemini-3.8-flash"
GEMINI_RAPIDO = os.getenv("GEMINI_MODELO_RAPIDO") or "gemini-3.5-flash-lite"
OLLAMA_MODELO = os.getenv("OLLAMA_MODELO") or "qwen2.5-coder:7b"
OLLAMA_URL = os.getenv("OLLAMA_URL") or "http://localhost:11434"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"


# Respaldo cuando Gemini se queda sin cuota (27/10/2026): capas gratis con API
# compatible con la de OpenAI. Cada una entra solo si su llave está en el .env;
# el modelo se cambia con <NOMBRE>_MODELO. Perplexity y Grok (xAI) no tienen
# API gratis; Groq (con q) es otra empresa y sí.
# Solo las que no piden tarjeta (27/10/2026: Cerebras sí la pidió; SambaNova y
# Hugging Face fuera por dudosas o por dar casi nada).
RESPALDOS = [
    ("GROQ", "https://api.groq.com/openai/v1/chat/completions", "openai/gpt-oss-120b"),
    ("OPENROUTER", "https://openrouter.ai/api/v1/chat/completions", "nvidia/nemotron-3-ultra-550b-a55b:free"),
    ("MISTRAL", "https://api.mistral.ai/v1/chat/completions", "ministral-14b-latest"),  # small y medium: 429 en el plan gratis (27/10)
    # GitHub Models: token fino con SOLO el permiso models:read, no el de `gh`
    # (ese trae repo y workflow).
    ("GITHUB_MODELS", "https://models.github.ai/inference/chat/completions", "openai/gpt-4.1-mini"),
    ("NVIDIA", "https://integrate.api.nvidia.com/v1/chat/completions", "meta/llama-3.3-70b-instruct"),
    # Cloudflare pide además CLOUDFLARE_ACCOUNT_ID (va en la URL).
    ("CLOUDFLARE", "https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/v1/chat/completions",
     "@cf/meta/llama-3.3-70b-instruct-fp8-fast"),
]


# Qué modelos contestaron desde el último reiniciar_usados(): el expediente lo
# dice en su aviso de Telegram ("armado sin Claude con gemini-3.5-flash-lite").
_USADOS: set[str] = set()


def reiniciar_usados() -> None:
    _USADOS.clear()


def usados() -> set[str]:
    return set(_USADOS)


def es_cuota(error: str) -> bool:
    """El error de pedir() fue porque se acabó la cuota (429 / RESOURCE_EXHAUSTED)
    en todos los que se intentaron, no por la red o una llave que falta."""
    partes = [e for e in error.split(" | ") if "falta " not in e]
    return bool(partes) and all("429" in e or "RESOURCE_EXHAUSTED" in e or "quota" in e.lower()
                                for e in partes)


class SinIA(RuntimeError):
    """Ni Gemini ni Ollama contestaron: quien llama sigue sin esta ayuda."""


def _llave() -> str:
    return (os.getenv("GEMINI_API_KEY") or "").strip().strip("\"'")


def _json(texto: str):
    texto = texto.strip()
    if texto.startswith("```"):
        texto = texto.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(texto)


def gemini(prompt: str, modelo: str = GEMINI_FUERTE, como_json: bool = True, intentos: int = 3):
    """Una llamada a Gemini. Reintenta el 429 (cuota por minuto) y los 5xx."""
    if not _llave():
        raise SinIA("falta GEMINI_API_KEY")
    cuerpo = {"contents": [{"parts": [{"text": prompt}]}]}
    if como_json:
        cuerpo["generationConfig"] = {"responseMimeType": "application/json"}
    ultimo = ""
    for intento in range(intentos):
        try:
            r = httpx.post(GEMINI_URL.format(modelo), params={"key": _llave()}, json=cuerpo, timeout=120)
        except httpx.HTTPError as exc:
            ultimo = str(exc)
        else:
            if r.status_code == 200:
                partes = r.json()["candidates"][0]["content"]["parts"]
                texto = "".join(p.get("text", "") for p in partes)
                return _json(texto) if como_json else texto
            ultimo = f"HTTP {r.status_code}: {r.text[:200]}"
            if r.status_code not in (429, 500, 502, 503, 504):
                break
        if intento + 1 < intentos:
            time.sleep(15 * (intento + 1))
    raise SinIA(f"Gemini {modelo}: {ultimo}")


def compatible(nombre: str, url: str, modelo: str, prompt: str, como_json: bool = True, intentos: int = 2):
    """Una llamada a un proveedor con la API de OpenAI (los de RESPALDOS)."""
    llave = (os.getenv(f"{nombre}_API_KEY") or "").strip().strip("\"'")
    if not llave:
        raise SinIA(f"falta {nombre}_API_KEY")
    if "{CLOUDFLARE_ACCOUNT_ID}" in url:
        if not (cuenta := (os.getenv("CLOUDFLARE_ACCOUNT_ID") or "").strip()):
            raise SinIA("falta CLOUDFLARE_ACCOUNT_ID")
        url = url.replace("{CLOUDFLARE_ACCOUNT_ID}", cuenta)
    modelo = os.getenv(f"{nombre}_MODELO") or modelo
    cuerpo = {"model": modelo, "messages": [{"role": "user", "content": prompt}]}
    if como_json:
        cuerpo["response_format"] = {"type": "json_object"}
    ultimo = ""
    for intento in range(intentos):
        try:
            r = httpx.post(url, headers={"Authorization": f"Bearer {llave}"}, json=cuerpo, timeout=120)
        except httpx.HTTPError as exc:
            ultimo = str(exc)
        else:
            if r.status_code == 200:
                texto = r.json()["choices"][0]["message"]["content"]
                return _json(texto) if como_json else texto
            ultimo = f"HTTP {r.status_code}: {r.text[:200]}"
            if r.status_code not in (429, 500, 502, 503, 504):
                break
        if intento + 1 < intentos:
            time.sleep(10 * (intento + 1))
    raise SinIA(f"{nombre} {modelo}: {ultimo}")


def ollama(prompt: str, como_json: bool = True):
    """Una llamada al modelo local. Suelta la VRAM al terminar."""
    try:
        r = httpx.post(f"{OLLAMA_URL}/api/generate", timeout=300, json={
            "model": OLLAMA_MODELO, "prompt": prompt, "stream": False, "keep_alive": 0,
            "options": {"num_ctx": 8192}, **({"format": "json"} if como_json else {})})
        r.raise_for_status()
    except httpx.HTTPError as exc:
        raise SinIA(f"Ollama: {exc}") from exc
    texto = r.json()["response"]
    return _json(texto) if como_json else texto


def pedir(prompt: str, rapido: bool = False, local: bool = True, como_json: bool = True,
          reintentos: int | None = None):
    """Gemini (fuerte o rápido) -> el otro Gemini -> los RESPALDOS con llave ->
    Ollama si `local`. Los proveedores sin llave se brincan sin avisar.
    `reintentos=1` pasa al siguiente al primer 429 en vez de esperar (cada
    reintento de Gemini duerme 15-45 s y el Bash de Claude se corta a los 2 min)."""
    modelos = [GEMINI_RAPIDO, GEMINI_FUERTE] if rapido else [GEMINI_FUERTE, GEMINI_RAPIDO]
    errores = []
    veces = {"intentos": reintentos} if reintentos else {}
    intentos = [(m, lambda m=m: gemini(prompt, m, como_json, **veces)) for m in modelos]
    intentos += [(r[0].lower(), lambda r=r: compatible(*r, prompt, como_json, **veces)) for r in RESPALDOS
                 if os.getenv(f"{r[0]}_API_KEY")]
    for nombre, intento in intentos:
        try:
            respuesta = intento()
            _USADOS.add(nombre)
            return respuesta
        except (SinIA, ValueError, KeyError, IndexError) as exc:
            errores.append(str(exc))
            logger.warning("ia_gratis: %s", exc)
    if local:
        try:
            respuesta = ollama(prompt, como_json)
            _USADOS.add(f"ollama {OLLAMA_MODELO}")
            return respuesta
        except (SinIA, ValueError, KeyError) as exc:
            errores.append(str(exc))
    raise SinIA(" | ".join(errores))
