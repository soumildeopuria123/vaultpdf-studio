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
