"""Que escribir un lote no se coma la cuota de Claude.

Medido el 26/09/2026: el bot reusaba la MISMA conversación con Claude desde
el 19/08 (16 MB, ~900.000 tokens de contexto). Claude relee el historial
entero en cada paso, así que escribir 13 guiones costó 34 millones de tokens
y agotó la cuota a mitad de un /lotegrande de 20. Y como el bot siguió
intentando los tramos que faltaban y no guardó cuáles eran, el lote quedó a
medias sin forma de retomarlo.
"""

import asyncio
import json
from unittest.mock import patch

from dato_mata_gato_bot import bot, claude_runner, sessions


class _Msg:
    def __init__(self):
        self.replies = []

    async def reply_text(self, texto, **kwargs):
        self.replies.append(texto)


class _Update:
    def __init__(self, chat_id=7):
        self.effective_chat = type("C", (), {"id": chat_id})()
        self.message = _Msg()


class _Ctx:
    args = []


def _estado(tmp_path, monkeypatch, datos=None):
    ruta = tmp_path / "sessions.json"
    ruta.write_text(json.dumps(datos or {"7": {}}), encoding="utf-8")
    monkeypatch.setattr(sessions, "SESSIONS_PATH", ruta)
    monkeypatch.setattr(sessions, "DATA_DIR", tmp_path)


# ----------------------------------------------------------- el motivo real

LIMITE = ('{"type":"result","is_error":true,"result":"You\'ve hit your session limit '
          '\\u00b7 resets 3:40pm (America/Mexico_City)"}')


def test_el_motivo_del_error_sale_de_stdout():
    """Con la cuota agotada, stderr viene vacío: el bot decía solo "Error
    ejecutando Claude:" y el usuario no sabía qué pasó ni cuándo reintentar."""
    motivo = claude_runner._motivo_del_error(LIMITE)
    assert "session limit" in motivo and "3:40pm" in motivo
    assert claude_runner.es_limite_de_uso(motivo)
    assert not claude_runner.es_limite_de_uso("claude no encontró el archivo guion.json")


# --------------------------------------------------- sesiones nuevas y chicas

def test_cada_tramo_del_lote_va_en_una_conversacion_nueva(tmp_path, monkeypatch):
    _estado(tmp_path, monkeypatch)
    usadas = []

    async def _fake_guiones(update, session_id, is_new, cantidad, desc="", formato="crimen"):
        usadas.append((session_id, is_new))
        return [{"slug": f"guion-{len(usadas)}", "titulo": "t", "resumen_hechos": "r"}]

    async def _nada(*a, **k):
        return None

    with patch.object(bot, "_guiones_de_crimen", _fake_guiones), \
         patch.object(bot, "_authorized", lambda _chat: True), \
         patch.object(bot, "_send_long", _nada):
        asyncio.run(bot._pedir_lote(_Update(), _Ctx(), lambda n: [
            ("crimen", "de crimen", 2), ("famoso", "de famoso", 1)], cantidad=3))

    assert len(usadas) == 2
    assert all(nueva for _, nueva in usadas), "ninguna puede retomar la del chat"
    assert len({sid for sid, _ in usadas}) == 2, "una conversación distinta por tramo"


def test_si_se_acaba_la_cuota_para_y_guarda_lo_que_falta(tmp_path, monkeypatch):
    """Lo que ya salió queda en el lote, lo que falta queda anotado para
    /completarlote, y no se sigue martillando a Claude."""
    _estado(tmp_path, monkeypatch)
    intentos = []

    async def _fake_guiones(update, session_id, is_new, cantidad, desc="", formato="crimen"):
        intentos.append(formato)
        if formato == "culpable":
            raise bot.LimiteDeClaude("Error ejecutando Claude: You've hit your session limit")
        return [{"slug": f"guion-{formato}", "titulo": "t", "resumen_hechos": "r"}]

    async def _nada(*a, **k):
        return None

    update = _Update()
    with patch.object(bot, "_guiones_de_crimen", _fake_guiones), \
         patch.object(bot, "_authorized", lambda _chat: True), \
         patch.object(bot, "_send_long", _nada):
        asyncio.run(bot._pedir_lote(update, _Ctx(), lambda n: [
            ("crimen", "de crimen", 1), ("culpable", "de culpable", 1),
            ("mito", "de mitos", 2)], cantidad=4))

    assert intentos == ["crimen", "culpable"], "después del límite no se intenta nada más"
    assert sessions.get_pending_batch(7) == ["guion-crimen"]
    assert sessions.get_tramos_faltantes(7) == [("culpable", "de culpable", 1),
                                                ("mito", "de mitos", 2)]
    assert any("cuota" in r and "/completarlote" in r for r in update.message.replies)


