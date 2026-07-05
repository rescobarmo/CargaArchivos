import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from config import METADATA_FILE

_lock = threading.Lock()


def _load() -> list[dict]:
    if not METADATA_FILE.exists():
        return []
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: list[dict]) -> None:
    tmp = METADATA_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(METADATA_FILE)


def add_entry(entry: dict) -> None:
    with _lock:
        data = _load()
        data.append(entry)
        _save(data)


def list_entries() -> list[dict]:
    with _lock:
        return _load()


def get_entry(file_id: str) -> dict | None:
    with _lock:
        for e in _load():
            if e["id"] == file_id:
                return e
    return None


def delete_entry(file_id: str) -> dict | None:
    with _lock:
        data = _load()
        for i, e in enumerate(data):
            if e["id"] == file_id:
                removed = data.pop(i)
                _save(data)
                return removed
    return None


def build_entry(
    file_id: str,
    original_name: str,
    stored_name: str,
    mime: str,
    size: int,
    category: str,
    title: str = "",
    description: str = "",
    tags: list[str] | None = None,
) -> dict:
    return {
        "id": file_id,
        "original_name": original_name,
        "stored_name": stored_name,
        "mime_type": mime,
        "size_bytes": size,
        "category": category,
        "title": title,
        "description": description,
        "tags": tags or [],
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
