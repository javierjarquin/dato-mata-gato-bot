import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parents[2] / "data" / "bot.log"


def setup_logging(level: str = "INFO") -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s — %(message)s")

    file_handler = RotatingFileHandler(LOG_PATH, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(file_handler)

    # Con pythonw.exe no hay consola; agregar el StreamHandler igual no
    # estorba cuando SÍ corre con consola (ej. durante desarrollo).
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)
    root.addHandler(stream_handler)
