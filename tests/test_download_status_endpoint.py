from starlette.testclient import TestClient

from studio_app import app
from universal_iiif_core.services.storage.vault_manager import VaultManager


def test_download_status_endpoint_shows_progress():
    """Create a download job in the DB and verify the polling endpoint returns progress HTML."""
    vault = VaultManager()
    job_id = "TestLib_TestDoc"
    doc_id = "TestDoc"
    library = "TestLib"

    # Create job and set progress
    vault.create_download_job(job_id, doc_id, library, "https://example.org/manifest.json")
    vault.update_download_job(job_id, current=2, total=5, status="running")

    with TestClient(app) as client:
        resp = client.get(f"/api/download_status/{job_id}?doc_id={doc_id}&library={library}")
        assert resp.status_code == 200
        text = resp.text

        # Should contain the Italian progress substring used in the template
        assert "Scaricamento pagina 2 di 5" in text or "40%" in text
