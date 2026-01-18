import re

from .base import BaseResolver


class OxfordResolver(BaseResolver):
    def can_resolve(self, url_or_id):
        return "digital.bodleian.ox.ac.uk" in url_or_id

    def get_manifest_url(self, url_or_id):
        # Input: https://digital.bodleian.ox.ac.uk/objects/080f88f5-7586-4b8a-8064-63ab3495393c/
        # Output: https://iiif.bodleian.ox.ac.uk/iiif/manifest/080f88f5-7586-4b8a-8064-63ab3495393c.json

        # Regex to extract UUID: 8-4-4-4-12 hex digits
        uuid_pattern = r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
        match = re.search(uuid_pattern, url_or_id)

        if match:
            uuid = match.group(1)
            manifest_url = f"https://iiif.bodleian.ox.ac.uk/iiif/manifest/{uuid}.json"
            return manifest_url, uuid

        return None, None
