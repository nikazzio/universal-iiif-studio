import json

from universal_iiif_core.config_manager import get_config_manager
from universal_iiif_core.services.storage.vault_manager import VaultManager


def test_upsert_manuscript_keeps_existing_fields_on_partial_updates():
    """Partial updates must not corrupt or drop existing manuscript metadata."""
    vm = VaultManager()
    vm.upsert_manuscript(
        "DOC_KEEP",
        display_title="Titolo Uno",
        catalog_title="Titolo Uno",
        shelfmark="Shelf.1",
        source_detail_url="https://example.org/detail",
        item_type="manoscritto",
        item_type_source="manual",
    )
    vm.upsert_manuscript("DOC_KEEP", status="complete", asset_state="complete")

    row = vm.get_manuscript("DOC_KEEP") or {}
    assert row.get("display_title") == "Titolo Uno"
    assert row.get("catalog_title") == "Titolo Uno"
    assert row.get("shelfmark") == "Shelf.1"
    assert row.get("source_detail_url") == "https://example.org/detail"
    assert row.get("item_type") == "manoscritto"
    assert row.get("item_type_source") == "manual"


def test_normalize_asset_states_updates_legacy_item_type(tmp_path):
    """Normalization should align state and migrate legacy item_type values."""
    cm = get_config_manager()
    old_downloads = cm.get_downloads_dir()
    try:
        downloads = tmp_path / "downloads"
        cm.set_downloads_dir(str(downloads))
        scans = downloads / "Gallica" / "DOC_STATE" / "scans"
        scans.mkdir(parents=True, exist_ok=True)
        (scans / "pag_0000.jpg").write_text("x", encoding="utf-8")

        vm = VaultManager()
        vm.upsert_manuscript(
            "DOC_STATE",
            library="Gallica",
            local_path=str(scans.parent),
            status="complete",
            asset_state="saved",
            total_canvases=1,
            downloaded_canvases=1,
            item_type="altro",
        )

        updated = vm.normalize_asset_states(limit=10)
        row = vm.get_manuscript("DOC_STATE") or {}
        assert updated >= 1
        assert row.get("asset_state") == "complete"
        assert row.get("item_type") == "non classificato"
    finally:
        cm.set_downloads_dir(str(old_downloads))


def test_normalize_asset_states_recovers_stale_downloading_from_temp_pages(tmp_path):
    """Stale downloading rows without active jobs should be normalized using temp pages."""
    cm = get_config_manager()
    old_downloads = cm.get_downloads_dir()
    old_temp = cm.get_temp_dir()
    try:
        downloads = tmp_path / "downloads"
        temp_images = tmp_path / "temp_images"
        cm.set_downloads_dir(str(downloads))
        cm.set_temp_dir(str(temp_images))

        local_root = downloads / "Gallica" / "DOC_STALE"
        (local_root / "scans").mkdir(parents=True, exist_ok=True)
        temp_doc_dir = temp_images / "DOC_STALE"
        temp_doc_dir.mkdir(parents=True, exist_ok=True)
        for idx in (0, 1):
            (temp_doc_dir / f"pag_{idx:04d}.jpg").write_text("x", encoding="utf-8")

        vm = VaultManager()
        vm.upsert_manuscript(
            "DOC_STALE",
            library="Gallica",
            local_path=str(local_root),
            status="downloading",
            asset_state="downloading",
            total_canvases=5,
            downloaded_canvases=0,
            missing_pages_json="[]",
        )

        updated = vm.normalize_asset_states(limit=10)
        row = vm.get_manuscript("DOC_STALE") or {}
        assert updated >= 1
        assert row.get("status") == "partial"
        assert row.get("asset_state") == "partial"
        assert int(row.get("downloaded_canvases") or 0) == 2
        missing = json.loads(str(row.get("missing_pages_json") or "[]"))
        assert missing == [3, 4, 5]
    finally:
        cm.set_downloads_dir(str(old_downloads))
        cm.set_temp_dir(str(old_temp))
