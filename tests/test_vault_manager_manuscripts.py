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


def test_manuscript_ui_preferences_roundtrip():
    """Item-scoped UI preferences should persist as typed JSON values."""
    vm = VaultManager()
    vm.upsert_manuscript("DOC_PREFS", status="saved", asset_state="saved")

    vm.set_manuscript_ui_pref("DOC_PREFS", "studio_export_thumb_page_size", 72)
    vm.set_manuscript_ui_pref("DOC_PREFS", "studio_export_last_mode", "custom")

    assert vm.get_manuscript_ui_pref("DOC_PREFS", "studio_export_thumb_page_size", 0) == 72
    assert vm.get_manuscript_ui_pref("DOC_PREFS", "studio_export_last_mode", "") == "custom"
    assert vm.get_manuscript_ui_pref("DOC_PREFS", "missing_key", "fallback") == "fallback"


def test_delete_manuscript_removes_ui_preferences():
    """Deleting a manuscript should remove its UI preferences as well."""
    vm = VaultManager()
    vm.upsert_manuscript("DOC_PREF_DELETE", library="Gallica", status="saved", asset_state="saved")
    vm.set_manuscript_ui_pref("DOC_PREF_DELETE", "studio_export_thumb_page_size", 24)

    assert vm.get_manuscript_ui_pref("DOC_PREF_DELETE", "studio_export_thumb_page_size", None) == 24
    assert vm.delete_manuscript("DOC_PREF_DELETE") is True
    assert vm.get_manuscript_ui_pref("DOC_PREF_DELETE", "studio_export_thumb_page_size", None) is None


def test_upsert_manuscript_persists_source_and_optimization_fields():
    """Manuscript upsert should persist source-policy and optimization metadata fields."""
    vm = VaultManager()
    vm.upsert_manuscript(
        "DOC_FIELDS",
        status="saved",
        asset_state="saved",
        manifest_local_available=1,
        local_scans_available=0,
        read_source_mode="remote",
        local_optimized=1,
        local_optimization_meta_json='{"optimized_pages": 3}',
    )
    row = vm.get_manuscript("DOC_FIELDS") or {}
    assert int(row.get("manifest_local_available") or 0) == 1
    assert int(row.get("local_scans_available") or 0) == 0
    assert str(row.get("read_source_mode") or "") == "remote"
    assert int(row.get("local_optimized") or 0) == 1
    assert str(row.get("local_optimization_meta_json") or "").strip() == '{"optimized_pages": 3}'


def test_app_ui_preferences_roundtrip():
    """App-scoped UI preferences should persist independent from manuscript scope."""
    vm = VaultManager()
    vm.set_app_ui_pref("studio.last_context", {"doc_id": "DOC_A", "library": "Gallica", "page": 3, "tab": "history"})
    stored = vm.get_app_ui_pref("studio.last_context", {})
    assert stored.get("doc_id") == "DOC_A"
    assert stored.get("library") == "Gallica"
    assert int(stored.get("page") or 0) == 3
    assert stored.get("tab") == "history"


def test_save_studio_context_builds_recent_lru():
    """Saving studio context should deduplicate by doc/library and keep most recent first."""
    vm = VaultManager()
    vm.upsert_manuscript("DOC_A", library="Gallica", status="saved", asset_state="saved")
    vm.upsert_manuscript("DOC_B", library="Vaticana", status="saved", asset_state="saved")

    vm.save_studio_context("DOC_A", "Gallica", 5, "history", max_recent=8)
    vm.save_studio_context("DOC_B", "Vaticana", 2, "info", max_recent=8)
    vm.save_studio_context("DOC_A", "Gallica", 6, "export", max_recent=8)

    last = vm.get_studio_last_context() or {}
    recents = vm.list_studio_recent_contexts(limit=8)
    assert last.get("doc_id") == "DOC_A"
    assert last.get("library") == "Gallica"
    assert int(last.get("page") or 0) == 6
    assert last.get("tab") == "export"
    assert len(recents) == 2
    assert recents[0].get("doc_id") == "DOC_A"
    assert int(recents[0].get("page") or 0) == 6
    assert recents[1].get("doc_id") == "DOC_B"


def test_studio_recent_contexts_skip_removed_items():
    """Recent contexts should ignore entries for manuscripts removed from DB."""
    vm = VaultManager()
    vm.upsert_manuscript("DOC_KEEP_RECENT", library="Gallica", status="saved", asset_state="saved")
    vm.save_studio_context("DOC_KEEP_RECENT", "Gallica", 1, "transcription", max_recent=8)
    vm.set_app_ui_pref(
        "studio.recent_contexts",
        [
            {"doc_id": "DOC_MISSING", "library": "Gallica", "page": 1, "tab": "history", "updated_at": "x"},
            {"doc_id": "DOC_KEEP_RECENT", "library": "Gallica", "page": 2, "tab": "info", "updated_at": "x"},
        ],
    )
    recents = vm.list_studio_recent_contexts(limit=8)
    assert len(recents) == 1
    assert recents[0].get("doc_id") == "DOC_KEEP_RECENT"


def test_get_app_ui_pref_returns_default_on_malformed_json():
    """Malformed app preference JSON should not crash and must return default."""
    vm = VaultManager()
    conn = vm._get_conn()  # noqa: SLF001
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO app_ui_preferences (pref_key, pref_value_json, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(pref_key) DO UPDATE SET
            pref_value_json = excluded.pref_value_json,
            updated_at = CURRENT_TIMESTAMP
        """,
        ("studio.last_context", "{not-json"),
    )
    conn.commit()
    conn.close()

    fallback = {"doc_id": "fallback"}
    assert vm.get_app_ui_pref("studio.last_context", fallback) == fallback
