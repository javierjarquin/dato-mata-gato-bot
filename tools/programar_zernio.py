"""Programa los videos de un canal en TikTok con Zernio, repartidos por día.

    python tools/programar_zernio.py --canal papasia --videos 20 --dias 10              # muestra el plan
    python tools/programar_zernio.py --canal papasia --videos 20 --dias 10 --confirmar
    python tools/programar_zernio.py --canal datomatagato --confirmar                    # sigue su calendario
    python tools/programar_zernio.py --canal datomatagato --ya-publicado casomonstruodeatizapan
    python tools/programar_zernio.py --canal datomatagato --videos 10 --dias 3 --lote todos-20261122-2100 --confirmar

Canales: `papasia` (C:\\Android_in\\papasia) y `datomatagato` (C:\\Android_in).

--videos N --dias D arma un calendario nuevo: N lugares repartidos en D días
(N // D al día; si sobra, los ÚLTIMOS días llevan uno más: 10 en 3 = 3, 3, 4),
a horas parejas dentro de --ventana (default 10-22, hora de México) o en
--horas. Empieza mañana, o el día después del último post del calendario
anterior que todavía no sale. Cada lugar se llena con el siguiente video
terminado y sin publicar de <canal>\\lotes (el más viejo primero). Si no
alcanzan, los lugares quedan libres y se llenan al volver a correr; los que ya
pasaron se saltan.

--lote L (lo usan /lotegrande N D y /papasia N D desde Telegram): el calendario
solo toma los videos de lotes\\L, cada uno en cuanto la fábrica lo genera. Si un
lugar pasa sin video (todavía no se generaba), se repone al final a la misma
hora, para que salgan los N.

--ya-publicado <video> marca como publicado ese video y todos los anteriores
(lo que se subió a mano antes de Zernio).

Sin --confirmar no sube ni programa nada. Texto = titulo + descripcion +
hashtags del guion.json; etiqueta de IA encendida; portada = primer cuadro
(el pipeline la pega ahí).

Cuenta de TikTok: ZERNIO_TIKTOK_CUENTA en el .env PROPIO del canal (.env para
Dato Mata Gato, .env.papasia para papasia), nunca heredada de otro canal.
ZERNIO_API_KEY puede estar en cualquiera de los dos (es una cuenta de Zernio).
Archivos por canal, en su carpeta: zernio_calendario.json, zernio_publicados.json.

El vigilante de la fábrica (tools/fabrica.py ciclo) lo corre con --confirmar
cada 15 min para cada canal que tenga calendario. Un candado en disco evita
que dos corridas suban el mismo video.
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

from dotenv import dotenv_values

RAIZ_BOT = Path(__file__).resolve().parents[1]
ENTRADA_BASE = Path(r"C:\Android_in")
BASE = "https://zernio.com/api/v1"
ZONA = "America/Mexico_City"
TZ = ZoneInfo(ZONA)

# "" es Dato Mata Gato, como en canal.py.
CANALES = {"papasia": "papasia", "datomatagato": ""}

AJUSTES_COMUNES = {
    "privacyLevel": "PUBLIC_TO_EVERYONE",
    "allowComment": True,
    "videoMadeWithAi": True,
    "commercialContentType": "none",
    # La portada va pegada en el primer cuadro (pipeline); sin esto TikTok toma
    # el cuadro del segundo 1.
    "videoCoverTimestampMs": 0,
    "contentPreviewConfirmed": True,
    "expressConsentGiven": True,
}
# Dúos y stitch: Dato Mata Gato los lleva encendidos (CHECKLIST_PUBLICAR de fabrica.py).
AJUSTES_CANAL = {
    "papasia": {"allowDuet": False, "allowStitch": False},
    "": {"allowDuet": True, "allowStitch": True},
}


class Canal:
    def __init__(self, nombre_cli: str):
        self.nombre = nombre_cli
        self.id = CANALES[nombre_cli]
        self.raiz = ENTRADA_BASE / self.id if self.id else ENTRADA_BASE
        self.lotes = self.raiz / "lotes"
        self.calendario = self.raiz / "zernio_calendario.json"
        self.publicados = self.raiz / "zernio_publicados.json"
        self.candado = self.raiz / "zernio_programar.lock"
        self.env = RAIZ_BOT / (f".env.{self.id}" if self.id else ".env")
        self.ajustes = {**AJUSTES_COMUNES, **AJUSTES_CANAL[self.id]}

    def key(self) -> str:
        for archivo in (self.env, RAIZ_BOT / ".env", RAIZ_BOT / ".env.papasia"):
            if archivo.exists() and (k := dotenv_values(archivo).get("ZERNIO_API_KEY")):
                return k
        sys.exit("No encontré ZERNIO_API_KEY en los .env del bot")

    def cuenta(self) -> str:
        """Solo del .env de ESTE canal: un canal nunca publica en la cuenta del otro."""
        c = dotenv_values(self.env).get("ZERNIO_TIKTOK_CUENTA") if self.env.exists() else None
        if not c:
            sys.exit(f"Falta ZERNIO_TIKTOK_CUENTA en {self.env.name} (canal {self.nombre})")
        return c


# ---------- utilidades ----------

def leer_json(p: Path, defecto):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else defecto


def guardar_json(p: Path, dato) -> None:
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(dato, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def tomar_candado(candado: Path) -> bool:
    """Uno a la vez por canal; un candado de más de una hora es de una corrida que murió."""
    try:
        if candado.exists() and time.time() - candado.stat().st_mtime > 3600:
            candado.unlink()
        os.close(os.open(candado, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        return True
    except FileExistsError:
        return False


def normalizar(texto: str) -> str:
    """Igual que drive_upload.slugify_titulo, que pone el nombre del archivo en lotes."""
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
    """10 en 3 días = 3, 3 y 4: lo que sobra va en los ÚLTIMOS días (Javier,
    22/11/2026), que es cuando ya hay más videos generados."""
    base, sobra = divmod(videos, dias)
    lugares = []
    for d in range(dias):
        cuantos = base + (1 if d >= dias - sobra else 0)
        if not cuantos:
            continue
        dia = desde + timedelta(days=d)
        for h in horas_del_dia(cuantos, ventana, fijas):
            lugares.append({"fecha": f"{dia.isoformat()}T{h}:00", "video": None, "postId": None})
    return lugares


def primer_dia_libre(cal: dict | None, ahora: datetime) -> date:
    """Mañana, o el día siguiente al último post del calendario anterior que
    todavía no sale: un calendario nuevo no se encima con lo ya programado."""
    dia = ahora.date() + timedelta(days=1)
    for l in (cal or {}).get("lugares", []):
        f = datetime.fromisoformat(l["fecha"])
        if l.get("postId") and f > ahora:
            dia = max(dia, f.date() + timedelta(days=1))
    return dia


def reponer_vencidos(cal: dict, ahora: datetime) -> int:
    """Calendario de un lote: si un lugar pasa sin video (la fábrica todavía no
    lo generaba), se repone al final, a la misma hora del día siguiente al
    último lugar. Así los N videos del lote salen todos; nunca se pierde uno."""
    repuestos = 0
    for l in cal["lugares"]:
        if l["video"] or l.get("vencido") or datetime.fromisoformat(l["fecha"]) > ahora + timedelta(minutes=15):
            continue
        l["vencido"] = True
        ultimo = max(datetime.fromisoformat(x["fecha"]) for x in cal["lugares"])
        hora = datetime.fromisoformat(l["fecha"]).time()
        nuevo = datetime.combine(ultimo.date() + (timedelta(days=1) if hora <= ultimo.time() else timedelta()), hora)
        cal["lugares"].append({"fecha": nuevo.isoformat(timespec="seconds"), "video": None, "postId": None})
        repuestos += 1
    return repuestos


# ---------- videos ----------

def videos_archivados(c: Canal, lote: str | None = None) -> list[Path]:
    """Un mp4 por video (de 'x.mp4' y 'x_2.mp4', el último), del más viejo al
    más nuevo. Con `lote`, solo los de lotes/<lote> (calendario de un comando)."""
    ultimo: dict[str, Path] = {}
    for mp4 in (c.lotes / lote if lote else c.lotes).rglob("*.mp4"):
        if mp4.stem.endswith("_telegram"):
            continue
        b = base_video(mp4)
        if b not in ultimo or mp4.stat().st_mtime > ultimo[b].stat().st_mtime:
            ultimo[b] = mp4
    return sorted(ultimo.values(), key=lambda p: p.stat().st_mtime)


def indice_guiones(c: Canal) -> dict[str, Path]:
    idx = {}
    for g in c.raiz.glob("*/guion.json"):
        try:
            titulo = json.loads(g.read_text(encoding="utf-8")).get("titulo", "")
        except (OSError, json.JSONDecodeError, AttributeError):
            continue
        if titulo:
            idx[normalizar(titulo)] = g
    return idx


def pendientes(c: Canal, publicados: dict, ocupados: set[str],
               lote: str | None = None) -> list[tuple[Path, Path]]:
    guiones = indice_guiones(c)
    salida = []
    for mp4 in videos_archivados(c, lote):
        b = base_video(mp4)
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
    etiquetas = [h if str(h).startswith("#") else f"#{h}" for h in d.get("hashtags", []) if str(h).strip()]
    partes = [d.get("titulo", "").strip(), d.get("descripcion", "").strip(), " ".join(etiquetas)]
    return "\n\n".join(p for p in partes if p)


def marcar_publicados_hasta(c: Canal, ultimo: str) -> None:
    videos = videos_archivados(c)
    nombres = [base_video(v) for v in videos]
    if ultimo not in nombres:
        sys.exit(f"No encontré {ultimo} en {c.lotes}")
    publicados = leer_json(c.publicados, {})
    corte = nombres.index(ultimo)
    nuevos = 0
    for v in videos[: corte + 1]:
        b = base_video(v)
        if b not in publicados:
            publicados[b] = {"postId": None, "programado": None, "archivo": str(v),
                             "nota": "publicado a mano antes de Zernio"}
            nuevos += 1
    guardar_json(c.publicados, publicados)
    print(f"{nuevos} marcados como publicados (hasta {ultimo}); quedan {len(videos) - corte - 1} después.")


# ---------- Zernio ----------

class Zernio:
    def __init__(self, key: str, cuenta: str, ajustes: dict):
        self.key, self.cuenta, self.ajustes = key, cuenta, ajustes

    def llamar(self, metodo: str, ruta: str, cuerpo: dict | None = None):
        req = urllib.request.Request(
            BASE + ruta,
            data=json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None,
            method=metodo,
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json",
                     "User-Agent": "publicador/0.2"},
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

    def cuerpo(self, url: str, texto: str, fecha: str) -> dict:
        return {
            "content": texto,
            "mediaItems": [{"type": "video", "url": url}],
            "platforms": [{"platform": "tiktok", "accountId": self.cuenta}],
            "scheduledFor": fecha,
            "timezone": ZONA,
            "tiktokSettings": self.ajustes,
        }

    def programar(self, url: str, texto: str, fecha: str) -> str:
        st, resp = self.llamar("POST", "/posts", self.cuerpo(url, texto, fecha))
        if st not in (200, 201) or not isinstance(resp, dict):
            raise RuntimeError(f"crear post {st}: {resp}")
        post = resp.get("post", resp)
        return post.get("_id") or post.get("id")

    def en_seco(self, url: str, texto: str, fecha: str):
        return self.llamar("POST", "/posts", {**self.cuerpo(url, texto, fecha), "dryRun": True})


# ---------- principal ----------

def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--canal", required=True, choices=sorted(CANALES))
    ap.add_argument("--videos", type=int, help="total de videos del calendario nuevo")
    ap.add_argument("--dias", type=int, help="días del calendario nuevo")
    ap.add_argument("--desde", help="primer día AAAA-MM-DD (default: mañana)")
    ap.add_argument("--ventana", default="10-22", help="horas parejas dentro de esta ventana (default 10-22)")
    ap.add_argument("--horas", help="horas fijas, p. ej. 13:00,19:00 (en lugar de la ventana)")
    ap.add_argument("--lote", help="con --videos: el calendario solo toma los videos de lotes/<lote> "
                                   "(lo que arma /lotegrande N D o /papasia N D)")
    ap.add_argument("--ya-publicado", metavar="VIDEO", help="marca ese video y los anteriores como publicados")
    ap.add_argument("--en-seco", action="store_true",
                    help="sube el siguiente pendiente y lo valida con dryRun (no publica)")
    ap.add_argument("--confirmar", action="store_true", help="sube y programa de verdad")
    a = ap.parse_args()
    c = Canal(a.canal)

    if a.ya_publicado:
        marcar_publicados_hasta(c, a.ya_publicado)
        return
    if a.en_seco:
        _en_seco(c)
        return
    if a.confirmar and not tomar_candado(c.candado):
        # Un calendario nuevo (lo manda el bot) espera a que el vigilante
        # termine de subir: si no, el vigilante guardaría encima el calendario viejo.
        limite = time.time() + (1200 if a.videos else 0)
        tomado = False
        while not tomado and time.time() < limite:
            time.sleep(5)
            tomado = tomar_candado(c.candado)
        if not tomado:
            print("Ya hay otra corrida programando este canal; no hago nada.")
            sys.exit(2 if a.videos else 0)
    try:
        _programar(c, a)
    finally:
        if a.confirmar:
            c.candado.unlink(missing_ok=True)


def _en_seco(c: Canal) -> None:
    cola = pendientes(c, leer_json(c.publicados, {}), set())
    if not cola:
        sys.exit("No hay videos pendientes para probar")
    mp4, guion = cola[0]
    z = Zernio(c.key(), c.cuenta(), c.ajustes)
    print(f"Probando {mp4.name}\n\n{texto_publicacion(guion)}\n")
    manana = (datetime.now(TZ) + timedelta(days=1)).strftime("%Y-%m-%dT13:00:00")
    st, resp = z.en_seco(z.subir(mp4), texto_publicacion(guion), manana)
    print("dryRun", st, json.dumps(resp, ensure_ascii=False) if isinstance(resp, dict) else resp)


def _programar(c: Canal, a: argparse.Namespace) -> None:
    publicados = leer_json(c.publicados, {})
    cal = leer_json(c.calendario, None)

    if a.videos or a.dias:
        if not (a.videos and a.dias):
            sys.exit("--videos y --dias van juntos")
        previos = [l for l in (cal or {}).get("lugares", []) if l.get("postId")]
        if previos:
            print(f"(El calendario anterior tenía {len(previos)} ya programados en Zernio; esos siguen en pie.)")
        ahora_mx = datetime.now(TZ).replace(tzinfo=None)
        desde = date.fromisoformat(a.desde) if a.desde else primer_dia_libre(cal, ahora_mx)
        ini, fin = (int(x) for x in a.ventana.split("-"))
        fijas = [h.strip() for h in a.horas.split(",")] if a.horas else None
        cal = {"creado": datetime.now(TZ).isoformat(timespec="seconds"), "videos": a.videos, "dias": a.dias,
               **({"lote": a.lote} if a.lote else {}),
               "lugares": armar_calendario(a.videos, a.dias, desde, (ini, fin), fijas)}
    elif not cal:
        sys.exit(f"No hay calendario activo para {c.nombre}: usa --videos N --dias D")

    ahora = datetime.now(TZ).replace(tzinfo=None)
    if cal.get("lote"):
        # Solo se repone lo que todavía tiene un video del lote por llegar.
        llenos = sum(1 for l in cal["lugares"] if l["video"])
        vivos = sum(1 for l in cal["lugares"] if not l["video"] and not l.get("vencido")
                    and datetime.fromisoformat(l["fecha"]) > ahora + timedelta(minutes=15))
        # Un lote terminado (o detenido) ya no manda más videos: no se repone.
        estado = leer_json(c.raiz / "fabrica" / cal["lote"] / "estado.json", {})
        sin_subir = len(pendientes(c, publicados, {l["video"] for l in cal["lugares"] if l["video"]}, cal["lote"]))
        if llenos + vivos < cal["videos"] and (not estado.get("terminado") or sin_subir > vivos):
            reponer_vencidos(cal, ahora)
    ocupados = {l["video"] for l in cal["lugares"] if l["video"]}
    cola = pendientes(c, publicados, ocupados, cal.get("lote"))
    zernio = Zernio(c.key(), c.cuenta(), c.ajustes) if a.confirmar else None

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
            guardar_json(c.publicados, publicados)
            guardar_json(c.calendario, cal)
        else:
            lugar["video"] = b  # solo para mostrar el plan
        asignados += 1

    por_dia: dict[str, list[dict]] = {}
    for l in cal["lugares"]:
        por_dia.setdefault(l["fecha"][:10], []).append(l)
    print(f"\n{c.nombre}: {cal['videos']} videos en {cal['dias']} días")
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
        guardar_json(c.calendario, cal)
    else:
        print("Nada se envió (falta --confirmar).")


if __name__ == "__main__":
    main()
