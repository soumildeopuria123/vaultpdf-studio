import json
import uuid
from pathlib import Path
from typing import List

import fitz
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.services import compressor, converters, pdf_core, redactor
from app.utils.file_manager import create_workspace, save_upload, save_uploads, schedule_cleanup

BASE_DIR = Path(__file__).resolve().parents[1]

app = FastAPI(title="Local PDF Utility Studio")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Return clean JSON errors for API routes; let HTML routes behave normally if needed.
    if request.url.path.startswith("/api/"):
        detail = str(exc) or "An unexpected error occurred."
        status = 400 if isinstance(exc, ValueError) else 500
        if isinstance(exc, HTTPException):
            status = exc.status_code
            detail = exc.detail
        return JSONResponse(status_code=status, content={"error": detail})
    raise exc


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.post("/api/merge")
async def api_merge(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    workspace = create_workspace()
    try:
        if not files or len(files) < 2:
            raise ValueError("Please provide at least two PDF files to merge.")
        paths = save_uploads(files, workspace)
        output = workspace / "merged.pdf"
        pdf_core.merge_pdfs(paths, output)
        schedule_cleanup(background_tasks, workspace)
        return FileResponse(
            path=str(output),
            filename="merged.pdf",
            media_type="application/pdf",
            background=background_tasks,
        )
    except Exception:
        schedule_cleanup(background_tasks, workspace)
        raise


@app.post("/api/split")
async def api_split(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    ranges: str = Form(...),
):
    workspace = create_workspace()
    try:
        input_path = save_upload(file, workspace / (file.filename or "input.pdf"))
        output = workspace / "split_pages.zip"
        pdf_core.split_pdf(input_path, ranges, output)
        schedule_cleanup(background_tasks, workspace)
        return FileResponse(
            path=str(output),
            filename="split_pages.zip",
            media_type="application/zip",
            background=background_tasks,
        )
    except Exception:
        schedule_cleanup(background_tasks, workspace)
        raise


@app.post("/api/compress")
async def api_compress(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    target_kb: float = Form(...),
):
    workspace = create_workspace()
    try:
        stem = Path(file.filename or "document").stem
        input_path = save_upload(file, workspace / (file.filename or "input.pdf"))
        output = workspace / f"{stem}_compressed.pdf"
        original_size, final_size, target_met = compressor.compress_to_target(
            input_path, output, target_kb
        )
        headers = {
            "X-Original-Size": str(original_size),
            "X-Final-Size": str(final_size),
            "X-Target-Met": "true" if target_met else "false",
            "Access-Control-Expose-Headers": "X-Original-Size, X-Final-Size, X-Target-Met",
        }
        schedule_cleanup(background_tasks, workspace)
        return FileResponse(
            path=str(output),
            filename=f"{stem}_compressed.pdf",
            media_type="application/pdf",
            headers=headers,
            background=background_tasks,
        )
    except Exception:
        schedule_cleanup(background_tasks, workspace)
        raise


@app.post("/api/redact/preview")
async def api_redact_preview(file: UploadFile = File(...), page: int = Form(0)):
    workspace = create_workspace()
    try:
        input_path = save_upload(file, workspace / (file.filename or "input.pdf"))
        with fitz.open(input_path) as doc:
            page_count = doc.page_count
            if page < 0 or page >= page_count:
                raise ValueError(f"Page out of range. Document has {page_count} pages.")
        png_bytes = redactor.render_page_preview(input_path, page)
        # cleanup immediately; preview is stateless per request
        from app.utils.file_manager import cleanup_workspace

        cleanup_workspace(workspace)
        return HTMLResponse(content=png_bytes, media_type="image/png")
    except Exception:
        from app.utils.file_manager import cleanup_workspace

        cleanup_workspace(workspace)
        raise


@app.post("/api/redact/apply")
async def api_redact_apply(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    boxes: str = Form(...),
):
    workspace = create_workspace()
    try:
        try:
            boxes_payload = json.loads(boxes)
        except json.JSONDecodeError:
            raise ValueError("Invalid redaction boxes payload (must be JSON).")
        stem = Path(file.filename or "document").stem
        input_path = save_upload(file, workspace / (file.filename or "input.pdf"))
        output = workspace / f"{stem}_redacted.pdf"
        redactor.redact_regions(input_path, output, boxes_payload)
        schedule_cleanup(background_tasks, workspace)
        return FileResponse(
            path=str(output),
            filename=f"{stem}_redacted.pdf",
            media_type="application/pdf",
            background=background_tasks,
        )
    except Exception:
        schedule_cleanup(background_tasks, workspace)
        raise


@app.post("/api/convert/pdf-to-word")
async def api_pdf_to_word(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    workspace = create_workspace()
    try:
        stem = Path(file.filename or "document").stem
        input_path = save_upload(file, workspace / (file.filename or "input.pdf"))
        output = workspace / f"{stem}.docx"
        converters.pdf_to_word(input_path, output)
        schedule_cleanup(background_tasks, workspace)
        return FileResponse(
            path=str(output),
            filename=f"{stem}.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            background=background_tasks,
        )
    except Exception:
        schedule_cleanup(background_tasks, workspace)
        raise


@app.post("/api/convert/word-to-pdf")
async def api_word_to_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    workspace = create_workspace()
    try:
        stem = Path(file.filename or "document").stem
        input_path = save_upload(file, workspace / (file.filename or "input.docx"))
        output = workspace / f"{stem}.pdf"
        converters.word_to_pdf(input_path, output)
        schedule_cleanup(background_tasks, workspace)
        return FileResponse(
            path=str(output),
            filename=f"{stem}.pdf",
            media_type="application/pdf",
            background=background_tasks,
        )
    except Exception:
        schedule_cleanup(background_tasks, workspace)
        raise


@app.post("/api/convert/pdf-to-images")
async def api_pdf_to_images(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    fmt: str = Form("png"),
    dpi: int = Form(150),
):
    workspace = create_workspace()
    try:
