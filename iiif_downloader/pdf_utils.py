from pathlib import Path
from pdf2image import convert_from_path, convert_from_bytes
import logging
from pathlib import Path
from pdf2image import convert_from_path, convert_from_bytes
from PIL import Image as PILImage
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

def generate_pdf_from_images(image_paths, output_path):
    """
    Combine a list of image paths into a single PDF.
    """
    try:
        images = []
        for p in image_paths:
            if Path(p).exists():
                img = PILImage.open(p)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                images.append(img)
        
        if images:
            images[0].save(output_path, save_all=True, append_images=images[1:])
            return True, f"PDF creato con successo: {output_path}"
        else:
            return False, "Nessuna immagine valida trovata."
    except Exception as e:
        logger.error(f"Error creating PDF: {e}")
        return False, str(e)

def convert_pdf_to_images(pdf_path, output_dir, progress_callback=None):
    """
    Convert a PDF into a series of JPG images in output_dir.
    """
    try:
        from pdf2image import convert_from_path, pdfinfo_from_path
        import os
        
        # Get info first
        info = pdfinfo_from_path(pdf_path)
        total_pages = info["Pages"]
        
        # Process in chunks to avoid memory issues
        chunk_size = 10
        for i in range(1, total_pages + 1, chunk_size):
            pages = convert_from_path(pdf_path, first_page=i, last_page=min(i + chunk_size - 1, total_pages))
            
            for j, page in enumerate(pages):
                page_num = i + j
                out_name = f"pag_{page_num-1:04d}.jpg"
                page.save(os.path.join(output_dir, out_name), "JPEG", quality=90)
            
            if progress_callback:
                progress_callback(min(i + chunk_size - 1, total_pages), total_pages)
                
        return True, f"Estratte {total_pages} pagine."
    except Exception as e:
        logger.error(f"Error converting PDF: {e}")
        return False, str(e)
