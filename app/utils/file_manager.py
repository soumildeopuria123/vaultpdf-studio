import os
import shutil
import uuid
from pathlib import Path
from typing import Iterable

from fastapi import BackgroundTasks

BASE_TEMP_DIR = Path(__file__).resolve().parents[2] / ".temp_workspace"
BASE_TEMP_DIR.mkdir(parents=True, exist_ok=True)
