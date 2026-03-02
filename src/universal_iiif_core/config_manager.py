"""Local configuration manager for secrets and user paths.

This module is designed to work both in normal Python execution and when
packaged (e.g., stlite-desktop). It stores user-editable values in a local
`config.json` file.

`config.json` is the single source of truth at runtime.
"""

from __future__ import annotations

import json
from contextlib import suppress
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from .logger import get_logger

logger = get_logger(__name__)


DEFAULT_CONFIG_JSON: dict[str, Any] = {
    "paths": {
        "downloads_dir": "data/local/downloads",
        "exports_dir": "data/local/exports",
        "temp_dir": "data/local/temp_images",
        "models_dir": "data/local/models",
        "logs_dir": "data/local/logs",
        "snippets_dir": "data/local/snippets",
    },
    "security": {
        "allowed_origins": [
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
    },
    "api_keys": {
        "openai": "",
        "anthropic": "",
        "google_vision": "",
        "huggingface": "",
    },
    "settings": {
        "system": {
            "max_concurrent_downloads": 2,
        },
        "defaults": {
            "default_library": "Vaticana",
            "preferred_ocr_engine": "openai",
        },
        "library": {
            "default_mode": "operativa",
        },
        "ui": {
            "theme_preset": "rosewater",
            "theme_primary_color": "#7B8CC7",
            "theme_accent_color": "#E8A6B6",
            "theme_color": "#E8A6B6",
            "items_per_page": 12,
            "toast_duration": 3000,
        },
        "images": {
            "download_strategy_mode": "balanced",
            "download_strategy_custom": ["3000", "1740", "max"],
            "download_strategy": ["3000", "1740", "max"],
            "iiif_quality": "default",
            "viewer_quality": 95,
            "probe_remote_max_resolution": True,
            "tile_stitch_max_ram_gb": 2,
        },
        "ocr": {
            "ocr_engine": "openai",
            "kraken_enabled": False,
        },
        "pdf": {
            "viewer_dpi": 150,
            "prefer_native_pdf": True,
            "create_pdf_from_images": False,
            "export": {
                "default_format": "pdf_images",
                "default_compression": "Standard",
                "include_cover": True,
                "include_colophon": True,
                "description_rows": 3,
            },
            "cover": {
                "logo_path": "",
                "curator": "",
                "description": "",
            },
            "profiles": {
                "default": "balanced",
                "catalog": {
                    "balanced": {
                        "label": "Balanced",
                        "compression": "Standard",
                        "include_cover": True,
                        "include_colophon": True,
                        "image_source_mode": "local_balanced",
                        "image_max_long_edge_px": 2600,
                        "jpeg_quality": 82,
                        "force_remote_refetch": False,
                        "cleanup_temp_after_export": True,
                        "max_parallel_page_fetch": 2,
                    },
                    "high_quality": {
                        "label": "High Quality",
                        "compression": "High-Res",
                        "include_cover": True,
                        "include_colophon": True,
                        "image_source_mode": "local_highres",
                        "image_max_long_edge_px": 3800,
                        "jpeg_quality": 92,
                        "force_remote_refetch": False,
                        "cleanup_temp_after_export": True,
                        "max_parallel_page_fetch": 2,
                    },
                    "archival_highres": {
                        "label": "Archival High-Res",
                        "compression": "High-Res",
                        "include_cover": True,
                        "include_colophon": True,
                        "image_source_mode": "remote_highres_temp",
                        "image_max_long_edge_px": 0,
                        "jpeg_quality": 95,
                        "force_remote_refetch": True,
                        "cleanup_temp_after_export": True,
                        "max_parallel_page_fetch": 1,
                    },
                    "lightweight": {
                        "label": "Lightweight",
                        "compression": "Light",
                        "include_cover": False,
                        "include_colophon": False,
                        "image_source_mode": "local_balanced",
                        "image_max_long_edge_px": 1500,
                        "jpeg_quality": 65,
                        "force_remote_refetch": False,
                        "cleanup_temp_after_export": True,
                        "max_parallel_page_fetch": 3,
                    },
                },
                "document_overrides": {},
            },
        },
        "thumbnails": {
            "max_long_edge_px": 320,
            "jpeg_quality": 70,
            "page_size": 48,
            "page_size_options": [24, 48, 72, 96],
        },
        "housekeeping": {
            "temp_cleanup_days": 7,
        },
        "storage": {
            "exports_retention_days": 30,
            "thumbnails_retention_days": 14,
            "highres_temp_retention_hours": 6,
            "auto_prune_on_startup": False,
            "max_exports_per_item": 5,
        },
        "logging": {
            "level": "INFO",
        },
        "testing": {
            "run_live_tests": False,
        },
        "viewer": {
            "mirador": {
                "openSeadragonOptions": {
                    "maxZoomPixelRatio": 5,
                    "maxZoomLevel": 25,
                    "minZoomLevel": 0.35,
                }
            },
            "visual_filters": {
                "defaults": {
                    "brightness": 1.0,
                    "contrast": 1.0,
                    "saturation": 1.0,
                    "hue": 0,
                    "invert": False,
                    "grayscale": False,
                },
                "presets": {
                    "default": {
                        "brightness": 1.0,
                        "contrast": 1.0,
                        "saturation": 1.0,
                        "hue": 0,
                        "invert": False,
                        "grayscale": False,
                    },
                    "night": {
                        "brightness": 0.9,
                        "contrast": 1.3,
                        "saturation": 0.9,
                        "hue": 0,
                        "invert": False,
                        "grayscale": False,
                    },
                    "contrast": {
                        "brightness": 1.05,
                        "contrast": 1.5,
                        "saturation": 1.2,
                        "hue": 0,
                        "invert": False,
                        "grayscale": False,
                    },
                },
            },
        },
    },
}


def _deep_merge(dst: dict[str, Any], src: dict[str, Any]) -> dict[str, Any]:
    for k, v in (src or {}).items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_merge(dst[k], v)
        else:
            dst[k] = v
    return dst


def _try_make_parent_writable(path: Path) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        test = path.parent / ".write_test"
        test.write_text("ok", encoding="utf-8")
        test.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def default_config_path() -> Path:
    """Pick a sensible config.json location.

    Priority:
    1) `./config.json` if writable
    2) `~/.universal-iiif/config.json`
    """
    cwd_candidate = Path.cwd() / "config.json"
    if _try_make_parent_writable(cwd_candidate):
        return cwd_candidate

    fallback = Path.home() / ".universal-iiif" / "config.json"
    return fallback


@dataclass
class ConfigManager:
    """Manages reading and writing the local config.json file.""" ""

    path: Path
    _data: dict[str, Any]

    @classmethod
    def load(cls, path: Path | None = None) -> ConfigManager:
        """Load the configuration from disk, creating defaults if necessary."""
        cfg_path = path or default_config_path()
        data: dict[str, Any] = json.loads(json.dumps(DEFAULT_CONFIG_JSON))

        if cfg_path.exists():
            try:
                loaded = json.loads(cfg_path.read_text(encoding="utf-8") or "{}")
                if isinstance(loaded, dict):
                    _deep_merge(data, loaded)
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("Failed to read config.json at %s: %s", cfg_path, exc)
        else:
            # Ensure file exists for user edits
            try:
                cfg_path.parent.mkdir(parents=True, exist_ok=True)
                cfg_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            except OSError as exc:
                logger.warning("Unable to create default config.json at %s: %s", cfg_path, exc)

        # Back-compat: older configs may have a single `pdf.render_dpi`.
        pdf_cfg = data.get("settings", {}).get("pdf")
        if isinstance(pdf_cfg, dict):
            legacy = pdf_cfg.get("render_dpi")
            if legacy is not None:
                pdf_cfg.setdefault("viewer_dpi", legacy)
                pdf_cfg.setdefault("ocr_dpi", legacy)
                # Keep the in-memory config clean; it will disappear on next save.
                with suppress(KeyError):
                    del pdf_cfg["render_dpi"]

        return cls(path=cfg_path, _data=data)

    @property
    def data(self) -> dict[str, Any]:
        """Get the full config data dictionary."""
        return self._data

    def save(self) -> None:
        """Persist the current config data to disk."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")

    def set_downloads_dir(self, value: str) -> None:
        """Set the downloads directory path."""
        self._data.setdefault("paths", {})["downloads_dir"] = (value or "data/local/downloads").strip()

    def set_exports_dir(self, value: str) -> None:
        """Set the exports directory path."""
        self._data.setdefault("paths", {})["exports_dir"] = (value or "data/local/exports").strip()

    def set_temp_dir(self, value: str) -> None:
        """Set the temporary images directory path."""
        self._data.setdefault("paths", {})["temp_dir"] = (value or "data/local/temp_images").strip()

    def set_models_dir(self, value: str) -> None:
        """Set the models directory path."""
        self._data.setdefault("paths", {})["models_dir"] = (value or "data/local/models").strip()

    def set_logs_dir(self, value: str) -> None:
        """Set the logs directory path."""
        self._data.setdefault("paths", {})["logs_dir"] = (value or "data/local/logs").strip()

    def set_snippets_dir(self, value: str) -> None:
        """Set the snippets directory path."""
        self._data.setdefault("paths", {})["snippets_dir"] = (value or "data/local/snippets").strip()

    def set_api_key(self, provider: str, value: str) -> None:
        """Set an API key for a given provider."""
        self._data.setdefault("api_keys", {})[provider] = (value or "").strip()

    def get_api_key(self, provider: str, default: str = "") -> str:
        """Get an API key for a given provider."""
        # Keys come from config.json only (no env fallback)
        return self._data.get("api_keys", {}).get(provider) or default

    def resolve_path(self, key: str, default_rel: str) -> Path:
        """Resolve a path from config, making it absolute."""
        raw = (self._data.get("paths", {}) or {}).get(key) or default_rel
        p = Path(str(raw)).expanduser()
        if p.is_absolute():
            return p
        # Relative paths are resolved relative to the execution directory
        return (Path.cwd() / p).resolve()

    def get_setting(self, dotted_path: str, default: Any = None) -> Any:
        """Read a nested value from `settings` using a dotted path.

        Example: `get_setting("logging.level", "INFO")`.
        """
        node: Any = self._data.get("settings", {}) or {}
        for part in (dotted_path or "").split("."):
            if not part:
                continue
            if not isinstance(node, dict):
                return default
            node = node.get(part)
        return default if node is None else node

    def set_setting(self, dotted_path: str, value: Any) -> None:
        """Set a nested value in `settings` using a dotted path."""
        if not dotted_path:
            return

        root = self._data.setdefault("settings", {})
        if not isinstance(root, dict):
            self._data["settings"] = {}
            root = self._data["settings"]

        parts = [p for p in dotted_path.split(".") if p]
        node: dict[str, Any] = root
        for part in parts[:-1]:
            child = node.get(part)
            if not isinstance(child, dict):
                child = {}
                node[part] = child
            node = child
        node[parts[-1]] = value

    def _ensure_dir(self, path: Path) -> Path:
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_downloads_dir(self) -> Path:
        """Get the downloads directory path."""
        return self._ensure_dir(self.resolve_path("downloads_dir", "data/local/downloads"))

    def get_exports_dir(self) -> Path:
        """Get the exports directory path."""
        return self._ensure_dir(self.resolve_path("exports_dir", "data/local/exports"))

    def get_temp_dir(self) -> Path:
        """Get the temporary images directory path."""
        return self._ensure_dir(self.resolve_path("temp_dir", "data/local/temp_images"))

    def get_models_dir(self) -> Path:
        """Get the models directory path."""
        return self._ensure_dir(self.resolve_path("models_dir", "data/local/models"))

    def get_logs_dir(self) -> Path:
        """Get the logs directory path."""
        return self._ensure_dir(self.resolve_path("logs_dir", "data/local/logs"))

    def get_snippets_dir(self) -> Path:
        """Get the snippets directory path."""
        return self._ensure_dir(self.resolve_path("snippets_dir", "data/local/snippets"))


# NOTE: apply_to_env() and env var mapping intentionally removed.
# This keeps the app fully self-contained for packaging.


@lru_cache(maxsize=1)
def get_config_manager() -> ConfigManager:
    """Get the singleton config manager."""
    return ConfigManager.load()
