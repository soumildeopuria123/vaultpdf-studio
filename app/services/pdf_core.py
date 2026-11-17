import io
import re
import zipfile
from pathlib import Path

import fitz  # PyMuPDF


def merge_pdfs(file_paths, output_path):
    """Merge multiple PDFs in specified order."""
    if not file_paths:
        raise ValueError("No PDF files provided for merge.")
    merged = fitz.open()
    try:
        for path in file_paths:
            with fitz.open(path) as src:
                merged.insert_pdf(src)
        merged.save(output_path)
