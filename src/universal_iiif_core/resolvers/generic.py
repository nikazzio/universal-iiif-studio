from .base import BaseResolver


class GenericResolver(BaseResolver):
    """Fallback resolver that treats the input as an already-resolved manifest URL."""

    def can_resolve(self, url_or_id):
        """Return True for anything that looks like an HTTP URL."""
        return url_or_id.lower().startswith("http")

    def get_manifest_url(self, url_or_id):
        """Return the input as the manifest URL and guess an ID."""
        # Return as-is, let the downloader try to fetch it
        # Try to guess an ID from the URL
        parts = url_or_id.strip("/").split("/")
        candidate_id = parts[-1]
        if candidate_id.lower() in ("manifest.json", "manifest"):
            candidate_id = parts[-2]

        return url_or_id, candidate_id
