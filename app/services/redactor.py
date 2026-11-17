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
    if not isinstance(boxes, list):
        raise ValueError("Boxes payload must be a list.")

    with fitz.open(input_path) as doc:
        # Group boxes by page for efficient application
        by_page: dict[int, list[dict]] = {}
        for i, box in enumerate(boxes):
            if not isinstance(box, dict):
                raise ValueError(f"Box at index {i} is not an object.")
            try:
                page_idx = int(box["page"])
                x0 = float(box["x0"])
                y0 = float(box["y0"])
                x1 = float(box["x1"])
                y1 = float(box["y1"])
            except Exception as e:
                raise ValueError(f"Invalid box at index {i}: {e}")
            if page_idx < 0 or page_idx >= doc.page_count:
                raise ValueError(f"Box page {page_idx} out of range.")
            # Clamp normalized coords
            x0 = max(0.0, min(1.0, x0))
            y0 = max(0.0, min(1.0, y0))
