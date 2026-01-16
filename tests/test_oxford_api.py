"""
Legacy test for Oxford/Bodleian API endpoint.

Note: This API endpoint is deprecated (returns 404) as of January 2026.
This test is kept for historical reference.
"""
import requests
from iiif_downloader.utils import DEFAULT_HEADERS

url = "https://digital.bodleian.ox.ac.uk/api/search/catalog/"
params = {"q": "dante", "format": "json", "rows": 1}
try:
    r = requests.get(url, params=params, headers=DEFAULT_HEADERS, timeout=15)
    print(f"Status: {r.status_code}")
    print(f"Content length: {len(r.text)}")
    if r.status_code == 200:
        print(r.text[:500])
except Exception as e:
    print(f"Error: {e}")
