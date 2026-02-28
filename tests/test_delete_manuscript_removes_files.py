from universal_iiif_core.config_manager import get_config_manager
from universal_iiif_core.services.storage.vault_manager import VaultManager


def test_delete_manuscript_removes_folder_and_snippets(tmp_path):
    """Ensure manuscript deletion removes DB entries and on-disk artifacts."""
    # Arrange: point downloads dir to a temporary location
    cm = get_config_manager()
    tmp_downloads = tmp_path / "downloads"
    cm.set_downloads_dir(str(tmp_downloads))

    # Create a VaultManager with DB inside tmp
    db_path = tmp_path / "vault.db"
    vm = VaultManager(db_path=str(db_path))

    # Create manuscript folder under downloads
    ms_id = "TEST_MS"
    lib = "TestLib"
    candidate = tmp_downloads / lib / ms_id
    scans = candidate / "scans"
    scans.mkdir(parents=True, exist_ok=True)

    # Create a dummy scan file and ensure it exists
    sfile = scans / "pag_0000.jpg"
    sfile.write_text("dummy")
    assert sfile.exists()

    # Register manuscript and snippet in DB
    vm.upsert_manuscript(ms_id, library=lib, title="T", local_path=str(candidate), status="complete")
    snippet_id = vm.save_snippet(ms_id, 1, str(sfile))
    vm.create_download_job("job_test_ms", ms_id, lib, "https://example.org/manifest.json")
    vm.update_download_job("job_test_ms", current=1, total=2, status="error", error="boom")
    assert snippet_id is not None

    # Sanity: DB record exists
    assert vm.get_manuscript(ms_id) is not None

    # Act
    deleted = vm.delete_manuscript(ms_id)

    # Assert: deletion reported and filesystem cleaned
    assert deleted is True
    assert not candidate.exists()
    # Snippet file should be removed
    assert not sfile.exists()
    # DB should not have manuscript
    assert vm.get_manuscript(ms_id) is None
    # Related download jobs should be removed too
    assert vm.get_download_job("job_test_ms") is None


def test_list_download_jobs_hides_terminal_orphans(tmp_path):
    """Terminal jobs without a manuscript row should not appear in manager list."""
    db_path = tmp_path / "vault.db"
    vm = VaultManager(db_path=str(db_path))

    vm.create_download_job("job_orphan", "DOC_ORPHAN", "TestLib", "https://example.org/orphan.json")
    vm.update_download_job("job_orphan", current=0, total=0, status="error", error="boom")

    jobs = vm.list_download_jobs(limit=20)
    assert all(j.get("job_id") != "job_orphan" for j in jobs)
