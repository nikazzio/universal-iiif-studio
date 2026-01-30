"""Test bootstrap.

Ensures the project root is importable when running `pytest` without installing the
package into the active environment.
"""

from __future__ import annotations

import contextlib
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SRC = ROOT / "src"
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


import pytest


@pytest.fixture(autouse=True)
def _capture_and_cleanup_download_jobs():
    """Autouse fixture that wraps VaultManager.

    create_download_job to record created download job IDs during a test and remove them from the DB at teardown.
    This prevents test artifacts from persisting between runs when tests create
    download job rows directly via the VaultManager.
    """
    created = []
    try:
        from universal_iiif_core.services.storage.vault_manager import VaultManager

        orig = VaultManager.create_download_job

        def _wrapped(self, job_id, *a, **kw):
            created.append(job_id)
            return orig(self, job_id, *a, **kw)

        VaultManager.create_download_job = _wrapped
    except Exception:
        # If VaultManager isn't importable in some contexts, just yield and do nothing
        yield
        return

    yield

    # Teardown: remove any created download job rows
    try:
        vm = VaultManager()
        conn = vm._get_conn()
        c = conn.cursor()
        for jid in set(created):
            with contextlib.suppress(Exception):
                c.execute("DELETE FROM download_jobs WHERE job_id = ?", (jid,))
        conn.commit()
        conn.close()
    except Exception as exc:
        logging.exception("Teardown failed while removing download jobs: %s", exc)
    finally:
        # restore original
        try:
            VaultManager.create_download_job = orig
        except Exception as exc:
            logging.exception("Failed to restore VaultManager.create_download_job: %s", exc)
