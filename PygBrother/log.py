import logging
from typing import Optional

_logger: Optional[logging.Logger] = None

def get_logger() -> logging.Logger:
    global _logger
    if _logger is None:
        _logger = logging.getLogger("PygBrother")
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s')
        handler.setFormatter(formatter)
        _logger.addHandler(handler)
        _logger.setLevel(logging.INFO)
    return _logger
