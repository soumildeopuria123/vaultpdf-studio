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
