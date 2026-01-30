from .settings_handlers import save_settings, settings_page


def setup_settings_routes(app):
    """Registra le route per le impostazioni."""
    app.get("/settings")(settings_page)
    app.post("/settings/save")(save_settings)
