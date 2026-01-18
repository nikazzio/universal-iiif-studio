from .base import BaseResolver


class GallicaResolver(BaseResolver):
    def can_resolve(self, url_or_id):
        return "gallica.bnf.fr" in url_or_id

    def get_manifest_url(self, url_or_id):
        # Input: https://gallica.bnf.fr/ark:/12148/btv1b84260335
        # Output: https://gallica.bnf.fr/iiif/ark:/12148/btv1b84260335/manifest.json

        clean_url = url_or_id.split("?")[0].strip("/")

        # Extract ARK ID part (everything after ark:/...)
        if "ark:/" not in clean_url:
            return None, None

        parts = clean_url.split("ark:/")
        if len(parts) <= 1:
            return None, None

        ark_suffix = parts[1]

        # If it already looks like a manifest URL
        if clean_url.endswith("/manifest.json"):
            ms_id = ark_suffix.replace("/manifest.json", "").split("/")[-1]
            return clean_url, ms_id

        ark_components = ark_suffix.split("/")
        if len(ark_components) < 2:
            return None, None

        repo_id = ark_components[0]  # 12148
        doc_id = ark_components[1]  # btv1b84260335

        full_ark = f"ark:/{repo_id}/{doc_id}"
        manifest_url = f"https://gallica.bnf.fr/iiif/{full_ark}/manifest.json"
        return manifest_url, doc_id
