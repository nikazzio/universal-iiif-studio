import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


def _get_configured_log_level() -> str:
    try:
        from .config_manager import get_config_manager

        cm = get_config_manager()
        level = cm.get_setting("logging.level", "INFO")
        return str(level or "INFO").upper()
    except (ImportError, OSError, ValueError, RuntimeError):
        return "INFO"


def _get_logs_dir() -> Path:
    try:
        from .config_manager import get_config_manager

        return get_config_manager().get_logs_dir()
    except (ImportError, OSError, ValueError, RuntimeError):
        return Path("logs")


# Base log directory
LOG_BASE_DIR = _get_logs_dir()
try:
    LOG_BASE_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    # Fall back to CWD logs if configured path isn't writable
    LOG_BASE_DIR = Path("logs")
    LOG_BASE_DIR.mkdir(parents=True, exist_ok=True)

# Shared formatters
CONSOLE_FORMAT = logging.Formatter("%(levelname)s | %(name)s | %(message)s")

FILE_FORMAT = logging.Formatter(
    "%(asctime)s [%(levelname)s] [%(name)s.%(funcName)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# The primary application logger
app_logger = logging.getLogger("iiif_downloader")
app_logger.propagate = True


def setup_logging():
    """Sets up the localized 'iiif_downloader' logger with daily rotation."""
    log_level = _get_configured_log_level()
    effective_level = getattr(logging, log_level, logging.INFO)

    # Ensure DIR exists again just in case
    LOG_BASE_DIR.mkdir(parents=True, exist_ok=True)

    if app_logger.hasHandlers():
        if app_logger.level != effective_level:
            app_logger.setLevel(effective_level)
            for h in app_logger.handlers:
                h.setLevel(effective_level)
        return

    app_logger.setLevel(effective_level)

    # Handlers
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(CONSOLE_FORMAT)
    console_handler.setLevel(effective_level)  # Ensure handler level is set
    app_logger.addHandler(console_handler)

    log_file = LOG_BASE_DIR / "app.log"
    try:
        file_handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=30, encoding="utf-8")
        file_handler.setFormatter(FILE_FORMAT)
        file_handler.setLevel(effective_level)  # Ensure handler level is set
        app_logger.addHandler(file_handler)
    except Exception as e:
        sys.stderr.write(f"FAILED TO SETUP FILE LOGGING: {e}\n")
        # Fallback: at least console handler should work
        app_logger.error(f"Failed to setup file logging: {e}", exc_info=True)

    app_logger.info("Localized logging system initialized (Level: %s) -> %s", log_level, log_file)


def summarize_for_debug(data: str, max_chars: int = 200) -> str:
    """Summarize a large string for debug logs."""
    if not data or len(data) <= max_chars:
        return data
    return f"{data[:max_chars]}... [TRUNCATED, total {len(data)} chars]"


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
    safe_id = "".join(c for c in doc_id if c.isalnum() or c in ("-", "_"))[:50]
    return get_logger(f"download.{safe_id}")
