# VaultPDF Studio (Local PDF Utility Studio)

**VaultPDF Studio** is a complete, 100% offline, privacy-first PDF toolkit that runs locally on your machine. It is a zero-upload alternative to cloud PDF services: files are processed in isolated temporary workspaces on disk and automatically deleted immediately after each download/response.

Built with **Python FastAPI** and a **Light Neo-Brutalism** frontend (no glassmorphism, no blur effects, no dark mode gradients).

## 🔗 Live Demo

**Try it now: [https://stanford-cam-tap-joining.trycloudflare.com](https://stanford-cam-tap-joining.trycloudflare.com)**

> The live demo is served from the developer's machine through a temporary Cloudflare tunnel, so it may be unavailable at times. For a permanent HTTPS deployment, follow [`DEPLOY_SELF_HOST.md`](DEPLOY_SELF_HOST.md).

## Privacy Architecture

- **100% offline processing:** All PDF operations run locally on your computer. No files are uploaded to any third-party server.
- **Zero uploads:** The browser talks only to your local FastAPI server (`localhost`).
- **Isolated per-request workspaces:** Every API request creates a unique workspace inside `.temp_workspace/`.
- **Automatic cleanup:** Uploaded inputs and generated outputs are scheduled for deletion via FastAPI `BackgroundTasks` immediately after the response/download completes (best-effort cleanup on errors as well).
- **No persistence by design:** The app does not store document history or retain processed files.

> Note: `.temp_workspace/` is used as an ephemeral scratch area. Do not point it at shared or sensitive directories.

## Features

| Tool | What it does |
| --- | --- |
| **Merge** | Combine multiple PDFs in a user-specified order (with drag-and-drop reordering). |
| **Split** | Extract page ranges like `1-3, 5, 7-9` (1-indexed) and download results as a ZIP of PDFs. |
| **Compress to Target KB** | Iteratively downscales/recompresses embedded images (and falls back to rasterized rebuild when needed) to reach a target size, reporting original vs. final size and whether the target was met. |
| **True Redact** | Interactive HTML5 canvas: preview pages, draw redaction rectangles, switch pages, and permanently purge underlying text and image data. |
| **PDF ↔ Word** | PDF → DOCX via `pdf2docx`. DOCX → PDF via `docx2pdf` on Windows (requires Microsoft Word; clean fallback error if unavailable). |
| **PDF ↔ Images** | Export all PDF pages to PNG/JPG in a ZIP, or bundle multiple JPG/PNG images into a single PDF. |
| **Protect / Unlock** | AES-256 encryption and decryption using PyMuPDF. |
| **Rotate & Watermark** | Rotate all pages by 90°/180°/270°, or add diagonal semi-transparent watermark text across all pages. |

## True Redaction vs. Naive Overlay Redaction

This project implements **true redaction**, not cosmetic masking:

- **Naive overlay redaction (unsafe):** Draws a black rectangle on top of content. The underlying text/images remain in the PDF and can often be copied, searched, or extracted.
- **True redaction (this app):** Uses PyMuPDF redaction annotations (`page.add_redact_annot`) and applies them with `page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_REMOVE)`. This **permanently removes** the underlying text and targeted image data from the page content before saving (with garbage collection/cleanup on save).

**Important:** Always verify redacted outputs for your compliance needs (e.g., confirm text cannot be selected/copied in the redacted regions). Redaction is applied to the regions you mark on the selected pages.

## Tech Stack

- **Backend:** FastAPI, Uvicorn, Jinja2
- **PDF & Imaging:** PyMuPDF (`fitz`), Pillow
- **Conversions:** `pdf2docx` (PDF → Word), `docx2pdf` (Word → PDF, Windows/MS Word)
- **Frontend:** Vanilla HTML/CSS/JS with HTML5 Canvas for redaction (Light Neo-Brutalism UI)

## Project Structure

```text
app/
  __init__.py
  main.py
  services/
    __init__.py
    pdf_core.py
    compressor.py
    redactor.py
    converters.py
  utils/
    __init__.py
    file_manager.py
static/
  css/
    brutalist.css
  js/
    studio.js
    redactor_canvas.js
templates/
  index.html
requirements.txt
README.md
```

## Windows Setup Instructions

### Prerequisites
- **Python 3.10+** (recommended) installed and available on `PATH`
- **Microsoft Word** (only required for **Word → PDF** conversion via `docx2pdf`; other features work without it)

### 1. Clone or download the project
Place the project folder on your local machine and open a terminal in the project root (the folder containing `app/`, `requirements.txt`, etc.).

### 2. Create and activate a virtual environment (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If script execution is blocked, you can use Command Prompt instead:
```bat
python -m venv .venv
.\.venv\Scripts\activate.bat
```

### 3. Install dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Run the application
```powershell
uvicorn app.main:app --reload
```

Then open your browser to: **http://127.0.0.1:8000**

> The app is intended for local use. Keep it bound to localhost for privacy.

## Usage Notes

- **Merge / Images → PDF:** Drag and drop multiple files and use the ↑ ↓ controls to reorder before processing.
- **Split ranges:** Use 1-indexed ranges such as `1-3, 5, 7-9`.
- **Compression:** Enter a target in KB. The app reports `original → final` size and whether the target was met. Very aggressive targets may reduce visual quality or text selectability (a rasterized fallback may be used as a best-effort step).
- **Redaction:** Upload a PDF, draw rectangles over sensitive areas (across any pages), then click **"Permanently Redact & Download"**. Redactions are applied to normalized coordinates and permanently remove underlying content.
- **Word → PDF:** Available on Windows with Microsoft Word installed. On systems without Word, the API returns a clean error message.

## API Endpoints

- `GET /` — Web UI
- `POST /api/merge`
- `POST /api/split`
- `POST /api/compress`
- `POST /api/redact/preview`
- `POST /api/redact/apply`
- `POST /api/convert/pdf-to-word`
- `POST /api/convert/word-to-pdf`
- `POST /api/convert/pdf-to-images`
- `POST /api/convert/images-to-pdf`
- `POST /api/rotate`
- `POST /api/protect`
- `POST /api/unlock`
- `POST /api/watermark`

All processing endpoints return downloadable files and schedule temporary workspace cleanup after the response.

## License

No license file is included by default. Add one if you plan to distribute this project.
