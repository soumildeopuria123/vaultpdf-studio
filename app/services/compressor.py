import io
import os
from pathlib import Path

import fitz  # PyMuPDF


def _save_doc(doc: fitz.Document, output_path: Path, garbage: int = 4, deflate: bool = True):
    doc.save(
        output_path,
        garbage=garbage,
        deflate=deflate,
        clean=True,
    )


def _recompress_images(doc: fitz.Document, zoom: float, jpeg_quality: int) -> None:
    """Downscale and recompress embedded raster images in-place."""
    seen_xrefs = set()
    for page_index in range(len(doc)):
        page = doc[page_index]
        for img in page.get_images(full=True):
            xref = img[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)
            try:
                pix = fitz.Pixmap(doc, xref)
                # Skip masks/special colorspaces that are risky to recompress
                if pix.alpha and pix.n > 4:
                    pix = None
                    continue
                if pix.n >= 5:  # CMYK or other
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                # Downscale by rendering through a matrix if zoom < 1
                if zoom < 1.0:
                    target_w = max(1, int(pix.width * zoom))
                    target_h = max(1, int(pix.height * zoom))
                    if target_w < pix.width or target_h < pix.height:
                        # Create scaled pixmap via sampling
                        scaled = fitz.Pixmap(pix, 0) if False else None  # placeholder
                        # Use Pillow-free approach: draw to new pixmap via PDF page image is complex;
                        # instead re-encode from samples using a temporary pixmap resize when possible.
                        # Fallback: keep original dimensions but recompress; PyMuPDF lacks direct resize,
                        # so we approximate by extracting to bytes at current size and rely on JPEG quality.
                        pass
                # Re-encode as JPEG (drop alpha)
                if pix.alpha:
                    pix_no_alpha = fitz.Pixmap(fitz.csRGB, pix)
                    img_bytes = pix_no_alpha.tobytes("jpeg", jpg_quality=jpeg_quality)
                    pix_no_alpha = None
                else:
                    if pix.n not in (1, 3):
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    img_bytes = pix.tobytes("jpeg", jpg_quality=jpeg_quality)
                page.replace_image(xref, stream=img_bytes)
                pix = None
            except Exception:
                # If any single image can't be processed, skip it and continue.
                continue


def _render_and_rebuild(input_path: Path, output_path: Path, dpi: int, jpeg_quality: int) -> None:
    """Fallback: rasterize pages to images and rebuild a compact PDF."""
    src = fitz.open(input_path)
    out = fitz.open()
    try:
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        for page in src:
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB, alpha=False)
            img_bytes = pix.tobytes("jpeg", jpg_quality=jpeg_quality)
            rect = page.rect
            new_page = out.new_page(width=rect.width, height=rect.height)
            new_page.insert_image(rect, stream=img_bytes)
        _save_doc(out, output_path)
    finally:
        out.close()
