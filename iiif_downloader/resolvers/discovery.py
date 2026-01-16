import re
import requests
import xml.etree.ElementTree as ET
from typing import Optional, Tuple, List, Dict
from iiif_downloader.utils import DEFAULT_HEADERS

def resolve_shelfmark(library: str, shelfmark: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Resolve a library name and shelfmark/ID into a IIIF Manifest URL.
    Returns (manifest_url, doc_id).
    """
    s = shelfmark.strip()
    
    if library == "Vaticana (BAV)":
        # Handle full URL if pasted accidentally
        if "digi.vatlib.it" in s:
            ms_id = s.strip("/").split("/")[-1]
            return f"https://digi.vatlib.it/iiif/{ms_id}/manifest.json", ms_id
            
        # SAFETY: Protect against Oxford UUIDs being pasted here
        uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        if re.search(uuid_pattern, s.lower()):
            return None, "L'ID sembra un UUID Oxford. Seleziona 'Bodleian (Oxford)' come biblioteca."

        # Standardize shelfmark: "Urb. Lat. 1779" -> "MSS_Urb.lat.1779"
        # 1. Remove all spaces
        clean_s = s.replace(" ", "")
        # 2. Case normalization (BAV often uses 'lat.' instead of 'Lat.')
        clean_s = clean_s.replace("Lat.", "lat.").replace("Gr.", "gr.").replace("Vat.", "vatic.").replace("Pal.", "pal.")
        
        clean_id = clean_s if clean_s.startswith("MSS_") else f"MSS_{clean_s}"
        return f"https://digi.vatlib.it/iiif/{clean_id}/manifest.json", clean_s
        
    elif library == "Gallica (BnF)":
        # Cleanup input
        s = s.strip().strip("/")
        # Handle cases where user pastes just the ID
        if "ark:/" not in s:
            if s and len(s) > 3 and s[0] in ('b', 'c'):
                s = f"ark:/12148/{s}"
            else:
                return None, "Gallica richiede un ID ARK o un identificatore Gallica (es. btv1b10033406t, bpt6k9761787t)"
        
        doc_id = s.split("/")[-1]
        return f"https://gallica.bnf.fr/iiif/{s}/manifest.json", doc_id
        
    elif library == "Bodleian (Oxford)":
        # UUID or full URL
        # Robustness: strip trailing slashes to avoid empty ms_id
        ms_id = s.strip("/").split("/")[-1].replace(".json", "")
        uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        if re.search(uuid_pattern, ms_id.lower()):
            return f"https://iiif.bodleian.ox.ac.uk/iiif/manifest/{ms_id.lower()}.json", ms_id
            
        return None, "Bodleian richiede un UUID valido (es. 080f88f5...)"
        
    return None, None

def search_gallica(query: str, max_records: int = 10) -> List[Dict]:
    """
    Search Gallica manuscripts using the official SRU API.
    
    Uses the BnF SRU (Search/Retrieve via URL) protocol with CQL queries.
    Documentation: https://api.bnf.fr/fr/api-gallica-de-recherche
    
    Args:
        query: Search term (searches in title field)
        max_records: Maximum number of results to return (1-50)
    
    Returns:
        List of dictionaries containing manuscript information
    """
    url = "https://gallica.bnf.fr/SRU"
    
    # Build CQL query: search in title and filter by manuscript type
    # Note: 'manuscrit' is the correct French term used by Gallica
    cql_query = f'(dc.title all "{query}") and (dc.type all "manuscrit")'
    
    params = {
        "operation": "searchRetrieve",
        "version": "1.2",
        "query": cql_query,
        "maximumRecords": str(min(max_records, 50)),  # API limit is 50
        "startRecord": "1"
    }
    
    results = []
    try:
        r = requests.get(url, params=params, headers=DEFAULT_HEADERS, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.text)
        
        # Define XML namespaces for parsing
        ns = {
            'srw': 'http://www.loc.gov/zing/srw/',
            'dc': 'http://purl.org/dc/elements/1.1/',
            'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/'
        }
        
        # Parse each result record
        for record in root.findall('.//srw:record', ns):
            title_elem = record.find('.//dc:title', ns)
            identifier_elem = record.find('.//dc:identifier', ns)
            
            if title_elem is not None and identifier_elem is not None:
                identifier = identifier_elem.text
                
                # Extract ARK identifier from the URL
                if identifier and "ark:/" in identifier:
                    ark = identifier[identifier.find("ark:/"):]
                    doc_id = ark.split("/")[-1]  # Extract btv... ID
                    
                    results.append({
                        "id": doc_id,
                        "title": title_elem.text or "Sans titre",
                        "manifest_url": f"https://gallica.bnf.fr/iiif/{ark}/manifest.json",
                        "preview_url": f"https://gallica.bnf.fr/{ark}.thumbnail"
                    })
                    
    except requests.RequestException as e:
        print(f"⚠️ Errore nella ricerca Gallica: {e}")
    except ET.ParseError as e:
        print(f"⚠️ Errore nel parsing XML da Gallica: {e}")
    except Exception as e:
        print(f"⚠️ Errore imprevisto nella ricerca Gallica: {e}")
        
    return results


def search_oxford(query: str) -> List[Dict]:
    """
    Oxford/Bodleian search is currently unavailable.
    
    The Digital Bodleian public search API has been removed (returns 404).
    As of January 2026, there is no publicly documented API endpoint for 
    searching the Bodleian manuscript collection programmatically.
    
    Alternative: Users should search manually at https://digital.bodleian.ox.ac.uk/
    and paste the manifest URL or UUID directly into the resolver.
    
    Args:
        query: Search term (currently unused)
    
    Returns:
        Empty list (API no longer available)
    """
    print("ℹ️ La ricerca automatica per Oxford/Bodleian non è disponibile.")
    print("   Cerca manualmente su https://digital.bodleian.ox.ac.uk/")
    print("   e copia l'UUID o l'URL del manifest nel campo 'ID o URL'.")
    return []
