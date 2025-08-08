import base64
import enum
import logging
import mimetypes
import sys
from typing import Optional, Tuple

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

    def __str__(self):
        return self.name.title()

    @classmethod
    def from_level(cls, level: int) -> "DepthLevel":
        if level < 1:
            raise ValueError("Level must be at least 1")
        elif level > 4:
            return cls.PAGE
        return cls(level)
    


def file_to_b64(path: str) -> Optional[str]:
    try:
        with open(path, "rb") as file:
            data = file.read()
            file_b64 = base64.b64encode(data).decode('utf-8')
            return file_b64
    except Exception as e:
        logger.error(f"Error converting file to base64: {e}")
        return None

def is_image_file(file_path: str) -> bool:
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico', '.tiff'}
    return file_path.lower().endswith(tuple(image_extensions))

def image_to_data_url(image_path: str) -> Optional[str]:
    try:
        if not is_image_file(image_path):
            logger.warning(f"File is not an image: {image_path}")
            return None
        base64_data = file_to_b64(image_path)
        if not base64_data:
            return None
        
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type or not mime_type.startswith('image/'):
            ext = image_path.lower().split('.')[-1]
            mime_map = {
                '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                '.png': 'image/png', '.gif': 'image/gif',
                '.bmp': 'image/bmp', '.webp': 'image/webp',
                '.svg': 'image/svg+xml', '.ico': 'image/x-icon',
                '.tiff': 'image/tiff'
            }
            mime_type = mime_map.get(ext, 'image/png')
        data_url = f"data:{mime_type};base64,{base64_data}"
        
        return data_url
        
    except Exception as e:
        logger.error(f"Error creating data URL for {image_path}: {e}")
        return None
