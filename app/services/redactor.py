import io
from pathlib import Path

import fitz  # PyMuPDF


def render_page_preview(pdf_path, page_num):
    """Render a PDF page as a high-DPI PNG byte stream for the frontend canvas."""
    pdf_path = Path(pdf_path)
    page_num = int(page_num)
    with fitz.open(pdf_path) as doc:
        if page_num < 0 or page_num >= doc.page_count:
            raise ValueError(f"Page number {page_num} out of range (0-{doc.page_count - 1}).")
        page = doc[page_num]
        # High-DPI render for clear canvas preview
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB, alpha=False)
        return pix.tobytes("png")


def redact_regions(input_path, output_path, boxes):
    """Permanently redact normalized regions.

    boxes: [{"page": int, "x0": float, "y0": float, "x1": float, "y1": float}] with coords 0.0-1.0.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
