from studio_ui.routes import discovery_handlers
from universal_iiif_core.services.storage.vault_manager import VaultManager


def test_download_status_endpoint_shows_progress():
    """Download status fragment should include progress details."""
    vault = VaultManager()
    job_id = "TestLib_TestDoc"
    doc_id = "TestDoc"
    library = "TestLib"

    # Create job and set progress
    vault.create_download_job(job_id, doc_id, library, "https://example.org/manifest.json")
    vault.update_download_job(job_id, current=2, total=5, status="running")

    fragment = discovery_handlers.get_download_status(job_id, doc_id=doc_id, library=library)
    text = repr(fragment)
    assert "40%" in text or "2/5" in text
