"""upload_cli.py nunca llamaba load_dotenv() -- confirmado en una corrida
real: fallaba con "Falta GOOGLE_DRIVE_FOLDER_ID en el .env del bot" pese a
que el .env sí lo tiene, porque la variable nunca llegaba al proceso."""

from pathlib import Path

_UPLOAD_CLI_SRC = Path(__file__).resolve().parents[1] / "src" / "dato_mata_gato_bot" / "upload_cli.py"


def test_upload_cli_carga_dotenv_antes_de_importar_pipeline():
    contenido = _UPLOAD_CLI_SRC.read_text(encoding="utf-8")
    idx_dotenv = contenido.index("load_dotenv()")
    idx_import_pipeline = contenido.index("import pipeline")
    assert idx_dotenv < idx_import_pipeline, (
        "load_dotenv() debe llamarse ANTES de importar pipeline -- si no, "
        "GOOGLE_DRIVE_FOLDER_ID (y cualquier otra variable de .env) nunca "
        "llega al proceso"
    )
