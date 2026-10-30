import pytest


@pytest.fixture(autouse=True)
def _sin_docker_real(monkeypatch):
    """pipeline.run levanta Docker/VoiceStudio antes de la voz (14/10/2026). En
    los tests eso no puede pasar: arrancaría Docker Desktop de verdad."""
    from dato_mata_gato_bot import fabrica

    monkeypatch.setattr(fabrica, "asegurar_infra", lambda: None)


@pytest.fixture(autouse=True)
def _sin_expediente(monkeypatch):
    """El expediente (27/10/2026) sale a Google News, Bing y Gemini. Los tests de
    la fábrica no pueden depender de la red: va apagado salvo en sus tests."""
    monkeypatch.setenv("FABRICA_EXPEDIENTE", "0")
