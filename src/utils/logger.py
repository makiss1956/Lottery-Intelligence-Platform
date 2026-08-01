import logging
import os
from datetime import datetime

def setup_logger(name: str = "LotteryApp", log_file: str = "app.log", level=logging.INFO) -> logging.Logger:
    """
    Sets up and returns a configured logger instance.
    """
    os.makedirs("logs", exist_ok=True)
    full_log_path = os.path.join("logs", log_file)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        file_handler = logging.FileHandler(full_log_path)
        stream_handler = logging.StreamHandler()

        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        file_handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

    return logger
