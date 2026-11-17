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


def split_pdf(file_path, page_ranges, output_zip_path):
    """Parse range strings and bundle extracted PDFs into a ZIP archive."""
    file_path = Path(file_path)
    output_zip_path = Path(output_zip_path)
    with fitz.open(file_path) as src:
        groups = _parse_page_ranges(page_ranges, src.page_count)
        with zipfile.ZipFile(output_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for idx, pages in enumerate(groups, start=1):
                part = fitz.open()
                try:
                    for p in pages:
                        part.insert_pdf(src, from_page=p, to_page=p)
                    buf = io.BytesIO()
                    part.save(buf)
                    data = buf.getvalue()
                finally:
                    part.close()
                start_p = pages[0] + 1
                end_p = pages[-1] + 1
                name = (
                    f"{file_path.stem}_pages_{start_p}.pdf"
                    if start_p == end_p
                    else f"{file_path.stem}_pages_{start_p}-{end_p}.pdf"
                )
                # Avoid duplicate names if same range repeated
                if name in zf.namelist():
                    name = f"{file_path.stem}_part_{idx}_pages_{start_p}-{end_p}.pdf"
                zf.writestr(name, data)
    return output_zip_path


def rotate_pdf(file_path, angle, output_path):
    """Rotate all pages by 90, 180, or 270 degrees."""
    angle = int(angle)
    if angle not in (90, 180, 270):
        raise ValueError("Rotation angle must be 90, 180, or 270 degrees.")
    with fitz.open(file_path) as doc:
        for page in doc:
            page.set_rotation((page.rotation + angle) % 360)
        doc.save(output_path)
    return output_path


def protect_pdf(file_path, password, output_path):
    """Encrypt PDF with AES-256 using PyMuPDF."""
    if not password:
        raise ValueError("Password is required for encryption.")
    with fitz.open(file_path) as doc:
        perm = int(
            fitz.PDF_PERM_ACCESSIBILITY
            | fitz.PDF_PERM_PRINT
            | fitz.PDF_PERM_COPY
            | fitz.PDF_PERM_ANNOTATE
        )
        doc.save(
            output_path,
            encryption=fitz.PDF_ENCRYPT_AES_256,
            user_pw=password,
            owner_pw=password,
            permissions=perm,
        )
    return output_path


def unlock_pdf(file_path, password, output_path):
    """Decrypt a password-protected PDF using PyMuPDF."""
    with fitz.open(file_path) as doc:
        if doc.needs_pass:
            if not password:
                raise ValueError("This PDF is encrypted. A password is required.")
            ok = doc.authenticate(password)
            if not ok:
                raise ValueError("Incorrect password for encrypted PDF.")
        # Save without encryption
        doc.save(output_path, encryption=fitz.PDF_ENCRYPT_NONE)
    return output_path


def add_watermark(file_path, text, output_path):
    """Add diagonal semi-transparent watermark text across all pages."""
    if not text or not text.strip():
        raise ValueError("Watermark text cannot be empty.")
    with fitz.open(file_path) as doc:
        for page in doc:
            rect = page.rect
            # Centered text box; rotate for diagonal watermark
            fontsize = max(24, min(rect.width, rect.height) / 8)
            # Use a large textbox to keep text centered after rotation
            box = fitz.Rect(-rect.width, rect.height * 0.25, rect.width * 2, rect.height * 0.75)
            page.insert_textbox(
                box,
                text,
                fontsize=fontsize,
                fontname="helv",
                color=(0.6, 0.6, 0.6),
                fill_opacity=0.18,
                stroke_opacity=0.18,
                align=fitz.TEXT_ALIGN_CENTER,
                rotate=45,
                overlay=True,
            )
        doc.save(output_path)
    return output_path
