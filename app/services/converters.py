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
