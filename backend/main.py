import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

from config import ALLOWED_EXTENSIONS, BASE_DIR, UPLOAD_IMAGEN, UPLOAD_TEXTO, UPLOAD_XLS, DEFAULT_MYSQL_CONFIG, DB_CONFIG_FILE, load_mysql_config, MYSQL_CONFIG
from database import import_excel_to_mysql
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

app.mount("/uploads/image", StaticFiles(directory=UPLOAD_IMAGEN), name="uploads_imagen")
app.mount("/uploads/texto", StaticFiles(directory=UPLOAD_TEXTO), name="uploads_texto")
app.mount("/uploads/xls", StaticFiles(directory=UPLOAD_XLS), name="uploads_xls")


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

    result = {"message": "Archivo subido correctamente", "file": entry}

    if category == "xls":
        try:
            table_base = title.strip() if title.strip() else base_name
            mysql_result = import_excel_to_mysql(dest, table_base)
            result["mysql"] = mysql_result
        except Exception as e:
            result["mysql"] = {"error": str(e)}

    return result


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


@app.get("/api/db-config")
async def get_db_config():
    config = load_mysql_config()
    safe = {k: v for k, v in config.items() if k != "password"}
    safe["password_set"] = bool(config.get("password"))
    return {"config": safe}


@app.post("/api/db-config")
async def save_db_config(
    host: str = Form("localhost"),
    port: int = Form(3306),
    user: str = Form("root"),
    password: str = Form(""),
    database: str = Form("carga_archivos"),
):
    import json
    new_config = {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
        "charset": "utf8mb4",
    }
    DB_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DB_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(new_config, f, ensure_ascii=False, indent=2)
    MYSQL_CONFIG.update(new_config)
    return {"message": "Configuracion guardada"}


@app.post("/api/db-config/test")
async def test_db_config(
    host: str = Form("localhost"),
    port: int = Form(3306),
    user: str = Form("root"),
    password: str = Form(""),
    database: str = Form("carga_archivos"),
):
    import pymysql
    try:
        conn = pymysql.connect(
            host=host, port=port, user=user, password=password,
            charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
        )
        try:
            with conn.cursor() as cur:
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            conn.commit()
        finally:
            conn.close()
        return {"success": True, "message": "Conexion exitosa"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/api/send-list")
async def send_list(
    number: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    button_text: str = Form(...),
    footer_text: str = Form(""),
    sections_json: str = Form(...),
):
    import json
    import httpx
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"Received send-list request for number: {number}")
    
    try:
        sections = json.loads(sections_json)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"JSON de secciones invalido: {str(e)}")
    
    payload = {
        "number": number,
        "title": title,
        "description": description,
        "buttonText": button_text,
        "footerText": footer_text,
        "sections": sections
    }
    
    headers = {
        "Content-Type": "application/json",
        "apikey": "41CF2568B6F0-4101-91B6-710026FB5B13"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://rsr-evolution-api.jdseuk.easypanel.host/message/sendList/bluepay",
                json=payload,
                headers=headers,
                timeout=30.0
            )
            
            logger.info(f"Evolution API response: {response.status_code}")
            
            if response.status_code == 200:
                return {"success": True, "message": "Lista enviada correctamente", "data": response.json()}
            else:
                return {"success": False, "message": f"Error de Evolution API: {response.text}"}
    except Exception as e:
        logger.error(f"Error connecting to Evolution API: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al conectar con Evolution API: {str(e)}")


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
