"""Pausas de silencio entre planos -- base del formato de preguntas.

El clip de un plano dura hasta el inicio del siguiente (ver
render_timeline.py en illustrated-narrator), así que un silencio insertado
después de la pregunta se convierte en tiempo de pregunta en pantalla, sin
tocar el ensamblador.
"""

import wave

from dato_mata_gato_bot import pipeline


def test_pausa_ausente_o_cero_no_agrega_silencio():
    assert pipeline._pausa_despues_seg({"id": "p00"}) == 0.0
    assert pipeline._pausa_despues_seg({"id": "p00", "pausa_despues_seg": 0}) == 0.0


def test_pausa_valida_se_respeta():
    assert pipeline._pausa_despues_seg({"id": "p01", "pausa_despues_seg": 3.5}) == 3.5


def test_pausa_se_recorta_al_maximo():
    # Un valor absurdo dejaría el video con un hueco enorme; se acota.
    assert pipeline._pausa_despues_seg({"id": "p01", "pausa_despues_seg": 600}) == 15.0


def test_pausa_invalida_se_ignora_en_vez_de_romper():
    assert pipeline._pausa_despues_seg({"id": "p01", "pausa_despues_seg": "tres"}) == 0.0
    assert pipeline._pausa_despues_seg({"id": "p01", "pausa_despues_seg": None}) == 0.0


def test_silencio_generado_coincide_con_el_formato_de_kokoro(tmp_path):
    # El concat demuxer de ffmpeg exige mismo sample rate y canales que los
    # WAV de Kokoro (pcm_s16le, 24000 Hz, mono); si no, el audio sale
    # corrupto o el concat falla.
    destino = pipeline._generar_silencio(tmp_path, "p01", 2.0)

    assert destino.exists()
    with wave.open(str(destino)) as w:
        assert w.getframerate() == 24000
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 2  # 16 bits
        duracion = w.getnframes() / w.getframerate()
    assert abs(duracion - 2.0) < 0.05


# --- motor de TTS: seleccion de voz y timeout ------------------------------

def test_con_voicestudio_no_se_pasa_voz_de_kokoro(monkeypatch):
    # El bot pasa siempre --voz con un nombre de Kokoro (am_adam). En
    # VoiceStudio la voz es un profile_id de esa instancia: mandarle am_adam
    # lo hace fallar. Se omite --voz para que use VOICESTUDIO_VOICE_ID.
    monkeypatch.setenv("TTS_ENGINE", "voicestudio")
    capturado = {}

    def _fake_run(args, cwd=None, env=None, timeout=None):
        capturado["args"] = args
        capturado["timeout"] = timeout
        return type("P", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(pipeline, "_run", _fake_run)
    pipeline._generate_audio("slug-x", voz="am_adam")

    assert "--voz" not in capturado["args"]
    # Y con timeout propio: a 13x, un episodio largo no entra en el general.
    assert capturado["timeout"] == pipeline.TIMEOUT_AUDIO_VOICESTUDIO


def test_con_kokoro_se_sigue_pasando_la_voz(monkeypatch):
    monkeypatch.setenv("TTS_ENGINE", "kokoro")
    capturado = {}

    def _fake_run(args, cwd=None, env=None, timeout=None):
        capturado["args"] = args
        capturado["timeout"] = timeout
        return type("P", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(pipeline, "_run", _fake_run)
    pipeline._generate_audio("slug-x", voz="am_adam")

    assert "--voz" in capturado["args"]
    assert capturado["args"][capturado["args"].index("--voz") + 1] == "am_adam"
    assert capturado["timeout"] is None  # usa el general


def test_el_timeout_de_audio_cubre_el_episodio_mas_largo():
    # 604s es la narración más larga que existe en projects/.
    assert 604 * 13 < pipeline.TIMEOUT_AUDIO_VOICESTUDIO
