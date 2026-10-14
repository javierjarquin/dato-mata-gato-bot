"""/vacamorada: un video de crimen de punta a punta, con el presentador.

Lo que hay que cuidar acá es que el comando haga el flujo ENTERO sin pedir
pasos intermedios, y que las verificaciones caras pasen antes de gastar una
llamada a Claude.
"""

import asyncio
from unittest.mock import patch

import pytest

from dato_mata_gato_bot import bot


class _Msg:
    def __init__(self, text=""):
        self.text = text
        self.replies = []

    async def reply_text(self, texto, **kwargs):
        self.replies.append(texto)


class _Update:
    def __init__(self, chat_id=1):
        self.effective_chat = type("C", (), {"id": chat_id})()
        self.message = _Msg()


class _Ctx:
    def __init__(self, args=None):
        self.args = args or []


def _correr(update, ctx, tmp_path, *, guiones=None, tts_falta="", avatar_falta="",
            resultado=None):
    """Corre /vacamorada con todo lo caro interceptado.

    Devuelve un dict con lo que el comando intentó hacer.
    """
    espia = {"pipeline": None, "pedido_a_claude": None, "enviados": []}

    def _fake_pipeline_run(slug, voz, chat_id, avatar=False, avatar_num=None):
        espia["pipeline"] = {"slug": slug, "voz": voz, "avatar": avatar,
                             "avatar_num": avatar_num}
        return resultado or bot.pipeline.PipelineResult(True, "listo")

    async def _fake_guiones(update_, session_id, is_new, cantidad, desc="x"):
        espia["pedido_a_claude"] = cantidad
        return guiones if guiones is not None else []

    async def _fake_send_long(update_, texto):
        espia["enviados"].append(texto)

    with patch.object(bot, "ANDROID_IN", tmp_path), \
         patch.object(bot, "_guiones_de_crimen", _fake_guiones), \
         patch.object(bot, "_send_long", _fake_send_long), \
         patch.object(bot.pipeline, "run", _fake_pipeline_run), \
         patch.object(bot.pipeline, "motor_tts_listo", lambda: tts_falta), \
         patch.object(bot.avatar_presentador, "disponible",
                      lambda n=None: avatar_falta), \
         patch.object(bot.sessions, "get_generating", lambda c: (False, None)), \
         patch.object(bot.sessions, "set_generating", lambda c, v: None), \
         patch.object(bot.sessions, "set_progress", lambda c, v: None), \
         patch.object(bot.sessions, "set_phase", lambda c, v: None), \
         patch.object(bot.sessions, "get_voice", lambda c: "am_adam"), \
         patch.object(bot.sessions, "ensure_session_id", lambda c: ("sid", True)), \
         patch.object(bot.sessions, "get_pending_batch", lambda c: []), \
         patch.object(bot.sessions, "set_pending_batch", lambda c, s: None), \
         patch.object(bot, "ALLOWED_CHAT_IDS", {1}):
        asyncio.run(bot.cmd_vacamorada(update, ctx))
    return espia


def _con_guion(tmp_path, slug):
    (tmp_path / slug).mkdir(parents=True, exist_ok=True)
    (tmp_path / slug / "guion.json").write_text("{}", encoding="utf-8")


def test_sin_argumentos_escribe_el_guion_y_genera(tmp_path):
    """El flujo entero: no debería hacer falta /crimen antes."""
    _con_guion(tmp_path, "guion-caso")
    espia = _correr(
        _Update(), _Ctx(), tmp_path,
        guiones=[{"slug": "guion-caso", "titulo": "Un caso", "resumen_hechos": "Pasó esto."}],
    )
    assert espia["pedido_a_claude"] == 1
    assert espia["pipeline"] == {"slug": "guion-caso", "voz": "am_adam",
                                 "avatar": True, "avatar_num": None}


def test_muestra_el_guion_antes_de_generar(tmp_path):
    """Sin pausa para revisar, pero los hechos tienen que estar a la vista."""
    _con_guion(tmp_path, "guion-caso")
    espia = _correr(
        _Update(), _Ctx(), tmp_path,
        guiones=[{"slug": "guion-caso", "titulo": "Un caso", "resumen_hechos": "Pasó esto."}],
    )
    resumenes = [t for t in espia["enviados"] if "Pasó esto." in t]
    assert resumenes, "el resumen de hechos tiene que mostrarse antes de generar"
    assert "Un caso" in resumenes[0]


def test_con_slug_no_le_pide_nada_a_claude(tmp_path):
    """Reintentar un guion ya escrito no debe costar otra llamada."""
    _con_guion(tmp_path, "guion-viejo")
    espia = _correr(_Update(), _Ctx(["guion-viejo"]), tmp_path)
    assert espia["pedido_a_claude"] is None
    assert espia["pipeline"]["slug"] == "guion-viejo"
    assert espia["pipeline"]["avatar"] is True


def test_no_gasta_claude_si_falta_el_motor_de_voz(tmp_path):
    espia = _correr(_Update(), _Ctx(), tmp_path, tts_falta="VoiceStudio está caído")
    assert espia["pedido_a_claude"] is None
    assert espia["pipeline"] is None


def test_no_gasta_claude_si_no_esta_el_presentador(tmp_path):
    espia = _correr(_Update(), _Ctx(), tmp_path, avatar_falta="Falta la placa")
    assert espia["pedido_a_claude"] is None
    assert espia["pipeline"] is None


def test_no_genera_si_claude_no_devolvio_guion(tmp_path):
    espia = _correr(_Update(), _Ctx(), tmp_path, guiones=[])
    assert espia["pipeline"] is None


def test_no_genera_si_el_guion_no_quedo_en_disco(tmp_path):
    """Claude puede contestar la lista y no haber escrito el archivo."""
    espia = _correr(
        _Update(), _Ctx(), tmp_path,
        guiones=[{"slug": "guion-fantasma", "titulo": "X", "resumen_hechos": "Y"}],
    )
    assert espia["pipeline"] is None


def test_numero_elige_el_avatar(tmp_path):
    """/vacamorada 1 usa el segundo presentador, no el de siempre."""
    _con_guion(tmp_path, "guion-caso")
    espia = _correr(
        _Update(), _Ctx(["1"]), tmp_path,
        guiones=[{"slug": "guion-caso", "titulo": "X", "resumen_hechos": "Y"}],
    )
    assert espia["pipeline"]["avatar_num"] == 1


def test_numero_y_slug_en_cualquier_orden(tmp_path):
    """El número es el avatar y lo demás el slug, venga como venga."""
    _con_guion(tmp_path, "guion-viejo")
    for args in (["1", "guion-viejo"], ["guion-viejo", "1"]):
        espia = _correr(_Update(), _Ctx(args), tmp_path)
        assert espia["pipeline"]["slug"] == "guion-viejo", args
        assert espia["pipeline"]["avatar_num"] == 1, args
        assert espia["pedido_a_claude"] is None, args


def test_avatar_inexistente_no_genera(tmp_path):
    espia = _correr(_Update(), _Ctx(["7"]), tmp_path,
                    avatar_falta="No existe el avatar 7. Disponibles: 0, 1")
    assert espia["pipeline"] is None
    assert espia["pedido_a_claude"] is None


@pytest.mark.parametrize("campo", ["slug", None])
def test_guion_sin_slug_no_genera(tmp_path, campo):
    guion = {"titulo": "X", "resumen_hechos": "Y"}
    if campo:
        guion[campo] = ""
    espia = _correr(_Update(), _Ctx(), tmp_path, guiones=[guion])
    assert espia["pipeline"] is None
