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
