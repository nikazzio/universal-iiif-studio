"""Test bootstrap.

Ensures the project root is importable and handles automatic DB cleanup.
"""

from __future__ import annotations

import contextlib
import logging
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Add SRC to path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SRC = ROOT / "src"
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _config_manager():
    from universal_iiif_core.config_manager import get_config_manager

    return get_config_manager()


def _vault_manager_cls():
    from universal_iiif_core.services.storage.vault_manager import VaultManager

    return VaultManager


def pytest_configure():
    """Redirect session logging to a temporary folder before test collection."""
    cm = _config_manager()
    session_logs_dir = Path(tempfile.mkdtemp(prefix="iiif-pytest-logs-")) / "logs"
    cm.set_logs_dir(str(session_logs_dir))

    from universal_iiif_core import logger as logger_mod

    session_logs_dir.mkdir(parents=True, exist_ok=True)
    logger_mod.LOG_BASE_DIR = session_logs_dir
    for handler in list(logger_mod.app_logger.handlers):
        logger_mod.app_logger.removeHandler(handler)
        with contextlib.suppress(Exception):
            handler.close()


def _redirect_test_logging(monkeypatch, tmp_path):
    from universal_iiif_core import logger as logger_mod

    test_logs_dir = tmp_path / "logs"
    test_logs_dir.mkdir(parents=True, exist_ok=True)

    for handler in list(logger_mod.app_logger.handlers):
        logger_mod.app_logger.removeHandler(handler)
        with contextlib.suppress(Exception):
            handler.close()

    monkeypatch.setattr(logger_mod, "LOG_BASE_DIR", test_logs_dir)
    logger_mod.setup_logging()


def _snapshot_config_paths(cm):
    return {
        "downloads": cm.resolve_path("downloads_dir", "data/local/downloads"),
        "temp": cm.resolve_path("temp_dir", "data/local/temp_images"),
        "models": cm.resolve_path("models_dir", "data/local/models"),
        "logs": cm.resolve_path("logs_dir", "data/local/logs"),
        "snippets": cm.resolve_path("snippets_dir", "data/local/snippets"),
    }


def _set_tmp_config_paths(cm, tmp_path):
    cm.set_downloads_dir(str(tmp_path / "downloads"))
    cm.set_temp_dir(str(tmp_path / "temp_images"))
    cm.set_models_dir(str(tmp_path / "models"))
    cm.set_logs_dir(str(tmp_path / "logs"))
    cm.set_snippets_dir(str(tmp_path / "snippets"))


def _restore_config_paths(cm, original_paths):
    cm.set_downloads_dir(str(original_paths["downloads"]))
    cm.set_temp_dir(str(original_paths["temp"]))
    cm.set_models_dir(str(original_paths["models"]))
    cm.set_logs_dir(str(original_paths["logs"]))
    cm.set_snippets_dir(str(original_paths["snippets"]))


def _cleanup_db(created_jobs, created_manuscripts):
    try:
        vm = _vault_manager_cls()()
        conn = vm._get_conn()
        c = conn.cursor()

        for jid in created_jobs:
            with contextlib.suppress(Exception):
                c.execute("DELETE FROM download_jobs WHERE job_id = ?", (jid,))

        for mid in created_manuscripts:
            with contextlib.suppress(Exception):
                c.execute("DELETE FROM snippets WHERE ms_name = ?", (mid,))
            with contextlib.suppress(Exception):
                c.execute("DELETE FROM manuscripts WHERE id = ?", (mid,))

        conn.commit()
        conn.close()
    except Exception as exc:
        logging.debug("Teardown DB cleanup warning (ignored): %s", exc)


def _cleanup_local_paths(created_local_paths, tmp_root):
    for local_path in created_local_paths:
        p = Path(local_path).resolve()
        if not (p == tmp_root or tmp_root in p.parents):
            continue
        if p.is_dir():
            with contextlib.suppress(Exception):
                shutil.rmtree(p, ignore_errors=True)
            continue
        if p.exists():
            with contextlib.suppress(OSError):
                p.unlink()


@pytest.fixture(autouse=True)
def _auto_cleanup_database(monkeypatch, tmp_path):
    """Autouse fixture che intercetta la creazione di Job e Manoscritti.

    E li elimina dal DB alla fine di ogni test.
    """
    cm = _config_manager()
    original_paths = _snapshot_config_paths(cm)
    _set_tmp_config_paths(cm, tmp_path)
    _redirect_test_logging(monkeypatch, tmp_path)

    created_jobs = set()
    created_manuscripts = set()
    created_local_paths = set()

    vault_manager = _vault_manager_cls()

    orig_init = vault_manager.__init__

    def _wrapped_init(self, db_path="data/vault.db"):
        if db_path == "data/vault.db":
            db_path = str(tmp_path / "vault.db")
        orig_init(self, db_path)

    monkeypatch.setattr(vault_manager, "__init__", _wrapped_init)

    # 1. Monkeypatch create_download_job
    orig_create_job = vault_manager.create_download_job

    def _wrapped_create_job(self, job_id, *a, **kw):
        created_jobs.add(job_id)
        return orig_create_job(self, job_id, *a, **kw)

    monkeypatch.setattr(vault_manager, "create_download_job", _wrapped_create_job)

    # 2. Monkeypatch upsert_manuscript (per pulire i manoscritti)
    orig_upsert_ms = vault_manager.upsert_manuscript

    def _wrapped_upsert_ms(self, manuscript_id, **kw):
        created_manuscripts.add(manuscript_id)
        local_path = kw.get("local_path")
        if isinstance(local_path, str) and local_path.strip():
            created_local_paths.add(local_path)
        return orig_upsert_ms(self, manuscript_id, **kw)

    monkeypatch.setattr(vault_manager, "upsert_manuscript", _wrapped_upsert_ms)

    yield

    _cleanup_db(created_jobs, created_manuscripts)
    _cleanup_local_paths(created_local_paths, tmp_path.resolve())
    _restore_config_paths(cm, original_paths)
