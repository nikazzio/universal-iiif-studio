class BaseResolver:
    """Base class for resolving user input into a IIIF Manifest URL."""

    def __init__(self):
        pass

    def can_resolve(self, url_or_id):
        """Returns True if this resolver can handle the input."""
        raise NotImplementedError

    def get_manifest_url(self, url_or_id):
        """Returns the full Manifest URL and a suggested identifier."""
        raise NotImplementedError
