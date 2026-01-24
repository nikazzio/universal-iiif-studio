import re
from dataclasses import dataclass
from pathlib import Path

import requests
from requests import RequestException

from iiif_downloader.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class AvailableModel:
    """Metadata describing an OCR model available for download."""

    key: str
    doi: str
    kind: str  # 'manuscript' | 'print' | 'generic'
    description: str


def _default_cache_dir() -> Path:
    base = Path.home() / ".cache"
    return base / "universal-iiif-downloader" / "kraken-models"


def _safe_filename(name: str) -> str:
    name = name.strip().replace(" ", "_")
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return name[:180] if len(name) > 180 else name


class ModelManager:
    """Manages Kraken models without committing them into the repo.

    Models are stored in a user-configurable directory via `config.json`.
    """

    def __init__(self, models_dir: Path | None = None):
        """Prepare the storage directory and fall back to cache if needed."""
        if models_dir is not None:
            self.models_dir = Path(models_dir)
        else:
            try:
                from iiif_downloader.config_manager import get_config_manager

                self.models_dir = get_config_manager().get_models_dir()
            except (ImportError, OSError, ValueError, RuntimeError):
                self.models_dir = Path("models")

        try:
            self.models_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            # Last-resort fallback for non-writable install locations
            self.models_dir = _default_cache_dir()
            self.models_dir.mkdir(parents=True, exist_ok=True)

    def list_installed_models(self) -> list[str]:
        """Returns a list of installed `.mlmodel` file names."""
        return sorted({f.name for f in self.models_dir.glob("*.mlmodel") if f.is_file()})

    def get_available_models(self) -> dict[str, AvailableModel]:
        """Hardcoded list for prototype.

        We keep this explicit for stability (no live Zenodo search).
        """
        models = [
            AvailableModel(
                key="TRIDIS (Medieval/Early Modern Latin)",
                doi="10.5281/zenodo.10788591",
                kind="manuscript",
                description=(
                    "Highly versatile model for Latin, Old French, and Spanish "
                    "(11th-16th c.), expanding common abbreviations."
                ),
            ),
            AvailableModel(
                key="CATMuS Medieval (Latin/Graphematic)",
                doi="10.5281/zenodo.12743230",
                kind="manuscript",
                description=("Graphematic transcription approach for medieval Latin manuscripts."),
            ),
            AvailableModel(
                key="HTR Medieval Documentary (Best)",
                doi="10.5281/zenodo.7547438",
                kind="manuscript",
                description=("Specialized for 12th-15th c. documentary manuscripts (accuracy ~94%)."),
            ),
            AvailableModel(
                key="Chtulhu (Printed Books)",
                doi="10.5281/zenodo.6347311",
                kind="print",
                description="General purpose model for printed typography.",
            ),
        ]
        return {m.key: m for m in models}

    def recommend_model_key(
        self,
        document_hint: str | None,
    ) -> str | None:
        """Returns the best model key given a simple hint."""
        available = self.get_available_models()
        if not available:
            return None

        hint = (document_hint or "").strip().lower()
        if hint in {"manuscript", "ms", "manoscritto"}:
            for k, m in available.items():
                if m.kind == "manuscript":
                    return k
        if hint in {"print", "printed", "stampa"}:
            for k, m in available.items():
                if m.kind == "print":
                    return k

        # fallback to the first one available
        return next(iter(available.keys()))

    def search_zenodo(self, query: str = "kraken model manuscript") -> list[dict]:
        """Dynamically search Zenodo for Kraken models."""
        url = "https://zenodo.org/api/records"
        # We append 'kraken' to ensure we find models for the right engine
        search_q = f"kraken {query}" if "kraken" not in query.lower() else query
        params = {
            "q": search_q,
            "status": "published",
            "size": 15,
            "sort": "bestmatch",
            "all_versions": "false",
        }
        try:
            r = requests.get(url, params=params, timeout=20)
            r.raise_for_status()
            data = r.json()
            hits = data.get("hits", {}).get("hits", [])
            results = []
            for h in hits:
                meta = h.get("metadata", {})
                title = meta.get("title", "Unknown Title")
                desc = meta.get("description", "")

                # Check if it likely contains an mlmodel
                # we don't fetch file list for all hits to stay fast,
                # but we can check if 'mlmodel' is in title or description.
                if "mlmodel" in title.lower() or "mlmodel" in desc.lower() or "kraken" in title.lower():
                    results.append(
                        {
                            "title": title,
                            "doi": h.get("doi") or h.get("conceptdoi"),
                            "description": desc[:300].replace("<p>", "").replace("</p>", "") + "...",
                            "links": h.get("links", {}),
                        }
                    )
            return results
        except (RequestException, ValueError, OSError) as e:
            logger.error("Zenodo search failed: %s", e)
            return []

    def get_model_path(self, model_filename: str) -> Path:
        """Return the path where a model file is expected to live."""
        return self.models_dir / model_filename

    def find_installed_model_for_key(self, model_key: str) -> str | None:
        """Returns an installed `.mlmodel` filename for a model key."""
        prefix = f"{_safe_filename(model_key)}__"
        matches = sorted([p.name for p in self.models_dir.glob(prefix + "*.mlmodel") if p.is_file()])
        return matches[0] if matches else None

    def _parse_zenodo_record_id(self, doi_or_record: str) -> str | None:
        s = (doi_or_record or "").strip()
        if not s:
            return None
        if s.isdigit():
            return s

        # Common DOI format: 10.5281/zenodo.2577813
        m = re.search(r"zenodo\.(\d+)", s)
        if m:
            return m.group(1)

        return None

    def _zenodo_record(self, record_id: str) -> dict:
        url = f"https://zenodo.org/api/records/{record_id}"
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return r.json()

    def _extract_mlmodel_files(self, record: dict, record_id: str) -> tuple[list[dict], str | None]:
        files = record.get("files") or []
        if not files:
            return [], f"Zenodo record {record_id} has no downloadable files."

        ml_files = [f for f in files if str(f.get("key", "")).lower().endswith(".mlmodel")]
        if not ml_files:
            keys = ", ".join([str(f.get("key")) for f in files])
            return [], f"No .mlmodel found in Zenodo record {record_id}. Files: {keys}"
        return ml_files, None

    def _choose_mlmodel_file(self, ml_files: list[dict], model_key: str) -> dict:
        if len(ml_files) == 1:
            return ml_files[0]
        safe_key = _safe_filename(model_key).lower()
        for f in ml_files:
            fkey = str(f.get("key", "")).lower()
            if safe_key and safe_key in fkey:
                return f
        return ml_files[0]

    def _resolve_download_url(self, file_info: dict, record_id: str) -> tuple[str | None, str | None]:
        links = file_info.get("links") or {}
        download_url = links.get("self") or links.get("download")
        if not download_url:
            return None, f"Zenodo record {record_id} file has no download link."
        return download_url, None

    def _build_model_dest(self, model_key: str, record_id: str, file_key: str) -> Path:
        local_name = f"{_safe_filename(model_key)}__{record_id}__{_safe_filename(file_key)}"
        if not local_name.lower().endswith(".mlmodel"):
            local_name += ".mlmodel"
        return self.models_dir / local_name

    def _download_file(self, download_url: str, dest: Path) -> tuple[bool, str]:
        tmp = dest.with_suffix(dest.suffix + ".part")
        try:
            with requests.get(download_url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with tmp.open("wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
            tmp.replace(dest)
        except (RequestException, OSError) as e:
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass
            return False, f"Download failed: {e}"
        return True, f"Downloaded model to: {dest.name}"

    def download_model(
        self,
        model_key: str,
        zenodo_doi: str,
        force: bool = False,
    ) -> tuple[bool, str]:
        """Downloads a Kraken `.mlmodel` from Zenodo by DOI.

        Returns (success, message).
        """
        record_id = self._parse_zenodo_record_id(zenodo_doi)
        if not record_id:
            return False, f"Unsupported DOI format: {zenodo_doi}"

        try:
            record = self._zenodo_record(record_id)
        except RequestException as e:
            return False, f"Failed to fetch Zenodo record {record_id}: {e}"

        ml_files, error = self._extract_mlmodel_files(record, record_id)
        if error:
            return False, error

        chosen = self._choose_mlmodel_file(ml_files, model_key)
        file_key = str(chosen.get("key"))
        download_url, error = self._resolve_download_url(chosen, record_id)
        if error:
            return False, error

        dest = self._build_model_dest(model_key, record_id, file_key)
        if dest.exists() and not force:
            return True, f"Model already installed: {dest.name}"

        return self._download_file(download_url, dest)
