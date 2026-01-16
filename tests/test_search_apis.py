"""
Test script for library search APIs (Gallica SRU and Oxford).

Note: Oxford API is deprecated as of Jan 2026 and will return errors.
Run from project root: python -m tests.test_search_apis
"""
import requests
from typing import Dict, List

def test_gallica(query: str):
    print(f"Testing Gallica with query: {query}")
    url = "https://gallica.bnf.fr/SRU"
    params = {
        "operation": "searchRetrieve",
        "version": "1.2",
        "query": f'dc.title all "{query}" and dc.type all "manuscrit"',
        "maximumRecords": "5",
        "responseFormat": "json" # Testing if this works
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        print(f"Status Code: {r.status_code}")
        print(f"Content-Type: {r.headers.get('Content-Type')}")
        if "json" in r.headers.get("Content-Type", "").lower():
            print("Successfully got JSON!")
            print(r.json().get("searchRetrieveResponse", {}).get("records", [])[:1])
        else:
            print("Returned XML instead of JSON.")
            # print(r.text[:500])
    except Exception as e:
        print(f"Error: {e}")

def test_oxford(query: str):
    print(f"\nTesting Oxford with query: {query}")
    url = "https://digital.bodleian.ox.ac.uk/api/search/"
    params = {
        "q": query,
        "format": "json",
        "rows": 5
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        print(f"Status Code: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            docs = data.get("response", {}).get("docs", [])
            print(f"Found {len(docs)} documents.")
            for doc in docs:
                print(f"- {doc.get('title_ssm', [doc.get('title')])[0]} (UUID: {doc.get('uuid')})")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_gallica("dante")
    test_oxford("dante")
