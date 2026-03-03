from pathlib import Path

from universal_iiif_core.logic import downloader_runtime


class _Logger:
    def debug(self, *_args, **_kwargs):
        return None


class _Vault:
    def __init__(self):
        self.calls: list[dict] = []

    def upsert_manuscript(self, _ms_id, **kwargs):
        self.calls.append(kwargs)


class _DummyDownloader:
    def __init__(self, root: Path, *, expected_total: int):
        self.scans_dir = root / "scans"
        self.temp_dir = root / "temp"
        self.pdf_dir = root / "pdf"
        self.scans_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        self.overwrite_existing_scans = False
        self.expected_total_canvases = expected_total
        self.total_canvases = expected_total
        self.ms_id = "DOC_STAGE"
        self.logger = _Logger()
        self.vault = _Vault()


def test_finalize_downloads_keeps_temp_files_when_incomplete(tmp_path):
    """Incomplete downloads must keep staged images in temp dir."""
    dummy = _DummyDownloader(tmp_path, expected_total=3)
    staged = dummy.temp_dir / "pag_0000.jpg"
    staged.write_bytes(b"temp-jpg")

    out = downloader_runtime._finalize_downloads(dummy, [str(staged)])
    assert out == []
    assert staged.exists()
    assert not (dummy.scans_dir / "pag_0000.jpg").exists()


def test_finalize_downloads_promotes_temp_files_when_complete(tmp_path):
    """Once all pages are present, staged files should move to scans and temp cleaned."""
    dummy = _DummyDownloader(tmp_path, expected_total=2)
    (dummy.temp_dir / "pag_0000.jpg").write_bytes(b"temp-0")
    (dummy.temp_dir / "pag_0001.jpg").write_bytes(b"temp-1")

    out = downloader_runtime._finalize_downloads(dummy, [])
    assert len(out) == 2
    assert (dummy.scans_dir / "pag_0000.jpg").exists()
    assert (dummy.scans_dir / "pag_0001.jpg").exists()
    assert not dummy.temp_dir.exists()


def test_sync_asset_state_counts_known_pages_from_scans_and_temp(tmp_path):
    """Asset sync should consider both scans and staged pages."""
    dummy = _DummyDownloader(tmp_path, expected_total=5)
    (dummy.scans_dir / "pag_0000.jpg").write_bytes(b"scan-0")
    (dummy.temp_dir / "pag_0001.jpg").write_bytes(b"temp-1")
    (dummy.temp_dir / "pag_0002.jpg").write_bytes(b"temp-2")

    downloader_runtime._sync_asset_state(dummy, total_expected=5)

    payload = dummy.vault.calls[-1]
    assert payload["asset_state"] == "partial"
    assert int(payload["downloaded_canvases"]) == 3
    assert payload["missing_pages_json"] == "[4, 5]"
