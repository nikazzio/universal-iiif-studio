from __future__ import annotations

import json
import logging
from pathlib import Path

from universal_iiif_core.config_manager import DEFAULT_CONFIG_JSON, ConfigManager


def _base_config() -> dict:
    return json.loads(json.dumps(DEFAULT_CONFIG_JSON))


def _write_config(path: Path, payload: dict) -> str:
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    path.write_text(text, encoding="utf-8")
    return text


def test_load_logs_validation_issues_without_rewriting_file(tmp_path, caplog):
    """Load should emit diagnostics while keeping file bytes untouched."""
    cfg_path = tmp_path / "config.json"
    payload = _base_config()
    payload["security"]["allowed_origins"] = "http://localhost:8000"
    payload["settings"]["thumbnails"]["columns"] = 6
    payload["settings"]["unexpected"] = {"flag": True}
    original = _write_config(cfg_path, payload)

    caplog.set_level(logging.WARNING)
    manager = ConfigManager.load(path=cfg_path)

    assert manager.get_setting("thumbnails.columns") == 6
    assert cfg_path.read_text(encoding="utf-8") == original
    assert any(
        rec.levelno >= logging.ERROR
        and "security.allowed_origins" in rec.getMessage()
        and "invalid_type" in rec.getMessage()
        for rec in caplog.records
    )
    assert any(
        rec.levelno == logging.WARNING
        and "settings.thumbnails.columns" in rec.getMessage()
        and "deprecated_key" in rec.getMessage()
        for rec in caplog.records
    )


def test_load_does_not_log_secret_values(tmp_path, caplog):
    """Validation output must not leak secret values."""
    cfg_path = tmp_path / "config.json"
    payload = _base_config()
    payload["api_keys"]["openai"] = "sk-super-secret-value"
    payload["api_keys"]["anthropic"] = {"token": "not-a-string"}
    _write_config(cfg_path, payload)

    caplog.set_level(logging.WARNING)
    ConfigManager.load(path=cfg_path)

    assert "sk-super-secret-value" not in caplog.text
    assert "not-a-string" not in caplog.text
