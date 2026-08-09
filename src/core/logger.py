import logging
import sys
from pathlib import Path
from typing import Optional


def get_logger(name: str = "LotteryIntelligence", log_file: Optional[str] = "app.log") -> logging.Logger:
    """
    Centralized production logger for the Lottery Intelligence Platform.
    Provides consistent log formatting across all modules.
    """
    logger = logging.getLogger(name)
    
    # Avoid adding multiple handlers if already configured
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # Formatter configuration
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler
    if log_file:
        # Υπολογισμός του project root: 3 επίπεδα πάνω από το logger.py (core -> src -> root)
        log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_dir / log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# Global instance for quick access
logger = get_logger()
