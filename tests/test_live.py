import unittest
import sys
import os
import time

# Add parent directory to path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from iiif_downloader.cli import resolve_url
from iiif_downloader.core import IIIFDownloader

class TestProviders(unittest.TestCase):
    """
    Live tests for Vatican, Gallica, and Oxford.
    Does NOT download full images. Just verifies parsing and metadata.
    """

    def test_01_vatican_resolver(self):
        print("\n[Test] Vatican Resolver & Manifest Fetching...")
        url = "https://digi.vatlib.it/view/MSS_Urb.lat.1779"
        
        # 1. Resolve
        manifest_url, suggested_id = resolve_url(url)
        self.assertEqual(manifest_url, "https://digi.vatlib.it/iiif/MSS_Urb.lat.1779/manifest.json")
        self.assertEqual(suggested_id, "MSS_Urb.lat.1779")
        
        # 2. Initialize Downloader (fetches manifest)
        d = IIIFDownloader(manifest_url, output_dir="tests/out", output_name="test_vat.pdf")
        
        self.assertTrue("Urb.lat.1779" in d.label)
        self.assertGreater(len(d.get_canvases()), 10) # Should have many pages
        
        # Vatican usually does NOT have a native PDF
        pdf_url = d.get_pdf_url()
        if pdf_url:
            print(f"   (Note: Found unexpected PDF for Vatican: {pdf_url})")
        else:
            print("   (Confirmed: No native PDF for this MS)")
        
        time.sleep(1) # Be polite

    def run_partial_download(self, url, name):
        """Helper to run a real download of first 3 pages."""
        print(f"\n   [Partial Download] Testing {name} with: {url}")
        d = IIIFDownloader(url, output_dir="tests/out", output_name=f"{name}.pdf", keep_temp=True)
        
        # Hack: Limit to 3 pages to save time/bandwidth
        canvases = d.get_canvases()
        if len(canvases) > 3:
            print(f"   (Truncating job from {len(canvases)} to 3 pages for testing)")
            # We need to modify the internal manifest structure to trick 'run'
            if 'sequences' in d.manifest and d.manifest['sequences']:
                d.manifest['sequences'][0]['canvases'] = d.manifest['sequences'][0]['canvases'][:3]
        
        d.run()
        
        # Verify PDF
        self.assertTrue(os.path.exists(d.output_path), "PDF was not created")
        self.assertGreater(os.path.getsize(d.output_path), 1024, "PDF is too small (might be empty)")
        print(f"   (PDF Created: {d.output_path}, Size: {os.path.getsize(d.output_path)} bytes)")

    def test_01_vatican(self):
        """Test Vatican: Resolver + Partial Download."""
        print("\n[Test] Vatican...")
        url = "https://digi.vatlib.it/view/MSS_Urb.lat.1779"
        
        # 1. Resolve
        manifest_url, _ = resolve_url(url)
        self.assertIn("manifest.json", manifest_url)
        
        # 2. Download
        self.run_partial_download(manifest_url, "test_vatican")

    def test_02_gallica(self):
        """Test Gallica: Resolver + Partial Download."""
        print("\n[Test] Gallica...")
        url = "https://gallica.bnf.fr/ark:/12148/bpt6k9604118j"
        
        # 1. Resolve
        manifest_url, _ = resolve_url(url)
        self.assertEqual(manifest_url, "https://gallica.bnf.fr/iiif/ark:/12148/bpt6k9604118j/manifest.json")
        
        # 2. Download
        self.run_partial_download(manifest_url, "test_gallica")

    def test_03_oxford(self):
        """Test Oxford: Resolver + Partial Download."""
        print("\n[Test] Oxford...")
        # MS. Bodl. Rolls 23
        url = "https://digital.bodleian.ox.ac.uk/objects/080f88f5-7586-4b8a-8064-63ab3495393c/"
        
        # 1. Resolve
        manifest_url, _ = resolve_url(url)
        expected = "https://iiif.bodleian.ox.ac.uk/iiif/manifest/080f88f5-7586-4b8a-8064-63ab3495393c.json"
        self.assertEqual(manifest_url, expected)
        
        # 2. Download 
        # Note: Oxford might have a native PDF, so we use --prefer-images logic implicitly via manual check?
        # Actually core.py logic prioritizes PDF unless prefer_images is True.
        # Let's force image download to test the image pipeline.
        
        print("   (Testing Image Pipeline - Ignoring Native PDF)")
        d = IIIFDownloader(manifest_url, output_dir="tests/out", output_name="test_oxford.pdf", prefer_images=True)
        
        # Truncate
        if 'sequences' in d.manifest and d.manifest['sequences']:
             d.manifest['sequences'][0]['canvases'] = d.manifest['sequences'][0]['canvases'][:3]
             
        d.run()
        self.assertTrue(os.path.exists(d.output_path))
        print(f"   (PDF Created: {d.output_path})")

if __name__ == '__main__':
    unittest.main()
