"""Programa los videos de papasia en TikTok con Zernio, repartidos por día.

    python tools/programar_papasia.py --videos 20 --dias 10            # muestra el plan
    python tools/programar_papasia.py --videos 20 --dias 10 --confirmar
    python tools/programar_papasia.py --confirmar                       # sigue el calendario activo

--videos N --dias D arma un calendario nuevo: N lugares repartidos en D días
(N // D al día; si sobra, los primeros días llevan uno más), a horas parejas
dentro de la ventana --ventana (default 10-22, hora de México) o en --horas.
Cada lugar se llena con el siguiente video terminado y sin publicar de
C:\\Android_in\\papasia\\lotes (el más viejo primero). Si no alcanzan los videos,
los lugares quedan libres; al volver a correr (sin --videos) se llenan los
lugares futuros con los videos nuevos. Los lugares que ya pasaron se saltan.

Sin --confirmar no sube ni programa nada. Texto = titulo + descripcion +
hashtags del guion.json; etiqueta de IA siempre encendida.
Archivos: zernio_calendario.json y zernio_publicados.json en C:\\Android_in\\papasia.

El vigilante de la fábrica (tools/fabrica.py ciclo) lo corre con --confirmar
cada 15 min si hay calendario, para que cada video nuevo tome el siguiente
lugar libre. Un candado en disco evita que dos corridas suban el mismo video.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

RAIZ = Path(r"C:\Android_in\papasia")
LOTES = RAIZ / "lotes"
CALENDARIO = RAIZ / "zernio_calendario.json"
PUBLICADOS = RAIZ / "zernio_publicados.json"
CANDADO = RAIZ / "zernio_programar.lock"
ENV = Path(__file__).resolve().parents[1] / ".env.papasia"
BASE = "https://zernio.com/api/v1"
CUENTA_TIKTOK = "6b032f2f9b297541e1582de7"  # @papasconia
ZONA = "America/Mexico_City"
TZ = ZoneInfo(ZONA)

AJUSTES_TIKTOK = {
    "privacyLevel": "PUBLIC_TO_EVERYONE",
    "allowComment": True,
    "allowDuet": False,
    "allowStitch": False,
    "videoMadeWithAi": True,
    "commercialContentType": "none",
    "contentPreviewConfirmed": True,
    "expressConsentGiven": True,
}


# ---------- utilidades ----------

def leer_json(p: Path, defecto):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else defecto


def guardar_json(p: Path, dato) -> None:
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(dato, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def tomar_candado() -> bool:
    """Uno a la vez; un candado de más de una hora es de una corrida que murió."""
    try:
        if CANDADO.exists() and time.time() - CANDADO.stat().st_mtime > 3600:
            CANDADO.unlink()
        os.close(os.open(CANDADO, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        return True
    except FileExistsError:
        return False


def normalizar(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", t)


def base_video(p: Path) -> str:
    """'nombre_2.mp4' y 'nombre.mp4' son versiones del mismo video."""
    return re.sub(r"_\d+$", "", p.stem)


# ---------- calendario ----------

def horas_del_dia(cuantos: int, ventana: tuple[int, int], fijas: list[str] | None) -> list[str]:
    if fijas:
        return [fijas[i % len(fijas)] for i in range(cuantos)]
    ini, fin = ventana
    paso = (fin - ini) * 60 / cuantos
    salida = []
    for i in range(cuantos):
        m = round(ini * 60 + paso * (i + 0.5))
        salida.append(f"{m // 60:02d}:{m % 60:02d}")
    return salida


def armar_calendario(videos: int, dias: int, desde: date, ventana, fijas) -> list[dict]:
    base, sobra = divmod(videos, dias)
    lugares = []
    for d in range(dias):
        cuantos = base + (1 if d < sobra else 0)
        if not cuantos:
            continue
        dia = desde + timedelta(days=d)
        for h in horas_del_dia(cuantos, ventana, fijas):
            lugares.append({"fecha": f"{dia.isoformat()}T{h}:00", "video": None, "postId": None})
    return lugares


# ---------- videos pendientes ----------

def indice_guiones() -> dict[str, Path]:
    idx = {}
    for g in RAIZ.glob("guion-papasia-*/guion.json"):
        try:
            titulo = json.loads(g.read_text(encoding="utf-8")).get("titulo", "")
        except (OSError, json.JSONDecodeError):
            continue
        if titulo:
            idx[normalizar(titulo)] = g
    return idx


def pendientes(publicados: dict, ocupados: set[str]) -> list[tuple[Path, Path]]:
    """(mp4, guion.json) sin publicar, del más viejo al más nuevo; una versión por video (la última)."""
    ultimo: dict[str, Path] = {}
    for mp4 in LOTES.rglob("*.mp4"):
        b = base_video(mp4)
        if b not in ultimo or mp4.stat().st_mtime > ultimo[b].stat().st_mtime:
            ultimo[b] = mp4
    guiones = indice_guiones()
    salida = []
    for b, mp4 in sorted(ultimo.items(), key=lambda kv: kv[1].stat().st_mtime):
        if b in publicados or b in ocupados:
            continue
        g = guiones.get(b)
        if not g:
            print(f"  ! sin guion.json para {mp4.name}; lo salto")
            continue
        salida.append((mp4, g))
    return salida


def texto_publicacion(guion: Path) -> str:
    d = json.loads(guion.read_text(encoding="utf-8"))
    partes = [d.get("titulo", "").strip(), d.get("descripcion", "").strip(), " ".join(d.get("hashtags", []))]
    return "\n\n".join(p for p in partes if p)


# ---------- Zernio ----------

def leer_key() -> str:
    for linea in ENV.read_text(encoding="utf-8").splitlines():
        if linea.strip().startswith("ZERNIO_API_KEY"):
            return linea.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit(f"No encontré ZERNIO_API_KEY en {ENV}")


class Zernio:
    def __init__(self, key: str):
        self.key = key

    def llamar(self, metodo: str, ruta: str, cuerpo: dict | None = None):
        req = urllib.request.Request(
            BASE + ruta,
            data=json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None,
            method=metodo,
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json",
                     "User-Agent": "publicador/0.1"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")[:1500]

    def subir(self, video: Path) -> str:
        st, pre = self.llamar("POST", "/media/presign", {
            "filename": video.name, "contentType": "video/mp4", "size": video.stat().st_size})
        if st != 200:
            raise RuntimeError(f"presign {st}: {pre}")
        req = urllib.request.Request(pre["uploadUrl"], data=video.read_bytes(), method="PUT",
                                     headers={"Content-Type": "video/mp4"})
        with urllib.request.urlopen(req, timeout=900):
            pass
        return pre["publicUrl"]

    def programar(self, url: str, texto: str, fecha: str) -> str:
        st, resp = self.llamar("POST", "/posts", {
            "content": texto,
            "mediaItems": [{"type": "video", "url": url}],
            "platforms": [{"platform": "tiktok", "accountId": CUENTA_TIKTOK}],
            "scheduledFor": fecha,
            "timezone": ZONA,
            "tiktokSettings": AJUSTES_TIKTOK,
        })
        if st not in (200, 201) or not isinstance(resp, dict):
            raise RuntimeError(f"crear post {st}: {resp}")
        post = resp.get("post", resp)
        return post.get("_id") or post.get("id")


# ---------- principal ----------

def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--videos", type=int, help="total de videos del calendario nuevo")
    ap.add_argument("--dias", type=int, help="días del calendario nuevo")
    ap.add_argument("--desde", help="primer día AAAA-MM-DD (default: mañana)")
    ap.add_argument("--ventana", default="10-22", help="horas parejas dentro de esta ventana (default 10-22)")
    ap.add_argument("--horas", help="horas fijas, p. ej. 13:00,19:00 (en lugar de la ventana)")
    ap.add_argument("--confirmar", action="store_true", help="sube y programa de verdad")
    a = ap.parse_args()

    if a.confirmar and not tomar_candado():
        print("Ya hay otra corrida programando; no hago nada.")
        return
    try:
        _programar(a)
    finally:
        if a.confirmar:
            CANDADO.unlink(missing_ok=True)


def _programar(a: argparse.Namespace) -> None:
    publicados = leer_json(PUBLICADOS, {})
    cal = leer_json(CALENDARIO, None)

    if a.videos or a.dias:
        if not (a.videos and a.dias):
            sys.exit("--videos y --dias van juntos")
        libres_viejos = [l for l in (cal or {}).get("lugares", []) if l["video"]]
        if libres_viejos and not a.confirmar:
            print(f"(Hay un calendario activo con {len(libres_viejos)} programados; esos se respetan.)")
        desde = date.fromisoformat(a.desde) if a.desde else datetime.now(TZ).date() + timedelta(days=1)
        ini, fin = (int(x) for x in a.ventana.split("-"))
        fijas = [h.strip() for h in a.horas.split(",")] if a.horas else None
        cal = {"creado": datetime.now(TZ).isoformat(timespec="seconds"), "videos": a.videos, "dias": a.dias,
               "lugares": armar_calendario(a.videos, a.dias, desde, (ini, fin), fijas)}
    elif not cal:
        sys.exit("No hay calendario activo: usa --videos N --dias D")

    ahora = datetime.now(TZ).replace(tzinfo=None)
    ocupados = {l["video"] for l in cal["lugares"] if l["video"]}
    cola = pendientes(publicados, ocupados)
    zernio = Zernio(leer_key()) if a.confirmar else None

    asignados = 0
    for lugar in cal["lugares"]:
        if lugar["video"] or datetime.fromisoformat(lugar["fecha"]) <= ahora + timedelta(minutes=15):
            continue
        if not cola:
            break
        mp4, guion = cola.pop(0)
        b = base_video(mp4)
        if a.confirmar:
            try:
                print(f"  subiendo {mp4.name} ...", flush=True)
                pid = zernio.programar(zernio.subir(mp4), texto_publicacion(guion), lugar["fecha"])
            except Exception as e:  # noqa: BLE001
                print(f"  ✗ {mp4.name}: {e}")
                break
            lugar.update(video=b, postId=pid)
            publicados[b] = {"postId": pid, "programado": lugar["fecha"], "archivo": str(mp4)}
            guardar_json(PUBLICADOS, publicados)
            guardar_json(CALENDARIO, cal)
        else:
            lugar["video"] = b  # solo para mostrar el plan
        asignados += 1

    # resumen por día
    por_dia: dict[str, list[dict]] = {}
    for l in cal["lugares"]:
        por_dia.setdefault(l["fecha"][:10], []).append(l)
    print(f"\nCalendario: {cal['videos']} videos en {cal['dias']} días")
    for dia, ls in por_dia.items():
        print(f"  {dia}")
        for l in ls:
            hora = l["fecha"][11:16]
            if l["video"]:
                marca = "programado" if l.get("postId") else "← se programaría"
                print(f"    {hora}  {l['video']}  ({marca})")
            else:
                vencido = datetime.fromisoformat(l["fecha"]) <= ahora
                print(f"    {hora}  {'(ya pasó)' if vencido else '— libre: falta video'}")
    libres = sum(1 for l in cal["lugares"] if not l["video"] and datetime.fromisoformat(l["fecha"]) > ahora)
    print(f"\n{asignados} {'programados ahora' if a.confirmar else 'se programarían'}; "
          f"{libres} lugares libres esperando video; {len(cola)} videos sobrantes.")
    if a.confirmar:
        guardar_json(CALENDARIO, cal)
    else:
        print("Nada se envió (falta --confirmar).")


if __name__ == "__main__":
    main()
