import os

import yaml

from iiif_downloader.logger import get_logger

logger = get_logger(__name__)

CONFIG_PATH = os.path.join(os.getcwd(), "config.yaml")

DEFAULT_CONFIG = {
    "system": {
        "download_workers": 4,
        "ocr_concurrency": 1,
        "request_timeout": 30
    },
    "defaults": {
        "default_library": "Vaticana (BAV)",
        "auto_generate_pdf": True,
        "preferred_ocr_engine": "openai"
    },
    "ui": {
        "theme_color": "#FF4B4B",
        "items_per_page": 12,
        "toast_duration": 3000
    },
    "images": {
        "download_strategy": ["max", "3000", "1740"],
        "iiif_quality": "default",
        "viewer_quality": 95,
        "ocr_quality": 95
    }
}


class ConfigLoader:
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            cls._instance.load()
        return cls._instance

    def load(self):
        if self._config:
            return

        self._config = DEFAULT_CONFIG.copy()

        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    user_config = yaml.safe_load(f) or {}
                    # Deep merge would be better; simple update is OK.
                    # We stick to 1-level merge for simplicity
                    for section, values in user_config.items():
                        if section in self._config and isinstance(
                            values,
                            dict,
                        ):
                            self._config[section].update(values)
                        else:
                            self._config[section] = values
                logger.info("Loaded config from %s", CONFIG_PATH)
            except (OSError, yaml.YAMLError) as e:
                logger.error("Failed to load config.yaml: %s", e)
        else:
            logger.info("No config.yaml found, using defaults")

    def get(self, section, key, default=None):
        return self._config.get(section, {}).get(key, default)

    def get_download_dir(self):
        downloads_dir = self.get("system", "downloads_dir", "downloads")
        return os.path.join(os.getcwd(), downloads_dir)

    @property
    def config(self):
        return self._config


# Global instance accessor
config = ConfigLoader()
