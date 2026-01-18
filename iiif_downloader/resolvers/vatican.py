from .base import BaseResolver


class VaticanResolver(BaseResolver):
    def can_resolve(self, url_or_id):
        return "digi.vatlib.it" in url_or_id

    def get_manifest_url(self, url_or_id):
        ms_id = url_or_id.strip("/").split("/")[-1]
        manifest_url = f"https://digi.vatlib.it/iiif/{ms_id}/manifest.json"
        return manifest_url, ms_id
