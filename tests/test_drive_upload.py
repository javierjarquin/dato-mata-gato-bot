from unittest.mock import MagicMock, patch

import pytest

from dato_mata_gato_bot import drive_upload


def test_slugify_titulo_quita_acentos_espacios_y_simbolos() -> None:
    assert drive_upload.slugify_titulo("Criptografía") == "criptografia"
    assert drive_upload.slugify_titulo("El Chalequero: Caso 1") == "elchalequerocaso1"


def test_slugify_titulo_vacio_cae_a_video() -> None:
    assert drive_upload.slugify_titulo("") == "video"
    assert drive_upload.slugify_titulo("...") == "video"


def test_build_filename() -> None:
    assert drive_upload.build_filename("Criptografía", "25082026") == "criptografia_25082026.mp4"


def _servicio_que_sube(respuesta, errores_antes=0):
    """Servicio de Drive falso. La subida es por trozos: next_chunk() devuelve
    (progreso, None) mientras quedan trozos, y (None, respuesta) al terminar."""
    servicio = MagicMock()
    pedido = servicio.files.return_value.create.return_value
    restantes = {"errores": errores_antes}

    def next_chunk(num_retries=0):
        if restantes["errores"]:
            restantes["errores"] -= 1
            raise OSError("EOF occurred in violation of protocol")
        return None, respuesta

    pedido.next_chunk.side_effect = next_chunk
    return servicio


@patch("dato_mata_gato_bot.drive_upload.get_drive_service")
@patch("dato_mata_gato_bot.drive_upload.MediaFileUpload")
def test_upload_video_sube_con_nombre_progresivo_y_folder(mock_media_cls, mock_get_service, tmp_path):
    local = tmp_path / "final.mp4"
    local.write_bytes(b"fake-mp4")
    servicio = _servicio_que_sube(
        {"id": "abc123", "webViewLink": "https://drive.google.com/file/d/abc123/view"}
    )
    mock_get_service.return_value = servicio

    nombre, link = drive_upload.upload_video(local, "Criptografía", "25082026", "folder-id-1")

    assert nombre == "criptografia_25082026.mp4"
    assert link == "https://drive.google.com/file/d/abc123/view"
    _, kwargs = servicio.files.return_value.create.call_args
    assert kwargs["body"] == {"name": "criptografia_25082026.mp4", "parents": ["folder-id-1"]}


@patch("dato_mata_gato_bot.drive_upload.get_drive_service")
@patch("dato_mata_gato_bot.drive_upload.MediaFileUpload")
def test_upload_video_arma_link_si_falta_webviewlink(mock_media_cls, mock_get_service, tmp_path):
    local = tmp_path / "final.mp4"
    local.write_bytes(b"fake-mp4")
    mock_get_service.return_value = _servicio_que_sube({"id": "xyz"})

    _, link = drive_upload.upload_video(local, "Algo", "26082026", "folder-id-1")
    assert link == "https://drive.google.com/file/d/xyz/view"


@patch("dato_mata_gato_bot.drive_upload.time.sleep")
@patch("dato_mata_gato_bot.drive_upload.get_drive_service")
@patch("dato_mata_gato_bot.drive_upload.MediaFileUpload")
def test_un_corte_de_tls_se_reintenta_sobre_el_mismo_pedido(
    mock_media_cls, mock_get_service, _sleep, tmp_path
):
    # Es lo que pasaba subiendo trozos de 46 MB: el TLS cortaba con
    # SSLEOFError y la subida entera moría. Ahora reintenta el trozo.
    local = tmp_path / "final.mp4"
    local.write_bytes(b"fake-mp4")
    servicio = _servicio_que_sube({"id": "ok1"}, errores_antes=3)
    mock_get_service.return_value = servicio

    _, link = drive_upload.subir_archivo(local, "x.mp4", "folder-1")

    assert link.endswith("ok1/view")
    # Un solo create(): se reintentó el MISMO pedido, que conserva la sesión
    # resumible, en vez de empezar el archivo de cero.
    assert servicio.files.return_value.create.call_count == 1


@patch("dato_mata_gato_bot.drive_upload.time.sleep")
@patch("dato_mata_gato_bot.drive_upload.get_drive_service")
@patch("dato_mata_gato_bot.drive_upload.MediaFileUpload")
def test_si_los_cortes_no_paran_el_error_sale_a_la_luz(
    mock_media_cls, mock_get_service, _sleep, tmp_path
):
    # Reintentar para siempre dejaría un troceo colgado sin que nadie se entere.
    local = tmp_path / "final.mp4"
    local.write_bytes(b"fake-mp4")
    mock_get_service.return_value = _servicio_que_sube({"id": "no"}, errores_antes=99)

    with pytest.raises(OSError):
        drive_upload.subir_archivo(local, "x.mp4", "folder-1")


@patch("dato_mata_gato_bot.drive_upload.get_drive_service")
@patch("dato_mata_gato_bot.drive_upload.MediaFileUpload")
def test_con_reusar_existente_no_vuelve_a_subir(mock_media_cls, mock_get_service, tmp_path):
    # Retomar un troceo cortado no debe dejar cada trozo duplicado: Drive
    # acepta nombres repetidos en la misma carpeta sin chistar.
    local = tmp_path / "final.mp4"
    local.write_bytes(b"fake-mp4")
    servicio = MagicMock()
    servicio.files.return_value.list.return_value.execute.return_value = {
        "files": [{"id": "ya", "name": "x.mp4", "webViewLink": "https://drive/ya"}]
    }
    mock_get_service.return_value = servicio

    nombre, link = drive_upload.subir_archivo(local, "x.mp4", "folder-1", reusar_existente=True)

    assert (nombre, link) == ("x.mp4", "https://drive/ya")
    servicio.files.return_value.create.assert_not_called()
