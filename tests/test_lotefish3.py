"""/lotefish3: lote SOLO de true crime con evidencia real y voz de Fish 3.

El formato aprobado con Tierra Blanca (28-29/09/2026). Lo que se fija acá es
que el lote no se mezcle con otra cosa: ni trivias, ni mitos, ni presentador
(que es la cara de Javier con su voz).
"""

import asyncio
import json
from unittest.mock import patch

from dato_mata_gato_bot import bot, formatos, lote_grande, sessions


def test_el_reparto_es_solo_true_crime_y_sin_el_dato_de_15():
    for n in (1, 5, 10, 20, 30):
        tramos = formatos.repartir_fish3(n)
        claves = {c for c, _, _ in tramos}
        assert sum(c for _, _, c in tramos) == n
        assert not claves & {formatos.TRIVIA, formatos.MITO, "dato_15"}
    assert "crimen" in {c for c, _, _ in formatos.repartir_fish3(10)}


def test_el_comando_esta_registrado():
    assert "lotefish3" in {n for n, _ in bot.BOT_COMMANDS}
    assert "/lotefish3" in bot.HELP_TEXT


def test_un_lote_sin_avatar_no_pone_presentador(tmp_path, monkeypatch):
    monkeypatch.setattr(lote_grande.avatar_presentador, "avatares_disponibles", lambda: [0, 1, 2])
    slugs = [f"guion-{i}" for i in range(30)]
    for s in slugs:
        (tmp_path / s).mkdir()
        (tmp_path / s / "guion.json").write_text(json.dumps({"planos": [{}] * 8}),
                                                 encoding="utf-8")
    plan = lote_grande.planificar(slugs, entrada=tmp_path, con_avatar=False)
    assert plan.con_avatar == 0
    assert lote_grande.planificar(slugs, entrada=tmp_path).con_avatar == 3


def test_la_marca_sin_avatar_se_guarda_en_disco(tmp_path, monkeypatch):
    ruta = tmp_path / "sessions.json"
    ruta.write_text(json.dumps({"7": {}}), encoding="utf-8")
    monkeypatch.setattr(sessions, "SESSIONS_PATH", ruta)
    monkeypatch.setattr(sessions, "DATA_DIR", tmp_path)
    assert sessions.get_lote_sin_avatar(7) is False
    sessions.set_lote_sin_avatar(7, True)
    assert sessions.get_lote_sin_avatar(7) is True


class _Msg:
    def __init__(self, text):
        self.text = text
        self.replies = []

    async def reply_text(self, texto, **kwargs):
        self.replies.append(texto)


class _Update:
    def __init__(self, text):
        self.effective_chat = type("C", (), {"id": 1})()
        self.message = _Msg(text)


def _correr(cmd, texto, args):
    espia = {"sin_avatar": None, "tramos": []}

    def _fake_crimen(update, session_id, is_new, cant, desc, formato):
        espia["tramos"].append(formato)
        return [{"slug": f"guion-{formato}-{i}"} for i in range(cant)]

    async def _async_crimen(*a, **k):
        return _fake_crimen(*a, **k)

    with patch.object(bot, "_guiones_de_crimen", _async_crimen), \
         patch.object(bot, "_sesion_nueva", lambda: ("sid", True)), \
         patch.object(bot.sessions, "get_generating", lambda c: (False, None)), \
         patch.object(bot.sessions, "set_generating", lambda c, v: None), \
         patch.object(bot.sessions, "set_tramos_faltantes", lambda c, f: None), \
         patch.object(bot.sessions, "set_pending_batch", lambda c, s: None), \
         patch.object(bot.sessions, "set_lote_sin_avatar",
                      lambda c, v: espia.__setitem__("sin_avatar", v)), \
         patch.object(bot, "ALLOWED_CHAT_IDS", {1}):
        asyncio.run(cmd(_Update(texto), type("X", (), {"args": args})()))
    return espia


def test_lotefish3_marca_el_lote_sin_presentador_y_solo_pide_crimen():
    espia = _correr(bot.cmd_lotefish3, "/lotefish3", ["5"])
    assert espia["sin_avatar"] is True
    assert espia["tramos"] and not set(espia["tramos"]) & {formatos.TRIVIA, formatos.MITO}


def test_un_lotegrande_despues_vuelve_a_tener_presentador():
    """Si la marca quedara puesta, el siguiente lote grande saldría sin presentadores."""
    with patch.object(bot.formatos, "repartir", lambda n: [("crimen", "de true crime", n)]):
        espia = _correr(bot.cmd_lotegrande, "/lotegrande", ["3", "variado"])
    assert espia["sin_avatar"] is False
