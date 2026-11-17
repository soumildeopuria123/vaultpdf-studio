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
