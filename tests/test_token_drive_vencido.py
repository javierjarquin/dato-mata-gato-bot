"""Detección del token de Drive caducado.

Con la app de OAuth en 'Testing', Google caduca el refresh token a los 7 días
aunque se use. Escalarlo a Claude no sirve -- reautorizar exige que una
persona abra el navegador -- así que se le avisa al usuario con el comando.
"""

from dato_mata_gato_bot import pipeline


class _RefreshError(Exception):
    """Imita a google.auth.exceptions.RefreshError sin importar la librería."""


def test_reconoce_el_error_real_de_google():
    exc = _RefreshError(
        "('invalid_grant: Token has been expired or revoked.', "
        "{'error': 'invalid_grant', 'error_description': 'Token has been expired or revoked.'})"
    )
    assert pipeline._es_token_drive_vencido(exc) is True


def test_reconoce_la_variante_por_mensaje():
    assert pipeline._es_token_drive_vencido(Exception("Token has been expired or revoked")) is True


def test_no_confunde_otros_fallos_de_subida():
    # Estos SÍ deben escalar a Claude: no los puede resolver el usuario con
    # una reautorización.
    for msg in (
        "HttpError 404: File not found: 1N3kqrf",
        "Falta GOOGLE_DRIVE_FOLDER_ID en el .env del bot",
        "ConnectionResetError: [WinError 10054]",
        "storageQuotaExceeded",
    ):
        assert pipeline._es_token_drive_vencido(Exception(msg)) is False, msg


def test_el_mensaje_trae_el_comando_y_la_causa_de_fondo():
    texto = pipeline._MENSAJE_TOKEN_DRIVE.format(slug="guion-x")
    assert "drive_auth" in texto
    assert "guion-x" in texto
    # Y el arreglo permanente, para no repetir el trámite cada semana.
    assert "In production" in texto
