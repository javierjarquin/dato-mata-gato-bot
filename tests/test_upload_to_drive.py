"""_upload_to_drive lee GOOGLE_DRIVE_FOLDER_ID en el momento de subir, no
como constante de módulo -- bot.py importa pipeline ANTES de llamar
load_dotenv(), así que una constante de módulo quedaba fija en "" para
siempre sin importar qué tuviera el .env (bug real confirmado: la subida
fallaba con "Falta GOOGLE_DRIVE_FOLDER_ID" pese a que el .env sí lo tenía)."""

from unittest.mock import patch

import pytest

from dato_mata_gato_bot import pipeline


def test_upload_to_drive_falla_si_no_hay_folder_id(monkeypatch):
    monkeypatch.delenv("GOOGLE_DRIVE_FOLDER_ID", raising=False)
    with pytest.raises(RuntimeError, match="Falta GOOGLE_DRIVE_FOLDER_ID"):
        pipeline._upload_to_drive("guion-inexistente")


@patch("dato_mata_gato_bot.pipeline.publish_schedule")
@patch("dato_mata_gato_bot.pipeline.drive_upload")
def test_upload_to_drive_lee_el_folder_id_puesto_despues_del_import(
    mock_drive_upload, mock_publish_schedule, tmp_path, monkeypatch
):
    # Simula el escenario real: el proceso ya está corriendo (el módulo ya
    # se importó) y GOOGLE_DRIVE_FOLDER_ID recién se vuelve visible después
    # (load_dotenv() corriendo tarde, o el .env cambiando en caliente) --
    # una constante de módulo NUNCA vería este valor; leerlo adentro de la
    # función sí.
    monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "folder-puesto-despues-del-import")
    monkeypatch.setattr(pipeline, "NARRATOR_PROJECTS", tmp_path)
    project = tmp_path / "guion-x"
    project.mkdir()
    (project / "guion.json").write_text('{"titulo": "X"}', encoding="utf-8")
    (project / "final.mp4").write_bytes(b"fake")

    mock_publish_schedule.assign_date.return_value = "25082026"
    mock_drive_upload.upload_video.return_value = ("x_25082026.mp4", "https://drive/x")

    pipeline._upload_to_drive("guion-x")

    args = mock_drive_upload.upload_video.call_args.args
    assert args[-1] == "folder-puesto-despues-del-import"
