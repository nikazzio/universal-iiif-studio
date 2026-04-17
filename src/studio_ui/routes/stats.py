"""Statistics routes registration."""

from studio_ui.routes import stats_handlers


def setup_stats_routes(app):
    """Register statistics page and API routes."""
    app.get("/stats")(stats_handlers.stats_page)
    app.get("/api/stats/sidebar")(stats_handlers.stats_sidebar_widget)
    app.get("/api/stats/detail")(stats_handlers.stats_detail_content)
