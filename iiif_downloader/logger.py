import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


def _get_configured_log_level() -> str:
    try:
        from iiif_downloader.config_manager import get_config_manager

        cm = get_config_manager()
        level = cm.get_setting("logging.level", "INFO")
        return str(level or "INFO").upper()
    except (ImportError, OSError, ValueError, RuntimeError):
        return "INFO"


def _get_logs_dir() -> Path:
    try:
        from iiif_downloader.config_manager import get_config_manager

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

# Internal state to avoid re-initializing handlers on every get_logger() call.
_STATE: dict[str, object] = {"initialized": False, "last_level": None}


def setup_logging():
    """Sets up the localized 'iiif_downloader' logger with daily rotation."""
    log_level = _get_configured_log_level()
    effective_level = getattr(logging, log_level, logging.INFO)

    # Check existence of handlers to detect prior initialization
    # (Checking _STATE is insufficient if module is reloaded in Streamlit)
    if app_logger.hasHandlers():
        # Only update if level actually changed
        if app_logger.level != effective_level:
            app_logger.setLevel(effective_level)
            for h in app_logger.handlers:
                try:
                    h.setLevel(effective_level)
                except (TypeError, ValueError, AttributeError):
                    pass
            app_logger.info("Logging level updated (Level: %s)", log_level)

        _STATE["initialized"] = True
        _STATE["last_level"] = log_level
        return

    # First-time configuration.
    app_logger.setLevel(effective_level)
    app_logger.propagate = False

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(effective_level)
    console_handler.setFormatter(CONSOLE_FORMAT)
    app_logger.addHandler(console_handler)

    log_file = LOG_BASE_DIR / "app.log"
    file_handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setLevel(effective_level)
    file_handler.setFormatter(FILE_FORMAT)
    app_logger.addHandler(file_handler)

    _STATE["initialized"] = True
    _STATE["last_level"] = log_level
    app_logger.info("Localized logging system initialized (Level: %s)", log_level)


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
