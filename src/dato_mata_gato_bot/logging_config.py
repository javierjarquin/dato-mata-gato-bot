import logging
from logging.handlers import RotatingFileHandler

from dato_mata_gato_bot import canal

# Un log por canal (15/11/2026): `data/bot.log` y `data/papasia/bot.log`. Antes
# los dos bots escribían en el mismo archivo y rotaban cada uno por su lado.
LOG_PATH = canal.data_dir() / "bot.log"


def setup_logging(level: str = "INFO") -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s — %(message)s")

    file_handler = RotatingFileHandler(LOG_PATH, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(file_handler)

    # httpx escribe en INFO cada consulta a Telegram con la URL completa, y la
    # URL trae el TOKEN del bot: quedaba en claro en el log cada 10 segundos.
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Con pythonw.exe no hay consola; agregar el StreamHandler igual no
    # estorba cuando SÍ corre con consola (ej. durante desarrollo).
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)
    root.addHandler(stream_handler)
