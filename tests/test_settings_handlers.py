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


def test_save_settings_applies_download_strategy_mode(monkeypatch):
    """Saving settings should materialize canonical images.download_strategy from selected mode."""
    dummy_cm = _DummyConfigManager()
    monkeypatch.setattr(settings_handlers, "get_config_manager", lambda: dummy_cm)
    monkeypatch.setattr(settings_handlers, "setup_logging", lambda: None)

    request = _DummyRequest(
        {
            "settings.images.download_strategy_mode": "quality_first",
            "settings.images.download_strategy_custom": "1740,1200,max",
        }
    )
    _ = asyncio.run(settings_handlers.save_settings(request))

    images = dummy_cm.data["settings"]["images"]
    assert images["download_strategy_mode"] == "quality_first"
    assert images["download_strategy"] == ["max", "3000", "1740"]
    assert images["download_strategy_custom"] == ["1740", "1200", "max"]


def test_save_settings_creates_new_pdf_profile_from_legacy_payload(monkeypatch):
    """Legacy new_profile payload remains supported for backward compatibility."""
    dummy_cm = _DummyConfigManager()
    monkeypatch.setattr(settings_handlers, "get_config_manager", lambda: dummy_cm)
    monkeypatch.setattr(settings_handlers, "setup_logging", lambda: None)

    request = _DummyRequest(
        {
            "settings.pdf.profiles.new_profile.create": "true",
            "settings.pdf.profiles.new_profile.key": "Ricerca Alta",
            "settings.pdf.profiles.new_profile.label": "Ricerca Alta",
            "settings.pdf.profiles.new_profile.compression": "High-Res",
            "settings.pdf.profiles.new_profile.image_source_mode": "remote_highres_temp",
            "settings.pdf.profiles.new_profile.max_parallel_page_fetch": "4",
            "settings.pdf.profiles.new_profile.make_default": "true",
        }
    )
    _ = asyncio.run(settings_handlers.save_settings(request))

    profiles = dummy_cm.data["settings"]["pdf"]["profiles"]
    catalog = profiles["catalog"]
    assert "ricerca_alta" in catalog
    assert catalog["ricerca_alta"]["compression"] == "High-Res"
    assert catalog["ricerca_alta"]["image_source_mode"] == "remote_highres_temp"
    assert catalog["ricerca_alta"]["max_parallel_page_fetch"] == 4
    assert profiles["default"] == "ricerca_alta"


def test_save_settings_profile_editor_creates_profile_and_triggers_reload(monkeypatch):
    """New profile editor mode should create profile and return reload script for refreshed select catalog."""
    dummy_cm = _DummyConfigManager()
    monkeypatch.setattr(settings_handlers, "get_config_manager", lambda: dummy_cm)
    monkeypatch.setattr(settings_handlers, "setup_logging", lambda: None)

    request = _DummyRequest(
        {
            "settings.pdf.profiles.editor.action": "save",
            "settings.pdf.profiles.editor.selected": "__new__",
            "settings.pdf.profiles.editor.key": "Ricerca Dettaglio",
            "settings.pdf.profiles.editor.label": "Ricerca Dettaglio",
            "settings.pdf.profiles.editor.compression": "High-Res",
            "settings.pdf.profiles.editor.image_source_mode": "remote_highres_temp",
            "settings.pdf.profiles.editor.max_parallel_page_fetch": "3",
            "settings.pdf.profiles.editor.make_default": "true",
        }
    )

    result = asyncio.run(settings_handlers.save_settings(request))

    profiles = dummy_cm.data["settings"]["pdf"]["profiles"]
    assert "ricerca_dettaglio" in profiles["catalog"]
    assert profiles["default"] == "ricerca_dettaglio"
    assert "/settings?tab=pdf" in str(result)


def test_save_settings_profile_editor_updates_existing_profile_without_reload(monkeypatch):
    """Editing an existing profile should update payload without forcing page reload."""
    dummy_cm = _DummyConfigManager()
    dummy_cm.data["settings"]["pdf"] = {
        "profiles": {
            "default": "balanced",
            "catalog": {
                "balanced": {"label": "Balanced"},
                "ricerca": {
                    "label": "Ricerca",
                    "compression": "Standard",
                    "image_source_mode": "local_balanced",
                    "max_parallel_page_fetch": 2,
                },
            },
        }
    }
    monkeypatch.setattr(settings_handlers, "get_config_manager", lambda: dummy_cm)
    monkeypatch.setattr(settings_handlers, "setup_logging", lambda: None)

    request = _DummyRequest(
        {
            "settings.pdf.profiles.editor.action": "save",
            "settings.pdf.profiles.editor.selected": "ricerca",
            "settings.pdf.profiles.editor.label": "Ricerca aggiornata",
            "settings.pdf.profiles.editor.compression": "Light",
            "settings.pdf.profiles.editor.image_source_mode": "local_highres",
            "settings.pdf.profiles.editor.max_parallel_page_fetch": "2",
        }
    )

    result = asyncio.run(settings_handlers.save_settings(request))

    profile = dummy_cm.data["settings"]["pdf"]["profiles"]["catalog"]["ricerca"]
    assert profile["label"] == "Ricerca aggiornata"
    assert profile["compression"] == "Light"
    assert profile["image_source_mode"] == "local_highres"
    assert "/settings?tab=pdf" not in str(result)


def test_save_settings_profile_editor_deletes_profile_and_triggers_reload(monkeypatch):
    """Delete action should remove selected profile and trigger a settings page reload."""
    dummy_cm = _DummyConfigManager()
    dummy_cm.data["settings"]["pdf"] = {
        "profiles": {
            "default": "ricerca",
            "catalog": {
                "balanced": {"label": "Balanced"},
                "ricerca": {"label": "Ricerca"},
            },
        }
    }
    monkeypatch.setattr(settings_handlers, "get_config_manager", lambda: dummy_cm)
    monkeypatch.setattr(settings_handlers, "setup_logging", lambda: None)

    request = _DummyRequest(
        {
            "settings.pdf.profiles.editor.action": "delete",
            "settings.pdf.profiles.editor.selected": "ricerca",
        }
    )

    result = asyncio.run(settings_handlers.save_settings(request))

    profiles = dummy_cm.data["settings"]["pdf"]["profiles"]
    assert "ricerca" not in profiles["catalog"]
    assert profiles["default"] == "balanced"
    assert "/settings?tab=pdf" in str(result)
