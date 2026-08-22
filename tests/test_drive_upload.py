from unittest.mock import MagicMock, patch

from dato_mata_gato_bot import drive_upload


def test_slugify_titulo_quita_acentos_espacios_y_simbolos() -> None:
    assert drive_upload.slugify_titulo("Criptografía") == "criptografia"
    assert drive_upload.slugify_titulo("El Chalequero: Caso 1") == "elchalequerocaso1"


def test_slugify_titulo_vacio_cae_a_video() -> None:
    assert drive_upload.slugify_titulo("") == "video"
    assert drive_upload.slugify_titulo("...") == "video"


def test_build_filename() -> None:
    assert drive_upload.build_filename("Criptografía", "25082026") == "criptografia_25082026.mp4"


@patch("dato_mata_gato_bot.drive_upload.get_drive_service")
@patch("dato_mata_gato_bot.drive_upload.MediaFileUpload")
def test_upload_video_sube_con_nombre_progresivo_y_folder(mock_media_cls, mock_get_service, tmp_path):
    local = tmp_path / "final.mp4"
    local.write_bytes(b"fake-mp4")

    mock_service = MagicMock()
    mock_get_service.return_value = mock_service
    mock_service.files.return_value.create.return_value.execute.return_value = {
        "id": "abc123", "webViewLink": "https://drive.google.com/file/d/abc123/view",
    }

    nombre, link = drive_upload.upload_video(local, "Criptografía", "25082026", "folder-id-1")

    assert nombre == "criptografia_25082026.mp4"
    assert link == "https://drive.google.com/file/d/abc123/view"
    _, kwargs = mock_service.files.return_value.create.call_args
    assert kwargs["body"] == {"name": "criptografia_25082026.mp4", "parents": ["folder-id-1"]}


@patch("dato_mata_gato_bot.drive_upload.get_drive_service")
@patch("dato_mata_gato_bot.drive_upload.MediaFileUpload")
def test_upload_video_arma_link_si_falta_webviewlink(mock_media_cls, mock_get_service, tmp_path):
    local = tmp_path / "final.mp4"
    local.write_bytes(b"fake-mp4")

    mock_service = MagicMock()
    mock_get_service.return_value = mock_service
    mock_service.files.return_value.create.return_value.execute.return_value = {"id": "xyz"}

    _, link = drive_upload.upload_video(local, "Algo", "26082026", "folder-id-1")
    assert link == "https://drive.google.com/file/d/xyz/view"
