"""No tirar trabajo al escribir guiones (20/10/2026): rescate del disco tras un
corte, completar lo que faltó en la misma sesión, y de 2 en 2 por ventana."""
import asyncio
import json
from datetime import datetime
from types import SimpleNamespace

import pytest

from dato_mata_gato_bot import bot, claude_runner, fabrica, pipeline


class _Avisos:
    def __init__(self):
        self.textos = []
        self.message = SimpleNamespace(reply_text=self._r)

    async def _r(self, t, **_):
        self.textos.append(t)


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "ANDROID_IN", tmp_path)
    monkeypatch.setattr(bot, "_sesion_nueva", lambda: ("s1", True))
    turnos = []

    def guion(slug):
        (tmp_path / slug).mkdir(exist_ok=True)
        (tmp_path / slug / "guion.json").write_text("{}", encoding="utf-8")

    return tmp_path, turnos, guion


def _correr(turnos_respuestas, turnos, revisar=lambda s: [], cantidad=2):
    def run_turn(sid, msg, nueva, ligera):
        turnos.append(msg)
        return turnos_respuestas[len(turnos) - 1]()
    import dato_mata_gato_bot.claude_runner as cr
    viejo = cr.run_turn
    cr.run_turn = run_turn
    try:
        avisos = _Avisos()
        res = asyncio.run(fabrica._escribir_y_rescatar(avisos, "la polémica", "instr", cantidad,
                                                       "guion-polemica-", revisar, True))
        return res, avisos
    finally:
        cr.run_turn = viejo


def test_corte_de_conexion_rescata_del_disco_y_retoma(entorno):
    tmp, turnos, guion = entorno
    ok = lambda t: claude_runner.ClaudeTurnResult(ok=True, text=t, raw="")

    def cortada():
        guion("guion-polemica-a")
        return claude_runner.ClaudeTurnResult(ok=False, text="API Error: Connection closed mid-response", raw="")

    def segunda():
        guion("guion-polemica-b")
        return ok('```json\n{"guiones": [{"slug": "guion-polemica-a"}, {"slug": "guion-polemica-b"}]}\n```')

    (buenos, sesiones), _ = _correr([cortada, segunda], turnos)
    assert sorted(g["slug"] for g in buenos) == ["guion-polemica-a", "guion-polemica-b"]
    assert len(turnos) == 2 and "Se cortó la conexión" in turnos[1]


def test_entrego_menos_y_pregunto_se_le_pide_en_la_misma_sesion(entorno):
    tmp, turnos, guion = entorno
    ok = lambda t: claude_runner.ClaudeTurnResult(ok=True, text=t, raw="")

    def uno():
        guion("guion-polemica-a")
        return ok("Entrego uno y no dos. Si quieres el segundo, dime cuál y lo escribo.")

    def dos():
        guion("guion-polemica-b")
        return ok("listo")

    (buenos, _), _ = _correr([uno, dos], turnos)
    assert len(buenos) == 2
    assert "Faltan 1 guion" in turnos[1] and "nadie va a contestar" in turnos[1]


def test_cuota_agotada_conserva_lo_que_paso(entorno):
    tmp, turnos, guion = entorno

    def limite():
        guion("guion-polemica-a")
        return claude_runner.ClaudeTurnResult(ok=False, text="You've hit your session limit · resets 3pm", raw="")

    with pytest.raises(bot.LimiteDeClaude) as exc:
        _correr([limite], turnos)
    assert exc.value.slugs == ["guion-polemica-a"]


def test_de_dos_en_dos_limita_guiones_por_ventana():
    ahora = datetime(2026, 10, 20, 12, 0)
    estado = {"horas_claude": "", "guiones_5h": 6,
              "consumo": [{"t": "2026-10-20T09:00", "guiones": 2, "pedidos": 2},
                          {"t": "2026-10-20T10:00", "guiones": 1, "pedidos": 2}]}
    assert fabrica.puede_usar_claude(estado, ahora) is None
    estado["consumo"].append({"t": "2026-10-20T11:00", "guiones": 2, "pedidos": 2})
    assert "6 guiones" in fabrica.puede_usar_claude(estado, ahora)
