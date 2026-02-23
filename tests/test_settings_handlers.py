import asyncio

from studio_ui.routes import settings_handlers


class _DummyRequest:
    def __init__(self, form_data):
        self._form_data = form_data

    async def form(self):
        return self._form_data


class _DummyConfigManager:
    def __init__(self):
        self.data = {"settings": {"viewer": {"theme": "light"}}, "paths": {}, "api_keys": {}}
        self.saved = False

    def save(self):
        self.saved = True


def test_parse_value_coercions():
    """Verify form value coercion handles JSON, booleans, numbers and CSV."""
    assert settings_handlers._parse_value(None) is None
    assert settings_handlers._parse_value("") == ""
    assert settings_handlers._parse_value('{"a": 1}') == {"a": 1}
    assert settings_handlers._parse_value("[1, 2]") == [1, 2]
    assert settings_handlers._parse_value("true") is True
    assert settings_handlers._parse_value("FALSE") is False
    assert settings_handlers._parse_value("42") == 42
    assert settings_handlers._parse_value("2.5") == 2.5
    assert settings_handlers._parse_value("a, b, c") == ["a", "b", "c"]
    assert settings_handlers._parse_value("plain text") == "plain text"
    assert settings_handlers._parse_value(123) == 123


def test_save_settings_merges_payload_and_reconfigures_logging(monkeypatch):
    """Ensure save_settings inflates dotted keys, merges config, and saves successfully."""
    dummy_cm = _DummyConfigManager()
    setup_calls: list[str] = []

    monkeypatch.setattr(settings_handlers, "get_config_manager", lambda: dummy_cm)
    monkeypatch.setattr(settings_handlers, "setup_logging", lambda: setup_calls.append("called"))

    request = _DummyRequest(
        {
            "settings.viewer.maxZoomLevel": "3",
            "settings.pdf.cover.description": "Nuova descrizione",
            "paths.downloads": "downloads/test-path",
            "custom.flag": "true",
        }
    )

    result = asyncio.run(settings_handlers.save_settings(request))

    assert dummy_cm.saved is True
    assert dummy_cm.data["settings"]["viewer"]["maxZoomLevel"] == 3
    assert dummy_cm.data["settings"]["pdf"]["cover"]["description"] == "Nuova descrizione"
    assert dummy_cm.data["paths"]["downloads"] == "downloads/test-path"
    assert dummy_cm.data["custom"]["flag"] is True
    assert setup_calls == ["called"]
    assert "Impostazioni salvate con successo" in str(result)


def test_save_settings_returns_danger_toast_on_failure(monkeypatch):
    """Ensure handler returns a danger toast when persistence raises an exception."""
    dummy_cm = _DummyConfigManager()

    def _raise_on_save():
        raise RuntimeError("boom")

    dummy_cm.save = _raise_on_save

    monkeypatch.setattr(settings_handlers, "get_config_manager", lambda: dummy_cm)
    monkeypatch.setattr(settings_handlers, "setup_logging", lambda: None)

    request = _DummyRequest({"settings.viewer.maxZoomLevel": "3"})

    result = asyncio.run(settings_handlers.save_settings(request))

    assert "Errore nel salvataggio" in str(result)
