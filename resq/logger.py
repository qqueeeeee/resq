import logging
import sys
from logging.handlers import RotatingFileHandler

_logger = logging.getLogger("resq")
_logger.setLevel(logging.INFO)
_logger.propagate = False


def init_log(path: str = "resq.log", debug: bool = False):
    _logger.handlers.clear()
    _logger.setLevel(logging.DEBUG if debug else logging.INFO)

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    file_handler = RotatingFileHandler(path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    _logger.addHandler(file_handler)

    if debug:
        stream = logging.StreamHandler(sys.stdout)
        stream.setFormatter(formatter)
        stream.setLevel(logging.DEBUG)
        _logger.addHandler(stream)


def log(msg: str, level: str = "info"):
    if not _logger.handlers:
        init_log()

    levels = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
    }
    _logger.log(levels.get(level, logging.INFO), msg)
