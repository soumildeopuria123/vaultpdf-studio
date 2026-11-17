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
        src.close()


def compress_to_target(input_path, output_path, target_kb):
    """Iteratively compress a PDF until <= target_kb*1024 bytes or best effort.

    Returns (original_size, final_size, target_met).
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    target_bytes = int(float(target_kb) * 1024)
    if target_bytes <= 0:
        raise ValueError("Target size must be greater than 0 KB.")

    original_size = input_path.stat().st_size

    # Try progressive strategies: in-place image recompress, then rasterize-rebuild at lower DPI/quality.
    # Step 1: lossless-ish cleanup
    doc = fitz.open(input_path)
    try:
        _save_doc(doc, output_path)
    finally:
        doc.close()
    if output_path.stat().st_size <= target_bytes:
        final_size = output_path.stat().st_size
        return original_size, final_size, True

    # Step 2: recompress embedded images at decreasing JPEG quality
    for quality in (75, 60, 45, 35, 25):
        doc = fitz.open(input_path)
        try:
            _recompress_images(doc, zoom=1.0, jpeg_quality=quality)
            _save_doc(doc, output_path)
        finally:
            doc.close()
        if output_path.stat().st_size <= target_bytes:
            final_size = output_path.stat().st_size
            return original_size, final_size, True

    # Step 3: rasterize & rebuild pages at decreasing DPI/quality (strongest, may affect text selectability)
    for dpi, quality in ((144, 70), (120, 60), (96, 50), (72, 40), (72, 30)):
        try:
            _render_and_rebuild(input_path, output_path, dpi=dpi, jpeg_quality=quality)
        except Exception:
            continue
        if output_path.stat().st_size <= target_bytes:
            final_size = output_path.stat().st_size
            return original_size, final_size, True

    # Best effort: keep smallest result we have (output_path currently holds last attempt)
    final_size = output_path.stat().st_size if output_path.exists() else original_size
    # If somehow larger than original, fall back to a cleaned copy of original
    if final_size > original_size:
        doc = fitz.open(input_path)
        try:
            _save_doc(doc, output_path)
        finally:
            doc.close()
        final_size = output_path.stat().st_size
    return original_size, final_size, final_size <= target_bytes
