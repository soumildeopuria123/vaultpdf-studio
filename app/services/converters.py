import io
import platform
import zipfile
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image


def pdf_to_word(pdf_path, docx_path):
    """Convert PDF to .docx using pdf2docx.Converter."""
    from pdf2docx import Converter

    pdf_path = str(pdf_path)
    docx_path = str(docx_path)
    cv = Converter(pdf_path)
    try:
        cv.convert(docx_path, start=0, end=None)
    finally:
        cv.close()
    return docx_path


def word_to_pdf(docx_path, pdf_path):
    """Convert .docx to PDF using docx2pdf on Windows."""
    if platform.system() != "Windows":
        raise RuntimeError(
            "Word to PDF conversion requires Microsoft Word on Windows (docx2pdf). "
            "This feature is not available on this system."
        )
    try:
        from docx2pdf import convert
    except Exception as e:
        raise RuntimeError(f"docx2pdf is not available: {e}")
    try:
        # docx2pdf uses MS Word via COM; must use absolute paths
        convert(str(Path(docx_path).resolve()), str(Path(pdf_path).resolve()))
    except Exception as e:
        msg = str(e)
        if "Word" in msg or "CoInitialize" in msg or "comtypes" in msg or "dispatch" in msg.lower():
            raise RuntimeError(
                "Microsoft Word is required for Word to PDF conversion but was not found or failed to initialize. "
                "Please install Microsoft Word and try again."
            )
        raise RuntimeError(f"Word to PDF conversion failed: {e}")
    if not Path(pdf_path).exists():
        raise RuntimeError(
            "Word to PDF conversion failed: output file was not created. "
            "Ensure Microsoft Word is installed and the document is valid."
        )
    return pdf_path


def pdf_to_images_zip(pdf_path, output_zip_path, fmt="png", dpi=150):
    """Export all pages as PNG/JPG inside a ZIP file."""
    fmt = (fmt or "png").lower()
    if fmt not in ("png", "jpg", "jpeg"):
        raise ValueError("Image format must be 'png' or 'jpg'.")
    ext = "jpg" if fmt in ("jpg", "jpeg") else "png"
    pil_fmt = "JPEG" if ext == "jpg" else "PNG"
    zoom = max(36, int(dpi)) / 72.0
    mat = fitz.Matrix(zoom, zoom)

    pdf_path = Path(pdf_path)
    output_zip_path = Path(output_zip_path)
    with fitz.open(pdf_path) as doc:
        with zipfile.ZipFile(output_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for i, page in enumerate(doc, start=1):
                pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB, alpha=False)
                if pil_fmt == "JPEG":
