import logging
import os
import sys
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler

# Log level from environment (default: INFO)
LOG_LEVEL = os.getenv("IIIF_LOG_LEVEL", "INFO").upper()

# Base log directory
LOG_BASE_DIR = Path("logs")
LOG_BASE_DIR.mkdir(parents=True, exist_ok=True)

# Shared formatters
CONSOLE_FORMAT = logging.Formatter(
    "%(levelname)s | %(name)s | %(message)s"
)

FILE_FORMAT = logging.Formatter(
    "%(asctime)s [%(levelname)s] [%(name)s.%(funcName)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Global flag to ensure setup only happens once
_LOGGING_CONFIGURED = False

# The primary application logger
app_logger = logging.getLogger("iiif_downloader")

def setup_logging():
    """Sets up the localized 'iiif_downloader' logger with daily rotation."""
    global _LOGGING_CONFIGURED
    
    # If already handles exist, we might just want to return. 
    # But clean and re-add allows changing LOG_LEVEL without restarting the process.
    if app_logger.handlers:
        app_logger.handlers.clear()
        
    # Set level from environment
    effective_level = getattr(logging, LOG_LEVEL, logging.INFO)
    app_logger.setLevel(effective_level)
    
    # Prevent logs from bubbling up to the root logger (keeps app.log isolated)
    app_logger.propagate = False

    # 1. Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(effective_level)
    console_handler.setFormatter(CONSOLE_FORMAT)
    app_logger.addHandler(console_handler)

    # 2. Daily Rotating File Handler
    log_file = LOG_BASE_DIR / "app.log"
    file_handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setLevel(effective_level)
    file_handler.setFormatter(FILE_FORMAT)
    app_logger.addHandler(file_handler)

    _LOGGING_CONFIGURED = True
    app_logger.info(f"Localized logging system initialized (Level: {LOG_LEVEL})")

def get_logger(name: str):
    """Get a configured logger within the 'iiif_downloader' namespace."""
    setup_logging()
    # Ensure name is relative to iiif_downloader if it's not already fully qualified
    if not name.startswith("iiif_downloader"):
        name = f"iiif_downloader.{name}"
    return logging.getLogger(name)

def get_download_logger(doc_id: str):
    """Get a logger instance for a specific download."""
    # Sanitize doc_id
    safe_id = "".join(c for c in doc_id if c.isalnum() or c in ('-', '_'))[:50]
    return get_logger(f"download.{safe_id}")
