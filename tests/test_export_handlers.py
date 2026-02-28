from __future__ import annotations

from PIL import Image

from studio_ui.routes import export_handlers
from universal_iiif_core.config_manager import get_config_manager
from universal_iiif_core.services.storage.vault_manager import VaultManager


def _seed_library_item(doc_id: str, library: str, pages: int = 3) -> None:
    cm = get_config_manager()
    doc_root = cm.get_downloads_dir() / library / doc_id
    scans_dir = doc_root / "scans"
    scans_dir.mkdir(parents=True, exist_ok=True)
    for idx in range(pages):
        Image.new("RGB", (600, 900), (245, 245, 245)).save(scans_dir / f"pag_{idx:04d}.jpg", format="JPEG")

    VaultManager().upsert_manuscript(
        doc_id,
        library=library,
        local_path=str(doc_root),
        status="complete",
        asset_state="complete",
        total_canvases=pages,
        downloaded_canvases=pages,
        title=f"Title {doc_id}",
        display_title=f"Title {doc_id}",
    )


def test_export_capabilities_route_exposes_planned_features():
    """Capabilities endpoint should include placeholders for roadmap features."""
    payload = export_handlers.export_capabilities()
    fmt = {item["key"]: item for item in payload["formats"]}
    dst = {item["key"]: item for item in payload["destinations"]}
    assert fmt["txt_transcription"]["available"] is False
    assert dst["google_drive"]["available"] is False


def test_start_export_rejects_unavailable_destination():
    """Google Drive is planned but not yet available in v1."""
    _seed_library_item("DOC_DEST", "Gallica")
    result = export_handlers.start_export(
        items_csv="Gallica::DOC_DEST",
        export_format="pdf_images",
        selection_mode="all",
        selected_pages="",
        destination="google_drive",
    )
    assert "Destinazione non disponibile" in repr(result)


def test_start_export_creates_job_and_spawns_worker(monkeypatch):
    """Starting export should persist a queued job and call worker launcher."""
    _seed_library_item("DOC_START", "Gallica")
    called: dict = {}

    def _fake_spawn(**kwargs):
        called.update(kwargs)

    monkeypatch.setattr(export_handlers, "_spawn_export_worker", _fake_spawn)
    result = export_handlers.start_export(
        items_csv="Gallica::DOC_START",
        export_format="pdf_images",
        selection_mode="all",
        selected_pages="",
        destination="local_filesystem",
    )

    jobs = VaultManager().list_export_jobs(limit=10)
    assert jobs
    latest = jobs[0]
    assert latest["status"] == "queued"
    assert latest["export_format"] == "pdf_images"
    assert called.get("job_id") == latest["job_id"]
    assert "Export avviato" in repr(result)


def test_cancel_export_marks_job_cancelled():
    """Cancelling an export should move it to cancelled state."""
    vm = VaultManager()
    vm.create_export_job(
        "exp_cancel_test",
        scope_type="single",
        doc_ids_json='["DOC_X"]',
        library="Gallica",
        export_format="pdf_images",
        output_kind="binary",
        selection_mode="all",
        selected_pages_json="[]",
        destination="local_filesystem",
        total_steps=1,
    )

    result = export_handlers.cancel_export("exp_cancel_test")
    assert "Annullamento richiesto" in repr(result)
    job = vm.get_export_job("exp_cancel_test") or {}
    assert str(job.get("status") or "").lower() == "cancelled"


def test_jobs_fragment_for_item_pauses_polling_when_idle():
    """Item jobs panel should stop polling when no running/queued jobs exist."""
    _seed_library_item("DOC_IDLE", "Gallica")
    panel = export_handlers.jobs_fragment_for_item("DOC_IDLE", "Gallica")
    rendered = repr(panel)
    assert "every 4s" not in rendered
    assert "Nessun job attivo: polling in pausa." in rendered


def test_jobs_fragment_for_item_enables_polling_when_active():
    """Item jobs panel should poll while item has queued/running jobs."""
    _seed_library_item("DOC_ACTIVE", "Gallica")
    vm = VaultManager()
    vm.create_export_job(
        "exp_active_item",
        scope_type="single",
        doc_ids_json='["DOC_ACTIVE"]',
        library="Gallica",
        export_format="pdf_images",
        output_kind="binary",
        selection_mode="all",
        selected_pages_json="[]",
        destination="local_filesystem",
        total_steps=1,
    )
    panel = export_handlers.jobs_fragment_for_item("DOC_ACTIVE", "Gallica")
    rendered = repr(panel)
    assert "every 4s" in rendered


def test_reset_active_exports_marks_stale_jobs_terminal():
    """Startup reset should move queued/running export jobs to terminal state."""
    vm = VaultManager()
    vm.create_export_job(
        "exp_reset_queued",
        scope_type="single",
        doc_ids_json='["DOC_RQ"]',
        library="Gallica",
        export_format="pdf_images",
        output_kind="binary",
        selection_mode="all",
        selected_pages_json="[]",
        destination="local_filesystem",
        total_steps=1,
    )
    vm.create_export_job(
        "exp_reset_running",
        scope_type="single",
        doc_ids_json='["DOC_RR"]',
        library="Gallica",
        export_format="pdf_images",
        output_kind="binary",
        selection_mode="all",
        selected_pages_json="[]",
        destination="local_filesystem",
        total_steps=1,
    )
    vm.update_export_job("exp_reset_running", status="running")

    updated = vm.reset_active_exports()
    assert updated >= 2
    assert (vm.get_export_job("exp_reset_queued") or {}).get("status") == "error"
    assert (vm.get_export_job("exp_reset_running") or {}).get("status") == "error"
