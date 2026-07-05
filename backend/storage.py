import re
from pathlib import Path

from config import UPLOAD_IMAGEN, UPLOAD_TEXTO, UPLOAD_XLS, THUMBNAILS_DIR


def get_upload_dir(category: str) -> Path:
    if category == "image":
        return UPLOAD_IMAGEN
    elif category in ("xls", "spreadsheet"):
        return UPLOAD_XLS
    else:
        return UPLOAD_TEXTO


def generate_unique_filename(original: str, ext: str, upload_dir: Path) -> str:
    safe_stem = re.sub(r'[^\w\-.]', '_', original)[:80]
    if not safe_stem:
        safe_stem = "archivo"
    return f"{safe_stem}{ext}"


def get_upload_path(filename: str, category: str) -> Path:
    return get_upload_dir(category) / filename


def get_thumbnail_path(filename: str) -> Path:
    return THUMBNAILS_DIR / filename
