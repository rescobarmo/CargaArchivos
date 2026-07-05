import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

from config import ALLOWED_EXTENSIONS, BASE_DIR
from metadata import add_entry, build_entry, delete_entry, get_entry, list_entries
import storage
from storage import get_thumbnail_path, get_upload_path
from validators import FileValidationError, validate_file

app = FastAPI(title="CargaArchivos API", version="1.0.0")

FRONTEND_DIR = BASE_DIR / "frontend"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _categorize(ext: str) -> str:
    if ext in ALLOWED_EXTENSIONS["image"]:
        return "image"
    elif ext in (".xls", ".xlsx", ".csv"):
        return "xls"
    else:
        return "texto"


def _make_thumbnail(stored_name: str, mime: str, category: str) -> None:
    if not mime.startswith("image/"):
        return
    src = get_upload_path(stored_name, category)
    dst = get_thumbnail_path(stored_name)
    try:
        with Image.open(src) as img:
            img.thumbnail((300, 300))
            if img.mode in ("RGBA", "P"):
                img.save(dst, "PNG")
            else:
                img.save(dst, "JPEG", quality=80)
    except Exception:
        pass


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    title: str = Form(""),
    description: str = Form(""),
    tags: str = Form(""),
):
    try:
        mime, ext = await validate_file(file)
    except FileValidationError as e:
        raise HTTPException(status_code=400, detail=e.detail)

    file_id = uuid.uuid4().hex
    base_name = title.strip() if title.strip() else Path(file.filename or "file").stem
    category = _categorize(ext)
    upload_dir = storage.get_upload_dir(category)
    stored_name = storage.generate_unique_filename(base_name, ext, upload_dir)
    dest = get_upload_path(stored_name, category)

    content = await file.read()
    dest.write_bytes(content)

    _make_thumbnail(stored_name, mime, category)

    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    entry = build_entry(
        file_id=file_id,
        original_name=file.filename or "unknown",
        stored_name=stored_name,
        mime=mime,
        size=len(content),
        category=category,
        title=title,
        description=description,
        tags=tag_list,
    )
    add_entry(entry)
    return {"message": "Archivo subido correctamente", "file": entry}


@app.get("/api/files")
async def get_files(category: str | None = None):
    files = list_entries()
    if category:
        files = [f for f in files if f.get("category") == category]
    return {"files": files, "total": len(files)}


@app.get("/api/files/{file_id}")
async def get_file(file_id: str):
    entry = get_entry(file_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return entry


@app.get("/api/files/{file_id}/download")
async def download_file(file_id: str):
    entry = get_entry(file_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    path = get_upload_path(entry["stored_name"], entry["category"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Archivo fisico no encontrado")
    return FileResponse(path, filename=entry["original_name"], media_type=entry["mime_type"])


@app.get("/api/files/{file_id}/thumbnail")
async def get_thumbnail(file_id: str):
    entry = get_entry(file_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    thumb = get_thumbnail_path(entry["stored_name"])
    if not thumb.exists():
        raise HTTPException(status_code=404, detail="Thumbnail no disponible")
    return FileResponse(thumb, media_type="image/jpeg")


@app.delete("/api/files/{file_id}")
async def remove_file(file_id: str):
    entry = delete_entry(file_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    path = get_upload_path(entry["stored_name"], entry["category"])
    thumb = get_thumbnail_path(entry["stored_name"])
    if path.exists():
        path.unlink()
    if thumb.exists():
        thumb.unlink()
    return {"message": "Archivo eliminado"}


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
