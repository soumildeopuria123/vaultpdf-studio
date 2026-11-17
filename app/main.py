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
