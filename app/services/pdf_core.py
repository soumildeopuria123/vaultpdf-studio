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
    finally:
        merged.close()
    return output_path


def _parse_page_ranges(range_str: str, max_pages: int) -> list[list[int]]:
    """Parse 1-indexed page ranges like '1-3, 5, 7-9' into groups of 0-indexed pages."""
    if not range_str or not range_str.strip():
        raise ValueError("Page ranges cannot be empty.")
    groups: list[list[int]] = []
    tokens = [t.strip() for t in range_str.split(",") if t.strip()]
    if not tokens:
        raise ValueError("No valid page ranges provided.")
    for token in tokens:
        if re.fullmatch(r"\d+", token):
            start = end = int(token)
        elif re.fullmatch(r"\d+\s*-\s*\d+", token):
            a, b = [int(x.strip()) for x in token.split("-", 1)]
            start, end = a, b
        else:
            raise ValueError(f"Invalid page range token: '{token}'")
        if start < 1 or end < 1 or start > end:
            raise ValueError(f"Invalid page range: '{token}'")
        if end > max_pages:
            raise ValueError(
                f"Page range '{token}' exceeds document length ({max_pages} pages)."
            )
        groups.append(list(range(start - 1, end)))
    return groups
