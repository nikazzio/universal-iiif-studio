from .base import BaseResolver

class GallicaResolver(BaseResolver):
    def can_resolve(self, url_or_id):
        return "gallica.bnf.fr" in url_or_id

    def get_manifest_url(self, url_or_id):
        # Input: https://gallica.bnf.fr/ark:/12148/btv1b84260335
        # Output: https://gallica.bnf.fr/iiif/ark:/12148/btv1b84260335/manifest.json
        
        # Clean URL
        clean_url = url_or_id.split("?")[0].strip("/")
        
        # Extract ARK ID part (everything after ark:/...)
        if "ark:/" in clean_url:
            # Split by ark:/ to get the ID part safely
            parts = clean_url.split("ark:/")
            if len(parts) > 1:
                ark_suffix = parts[1]
                
                # If the URL ends with .item or /date or similar extra paths, strip them?
                # Usually Gallica URLs are just .../ark:/12148/btv1b...
                # But sometimes they might have extra stuff. 
                # For IIIF manifest, we need the bare ARK component e.g. "12148/btv1b84260335"
                
                # If it already looks like a manifest URL
                if clean_url.endswith("/manifest.json"):
                     return clean_url, ark_suffix.replace("/manifest.json", "").split("/")[-1]

                # If it's a viewer URL e.g. .../f1.item or similar, we should be careful.
                # However, usually taking the first two components of the ark suffix is enough?
                # e.g. 12148/btv1b84260335
                
                ark_components = ark_suffix.split("/")
                if len(ark_components) >= 2:
                    repo_id = ark_components[0] # 12148
                    doc_id = ark_components[1]  # btv1b84260335
                    
                    full_ark = f"ark:/{repo_id}/{doc_id}"
                    ms_id = doc_id
                    
                    manifest_url = f"https://gallica.bnf.fr/iiif/{full_ark}/manifest.json"
                    return manifest_url, ms_id
        
        return None, None
