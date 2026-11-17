import os
import shutil
import uuid
from pathlib import Path
from typing import Iterable

from fastapi import BackgroundTasks

BASE_TEMP_DIR = Path(__file__).resolve().parents[2] / ".temp_workspace"
BASE_TEMP_DIR.mkdir(parents=True, exist_ok=True)


def create_workspace() -> Path:
    """Create and return an isolated per-request temporary workspace."""
    workspace = BASE_TEMP_DIR / uuid.uuid4().hex
    workspace.mkdir(parents=True, exist_ok=False)
    return workspace


def cleanup_workspace(workspace: Path) -> None:
    """Remove a temporary workspace and all contained files."""
    try:
        if workspace.exists():
            shutil.rmtree(workspace, ignore_errors=True)
    except Exception:
        # Best-effort cleanup; do not raise during background task execution.
        pass


def schedule_cleanup(background_tasks: BackgroundTasks, workspace: Path) -> None:
    """Register workspace cleanup as a FastAPI background task."""
    background_tasks.add_task(cleanup_workspace, workspace)


def save_upload(upload, destination: Path) -> Path:
    """Save a FastAPI UploadFile/Starlette UploadFile to destination."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as f:
        shutil.copyfileobj(upload.file, f)
    try:
        upload.file.close()
    except Exception:
        pass
    return destination


def save_uploads(uploads: Iterable, workspace: Path, prefix: str = "file") -> list[Path]:
    """Save multiple uploads into workspace, preserving order."""
    paths: list[Path] = []
    for idx, upload in enumerate(uploads):
        original = Path(getattr(upload, "filename", None) or f"{prefix}_{idx}")
        safe_name = original.name.replace("/", "_").replace("\\", "_") or f"{prefix}_{idx}"
        dest = workspace / f"{idx:03d}_{safe_name}"
        paths.append(save_upload(upload, dest))
    return paths
