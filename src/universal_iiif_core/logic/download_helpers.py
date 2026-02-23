from __future__ import annotations

import re


def sanitize_filename(label: str) -> str:
    """Return a filesystem-safe identifier derived from `label`."""
    safe = "".join([c for c in str(label) if c.isalnum() or c in (" ", ".", "_", "-")])
    return safe.strip().replace(" ", "_")


def derive_identifier(manifest_url: str, output_folder_name: str | None, library: str | None, label: str | None) -> str:
    """Derive a compact folder identifier for a manuscript.

    Returns a clean technical ID suitable for both filesystem and database.
    This ID must be atomic: same value used for folder name and DB primary key.

    Priority:
    1. `output_folder_name` if provided (already clean ID from resolver)
    2. ARK token found in `manifest_url` (Gallica)
    3. UUID-like token in `manifest_url` (Bodleian)
    4. MSS_* pattern in `manifest_url` (Vatican)
    5. sanitized `label` as fallback
    6. last meaningful URL path segment
    """
    # 1. Use output_folder_name directly if provided (should be clean ID from resolver)
    if output_folder_name:
        clean = sanitize_filename(output_folder_name.strip())
        if clean:
            return clean

    # 2. Extract ARK ID from URL (Gallica: ark:/12148/btv1b10033406t)
    m = re.search(r"ark[:/]+\d+/([a-zA-Z0-9]+)", manifest_url)
    if m:
        return sanitize_filename(m.group(1))

    # 3. Extract UUID from URL (Bodleian)
    m = re.search(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", manifest_url)
    if m:
        return m.group(1).lower()

    # 4. Extract MSS_* pattern from URL (Vatican: MSS_Urb.lat.1775)
    m = re.search(r"(MSS_[A-Za-z0-9._-]+)", manifest_url)
    if m:
        return sanitize_filename(m.group(1))

    # 5. Fallback to label
    if label:
        return sanitize_filename(label)

    # 6. Last resort: URL path segment
    parts = [p for p in manifest_url.split("/") if p]
    if parts:
        last = parts[-2] if parts[-1].lower().endswith("manifest.json") and len(parts) >= 2 else parts[-1]
        return sanitize_filename(last)

    return "unknown_manuscript"
