import os
import sys
import time
import logging
from logging.handlers import RotatingFileHandler


def setup_logger(name: str = "FrankyAutoMate") -> logging.Logger:
    """Configures and returns the central logger for the application."""
    logger = logging.getLogger(name)

    # Avoid duplicating handlers if logger is already configured
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.INFO)

    # Ensure logs directory exists
    log_dir = os.path.join(os.getenv("APPDATA", os.getcwd()), "FrankyAutoMate", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"automate_{time.strftime('%Y%m%d')}.log")

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    # File Handler
    file_handler = RotatingFileHandler(log_file, encoding="utf-8", maxBytes=5 * 1024 * 1024, backupCount=7)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# Global default logger instance
logger = setup_logger()
