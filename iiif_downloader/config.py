"""Legacy module (disabled).

This project has been migrated to a single runtime configuration source:
`config.json` via `iiif_downloader.config_manager`.

If you see this error, update the call site to:

    from iiif_downloader.config_manager import get_config_manager

and then use:

    get_config_manager().get_setting("section.key", default)
"""

raise RuntimeError("Legacy config module disabled. Use iiif_downloader.config_manager.get_config_manager() instead.")