def test_completarlote_suma_al_lote_en_vez_de_pisarlo(tmp_path, monkeypatch):
    _estado(tmp_path, monkeypatch, {"7": {
        "pending_batch": ["guion-a", "guion-b"],
        "tramos_faltantes": [["mito", "de mitos", 1]]}})

    async def _fake_guiones(update, session_id, is_new, cantidad, desc="", formato="crimen"):
        return [{"slug": "mito-nuevo", "titulo": "t", "resumen_hechos": "r"}]

    async def _nada(*a, **k):
        return None

    with patch.object(bot, "_guiones_de_crimen", _fake_guiones), \
         patch.object(bot, "_authorized", lambda _chat: True), \
         patch.object(bot, "_send_long", _nada):
        asyncio.run(bot.cmd_completarlote(_Update(), _Ctx()))

    assert sessions.get_pending_batch(7) == ["guion-a", "guion-b", "mito-nuevo"]
    assert sessions.get_tramos_faltantes(7) == []


def test_la_conversacion_rotada_se_crea_y_no_se_retoma(tmp_path, monkeypatch):
    """Si la nueva se "retomara", Claude fallaría: todavía no existe."""
    _estado(tmp_path, monkeypatch, {"7": {"session_id": "vieja", "pending_batch": ["x"]}})
    nueva = sessions.nueva_sesion_claude(7)
    assert sessions.ensure_session_id(7) == (nueva, True)
    assert sessions.ensure_session_id(7) == (nueva, False)
    assert sessions.get_pending_batch(7) == ["x"], "rotar no puede borrar el lote"


def test_el_tamano_de_la_sesion_se_mide_en_disco(tmp_path, monkeypatch):
    from pathlib import Path
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    carpeta = tmp_path / ".claude" / "projects" / claude_runner.CWD.replace(":", "-").replace("\\", "-")
    carpeta.mkdir(parents=True)
    (carpeta / "abc.jsonl").write_bytes(b"x" * 1234)
    assert claude_runner.tamano_sesion("abc") == 1234
    assert claude_runner.tamano_sesion("no-existe") == 0


# ------------------------------------------------------ la instrucción misma

def test_la_instruccion_ya_no_manda_a_abrir_todos_los_guiones():
    assert "abras los archivos" in bot.INSTRUCCION_NUEVO_LOTE
    assert "revisá qué ya está cubierto (los guion.json" not in bot.INSTRUCCION_NUEVO_LOTE


def test_los_mitos_tienen_presupuesto_de_investigacion():
    """La prueba de la Xtabay, con sesión nueva, igual hizo 92 pasos y gastó
    10 millones de tokens leyendo páginas."""
    assert "PRESUPUESTO DE INVESTIGACIÓN" in bot.INSTRUCCION_MITO


def test_la_lista_de_ya_cubiertos_sale_de_disco(tmp_path, monkeypatch):
    monkeypatch.setattr(sessions, "ANDROID_IN", tmp_path)
    for slug, titulo in (("guion-a", "Caso A"), ("mito-x", "La Xtabay")):
        (tmp_path / slug).mkdir()
        (tmp_path / slug / "guion.json").write_text(json.dumps({"titulo": titulo}), encoding="utf-8")
    assert bot._ya_cubiertos("guion") == "Caso A"
    assert bot._ya_cubiertos("mito") == "La Xtabay"
