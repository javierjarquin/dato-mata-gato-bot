"""Retoma el lote grande pendiente desde la consola, sin pasar por Telegram.

Hace lo mismo que `/generargrande` (mismo plan, misma carpeta, misma rotación
de avatares, mismo archivado sin publicar) y avisa el progreso por Telegram
igual. Existe para poder retomar un lote cortado sin tener que tocar el
teléfono.

Respeta `/pausa` y `/reanudar`: el usuario puede seguir pausando desde el
teléfono aunque el lote lo haya arrancado este script.

Mientras corre deja `generating=True`, así el bot rechaza un
`/generargrande` en paralelo -- dos corridas peleando por la misma placa de
8 GB no terminan bien.
"""

import argparse
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv  # noqa: E402

from dato_mata_gato_bot import (  # noqa: E402
    avatar_presentador, lote_grande, pipeline, sessions,
)

load_dotenv()
CHAT_ID = os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",")[0].strip()


# La consola de Windows es cp1252 y no sabe escribir emojis: el 23/09/2026
# este script termino el lote entero y despues se mato con UnicodeEncodeError
# al imprimir el resumen final, que por eso nunca llego a Telegram.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def avisar(texto: str) -> None:
    """Un aviso que no llega no puede tirar el lote (son horas de máquina)."""
    try:
        print(texto, flush=True)
    except UnicodeEncodeError:
        print(texto.encode("ascii", "replace").decode(), flush=True)
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or not CHAT_ID:
        return
    try:
        datos = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": texto}).encode()
        urllib.request.urlopen(
            f"https://api.telegram.org/bot{token}/sendMessage", datos, timeout=30)
    except Exception as exc:  # noqa: BLE001
        print(f"  (no se pudo avisar por Telegram: {exc})", flush=True)


def mandar_hoja(slug: str) -> None:
    """La hoja con las imágenes de un mito, igual que la manda el bot."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    hoja = pipeline.hoja_de_contacto(slug)
    if not (token and CHAT_ID and hoja):
        return
    try:
        import requests
        with open(hoja, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendPhoto",
                data={"chat_id": CHAT_ID,
                      "caption": f"Imágenes de '{slug}': revísalas antes de publicar."},
                files={"photo": f}, timeout=60)
    except Exception as exc:  # noqa: BLE001
        print(f"  (no se pudo mandar la hoja de {slug}: {exc})", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chat", type=int, default=int(CHAT_ID or 0))
    args = ap.parse_args()
    chat_id = args.chat

    slugs = sessions.get_pending_batch(chat_id)
    if not slugs:
        raise SystemExit("no hay lote pendiente")
    corriendo, desde = sessions.get_generating(chat_id)
    if corriendo:
        raise SystemExit(f"ya hay algo corriendo desde {desde}")

    # Las dos verificaciones caras ANTES de arrancar: descubrir a la segunda
    # hora que faltaba el motor de voz sería el peor final posible.
    sin_avatar = sessions.get_lote_sin_avatar(chat_id)
    for falta in (pipeline.motor_tts_listo(),
                  "" if sin_avatar else avatar_presentador.disponible()):
        if falta:
            raise SystemExit(falta)

    plan = lote_grande.planificar(list(slugs),
                                  con_avatar=not sessions.get_lote_sin_avatar(chat_id))
    lote_grande.repartir_voces(plan)  # prueba Fish 3 / voz de Javier (11/10/2026)
    total = len(plan.tareas)
    avisar(f"Retomando el lote.\n{plan.resumen()}\n\nNo se sube nada a Drive.")

    # A1111 arriba ANTES del primer video. En un video nuevo no haría falta
    # esperar (pasan minutos de audio y concat antes de pedir la primera
    # imagen), pero un proyecto que se RETOMA ya tiene eso en disco y llega a
    # pedir imágenes a los pocos segundos. El 23/09/2026 guion-mara-castilla
    # se perdió así: falló en seis segundos contra un A1111 que recién
    # arrancaba.
    pipeline._kick_off_a1111_if_needed()
    if not pipeline._esperar_a1111():
        avisar("A1111 no levantó; el lote sigue igual, pero los videos que "
               "necesiten imágenes generadas van a fallar.")

    ok_list, fallidos = [], []
    restantes = list(slugs)
    sessions.set_generating(chat_id, True)
    try:
        for i, (slug, avatar_num) in enumerate(plan.tareas, start=1):
            if sessions.get_pausa(chat_id):
                bajo = pipeline._detener_a1111()
                avisar(f"⏸️ Pausado antes de ({i}/{total})."
                       + (" A1111 cerrado, la gráfica queda libre." if bajo else "")
                       + f" Quedan {len(restantes)}. /reanudar para seguir.")
                while sessions.get_pausa(chat_id):
                    time.sleep(5)
                avisar(f"▶️ Sigo en ({i}/{total}).")

            etq = f"({i}/{total}) '{slug}'" + (
                f" con avatar {avatar_num}" if avatar_num is not None else "")
            avisar(f"{etq}...")
            try:
                r = pipeline.run(slug, sessions.get_voice(chat_id), chat_id,
                                 avatar_num is not None, avatar_num, plan.carpeta)
                if r.ok:
                    ok_list.append(slug)
                    avisar(f"{etq} listo: {r.mensaje}")
                    mandar_hoja(slug)
                else:
                    # Un guion roto NO corta el resto del lote: se anota y se sigue.
                    fallidos.append(slug)
                    avisar(f"{etq} falló: {r.mensaje[:400]}")
            except Exception as exc:  # noqa: BLE001
                fallidos.append(slug)
                avisar(f"{etq} explotó: {exc}")
            finally:
                sessions.set_progress(chat_id, None)
                if not sessions.get_pausa(chat_id):
                    restantes.remove(slug)
                    sessions.set_pending_batch(chat_id, restantes)

            if sessions.get_pausa(chat_id) and slug in restantes:
                avisar(f"⏸️ Cortado en ({i}/{total}). '{slug}' vuelve a la cola. "
                       f"Quedan {len(restantes)}.")
                break
    finally:
        sessions.set_generating(chat_id, False)
        sessions.set_progress(chat_id, None)

    videos = sorted(plan.carpeta.glob("*.mp4")) if plan.carpeta.exists() else []
    avisar(
        "🎬 LOTE TERMINADO\n"
        f"Listos ahora: {len(ok_list)}   Fallidos: {len(fallidos)}\n"
        f"En la carpeta hay {len(videos)} videos en total.\n\n"
        f"📁 {plan.carpeta}\n\n"
        "⚠️ NO se subió nada a Drive ni entró al calendario: son para revisar "
        "y publicar a mano."
        + (f"\n\nFallaron: {', '.join(fallidos)}" if fallidos else "")
    )


if __name__ == "__main__":
    main()
