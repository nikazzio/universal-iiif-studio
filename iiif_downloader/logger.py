"""
Centralized logging configuration for IIIF Downloader.

Provides structured logging with:
- File organization by date (logs/YYYY-MM-DD/)
- Session-based log files
- Configurable log levels via environment variable
- Console + file output
"""
import logging
import os
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler


# Log level from environment (default: INFO)
LOG_LEVEL = os.getenv("IIIF_LOG_LEVEL", "INFO").upper()

# Base log directory
LOG_BASE_DIR = Path("logs")

# Create logs directory structure
def _get_log_dir():
    """Get today's log directory, creating it if needed."""
    today = datetime.now().strftime("%Y-%m-%d")
    log_dir = LOG_BASE_DIR / today
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


# Shared formatters
CONSOLE_FORMAT = logging.Formatter(
    "%(levelname)-8s | %(name)-20s | %(message)s"
)

FILE_FORMAT = logging.Formatter(
    "%(asctime)s [%(levelname)-8s] [%(name)s.%(funcName)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


def get_logger(name: str, log_file: str = None):
    """
    Get or create a configured logger.
    
    Args:
        name: Logger name (usually __name__)
        log_file: Optional specific log file name (without path)
                 If None, uses 'session_HHMMSS.log'
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    logger.setLevel(LOG_LEVEL)
    
    # Console handler (INFO and above)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(CONSOLE_FORMAT)
    logger.addHandler(console_handler)
    
    # File handler (DEBUG and above)
    log_dir = _get_log_dir()
    
    if log_file is None:
        timestamp = datetime.now().strftime("%H%M%S")
        log_file = f"session_{timestamp}.log"
    
    file_path = log_dir / log_file
    file_handler = logging.FileHandler(file_path, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(FILE_FORMAT)
    logger.addHandler(file_handler)
    
    logger.debug(f"Logger initialized: {name}")
    return logger


def get_download_logger(doc_id: str):
    """
    Get a logger for a specific document download.
    
    Args:
        doc_id: Document identifier
        
    Returns:
        Configured logger with dedicated file
    """
    timestamp = datetime.now().strftime("%H%M%S")
    # Sanitize doc_id for filename
    safe_id = "".join(c for c in doc_id if c.isalnum() or c in ('-', '_'))[:50]
    log_file = f"download_{safe_id}_{timestamp}.log"
    
    return get_logger(f"iiif_downloader.download.{safe_id}", log_file)
