import pytest


@pytest.fixture(autouse=True)
def _sin_docker_real(monkeypatch):
    """pipeline.run levanta Docker/VoiceStudio antes de la voz (14/10/2026). En
    los tests eso no puede pasar: arrancaría Docker Desktop de verdad."""
    from dato_mata_gato_bot import fabrica

    monkeypatch.setattr(fabrica, "asegurar_infra", lambda: None)
