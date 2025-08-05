import enum
import logging
import sys
from typing import Optional


class Logger:

    _instance: Optional["Logger"] = None
    _logger: Optional[logging.Logger] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._logger is None:
            self._setup_logger()

    def _setup_logger(self):
        self._logger = logging.getLogger("confluence_to_bookstack")
        self._logger.setLevel(logging.DEBUG)
        if not self._logger.handlers:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.DEBUG)

            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            console_handler.setFormatter(formatter)

            self._logger.addHandler(console_handler)

    def info(self, message: str):
        self._logger.info(message)

    def error(self, message: str):
        self._logger.error(message)

    def warning(self, message: str):
        self._logger.warning(message)

    def debug(self, message: str):
        self._logger.debug(message)


logger = Logger()


class DepthLevel(enum.Enum):
    SHELF = 1
    BOOK = 2
    CHAPTER = 3
    PAGE = 4

    @classmethod
    def from_level(cls, level: int) -> "DepthLevel":
        if level < 1:
            raise ValueError("Level must be at least 1")
        elif level > 4:
            return cls.PAGE
        return cls(level)