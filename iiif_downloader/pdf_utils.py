import logging
from pathlib import Path

import pymupdf as fitz  # PyMuPDF
from PIL import Image as PILImage

from iiif_downloader.logger import get_logger

logger = get_logger(__name__)

# PDF parsing/rendering can fail in many ways depending on the environment.
# pylint: disable=broad-exception-caught


class PdfPasswordProtectedError(RuntimeError):
    pass


def _open_pdf_document(pdf_source, password: str | None = None) -> fitz.Document:
    try:
        if isinstance(pdf_source, (str, Path)):
            doc = fitz.open(str(pdf_source))
        else:
            doc = fitz.open(stream=pdf_source, filetype="pdf")
    except Exception as exc:
        raise RuntimeError(f"Impossibile aprire il PDF: {exc}") from exc

    # Encrypted docs need explicit authentication.
    if getattr(doc, "needs_pass", False):
        if not password:
            doc.close()
            raise PdfPasswordProtectedError(
                "PDF protetto da password. Rimuovi la password o fornisci una versione non protetta."
            )
        if not doc.authenticate(password):
            doc.close()
            raise PdfPasswordProtectedError("Password PDF non valida.")

    return doc


def _render_page_to_pil(page: fitz.Page, dpi: int = 300) -> PILImage.Image:
    dpi = int(dpi or 300)
    dpi = max(50, min(dpi, 1200))
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB, alpha=False)
    return PILImage.frombytes("RGB", (pix.width, pix.height), pix.samples)


def load_pdf_page(
    pdf_source,
    page_idx,
    dpi=300,
    password: str | None = None,
    return_error: bool = False,
):
    """Load a single PDF page and return it as a PIL.Image.

    `page_idx` is 1-based (page 1 == first page) to match the rest of the app.

    By default returns the image (or None). If `return_error=True`, returns
    `(image, error_message)` where error_message is None on success.
    """

    try:
        doc = _open_pdf_document(pdf_source, password=password)
        try:
            page_number = int(page_idx) - 1
            if page_number < 0 or page_number >= doc.page_count:
                msg = f"Pagina {page_idx} non trovata nel PDF."
                return (None, msg) if return_error else None
            page = doc.load_page(page_number)
            img = _render_page_to_pil(page, dpi=dpi)
            return (img, None) if return_error else img
        finally:
            doc.close()
    except PdfPasswordProtectedError as exc:
        logger.warning("Password-protected PDF blocked: %s", exc)
        return (None, str(exc)) if return_error else None
    except Exception as exc:
        logger.error("Error loading PDF page: %s", exc)
        return (None, str(exc)) if return_error else None


def generate_pdf_from_images(image_paths, output_path):
    """
    Combine a list of image paths into a single PDF.
    """
    try:
        images = []
        for p in image_paths:
            if Path(p).exists():
                img = PILImage.open(p)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                images.append(img)

        if images:
            images[0].save(output_path, save_all=True, append_images=images[1:])
            return True, f"PDF creato con successo: {output_path}"

        return False, "Nessuna immagine valida trovata."
    except Exception as e:
        logger.error("Error creating PDF: %s", e)
        return False, str(e)


def convert_pdf_to_images(
    pdf_path,
    output_dir,
    progress_callback=None,
    dpi: int = 300,
    jpeg_quality: int = 90,
    password: str | None = None,
):
    """Convert a PDF into a series of JPG images in `output_dir`.

    - DPI is configurable (default 300, good for OCR).
    - Detects password-protected PDFs and returns a user-friendly message.
    """

    try:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        doc = _open_pdf_document(pdf_path, password=password)
        try:
            total_pages = int(doc.page_count)
            if total_pages <= 0:
                return False, "PDF vuoto o non valido."

            jpeg_quality = int(jpeg_quality or 90)
            jpeg_quality = max(30, min(jpeg_quality, 95))

            for page_number in range(total_pages):
                page = doc.load_page(page_number)
                img = _render_page_to_pil(page, dpi=dpi)
                out_name = f"pag_{page_number:04d}.jpg"
                img.save(str(out_dir / out_name), "JPEG", quality=jpeg_quality)

                if progress_callback:
                    progress_callback(page_number + 1, total_pages)

            return True, f"Estratte {total_pages} pagine."
        finally:
            doc.close()
    except PdfPasswordProtectedError as exc:
        logger.warning("Password-protected PDF blocked: %s", exc)
        return False, str(exc)
    except Exception as exc:
        logger.error("Error converting PDF: %s", exc)
        return False, str(exc)
