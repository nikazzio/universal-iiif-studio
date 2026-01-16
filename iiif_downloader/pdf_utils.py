from pathlib import Path
from pdf2image import convert_from_path, convert_from_bytes
import logging

logger = logging.getLogger(__name__)

def load_pdf_page(pdf_source, page_idx, dpi=300):
    """
    Load a single page from a PDF source (Path or bytes) and convert to a PIL Image.
    Returns (Image, error_message).
    """
    try:
        if isinstance(pdf_source, (str, Path)):
            pages = convert_from_path(pdf_source, first_page=page_idx, last_page=page_idx, dpi=dpi)
        else:
            pages = convert_from_bytes(pdf_source, first_page=page_idx, last_page=page_idx, dpi=dpi)
        
        if not pages:
            return None, f"Pagina {page_idx} non trovata nel PDF."
        
        return pages[0], None
    except Exception as e:
        logger.error(f"Error loading PDF page: {e}")
        return None, str(e)
