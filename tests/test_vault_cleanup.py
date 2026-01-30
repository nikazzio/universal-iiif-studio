from pathlib import Path

from universal_iiif_core.services.storage.vault_manager import VaultManager


class _FakeConfig:
    def __init__(self, temp_dir: Path):
        self._temp = temp_dir

    def get_temp_dir(self):
        self._temp.mkdir(parents=True, exist_ok=True)
        return self._temp


def test_cleanup_stale_data_removes_old_jobs_and_prunes_tmp(tmp_path, monkeypatch):
    """Test that cleanup_stale_data removes old job records and prunes temp dirs."""
    db_path = tmp_path / "vault.db"
    vm = VaultManager(str(db_path))

    # Insert an old job row (created_at older than 25 hours)
    conn = vm._get_conn()
    cur = conn.cursor()
    # Ensure table exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='download_jobs'")
    if not cur.fetchone():
        vm._init_db()
    cur.execute(
        "INSERT OR REPLACE INTO download_jobs (job_id, doc_id, library, manifest_url, status, "
        "current_page, total_pages, error_message, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now', '-25 hours'))",
        (
            "oldjob",
            "doc-old",
            "Lib",
            "",
            "pending",
            0,
            10,
            None,
        ),
    )
    conn.commit()
    conn.close()

    # Create a corresponding temp folder to be pruned
    fake_temp = tmp_path / "temp_images"
    temp_for_doc = fake_temp / "doc-old"
    temp_for_doc.mkdir(parents=True, exist_ok=True)
    # add a dummy file
    (temp_for_doc / "dummy.jpg").write_text("x")

    # Monkeypatch get_config_manager used inside cleanup to return our fake temp dir
    # The cleanup function imports `get_config_manager` from the config_manager
    # module at call time; patch that instead so our fake temp dir is used.
    import universal_iiif_core.config_manager as cfg_mod

    monkeypatch.setattr(cfg_mod, "get_config_manager", lambda: _FakeConfig(fake_temp))

    removed = vm.cleanup_stale_data(retention_hours=24)
    assert removed >= 1
    # ensure temp folder pruned
    assert not temp_for_doc.exists()
