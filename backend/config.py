import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "backend" / "uploads"
DATA_DIR = BASE_DIR / "data"
METADATA_FILE = DATA_DIR / "metadata.json"
DB_CONFIG_FILE = DATA_DIR / "db_config.json"

UPLOAD_IMAGEN = UPLOAD_DIR / "imagen"
UPLOAD_TEXTO = UPLOAD_DIR / "texto"
UPLOAD_XLS = UPLOAD_DIR / "xls"
THUMBNAILS_DIR = UPLOAD_DIR / "thumbnails"

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

ALLOWED_EXTENSIONS: dict[str, list[str]] = {
    "image": [".jpg", ".jpeg", ".png", ".gif", ".webp"],
    "document": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt", ".csv"],
}

ALLOWED_MIME_TYPES: dict[str, list[str]] = {
    "image": ["image/jpeg", "image/png", "image/gif", "image/webp"],
    "document": [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/plain",
        "text/csv",
    ],
}

ALL_ALLOWED_MIMES = [m for group in ALLOWED_MIME_TYPES.values() for m in group]
ALL_ALLOWED_EXTENSIONS = [e for group in ALLOWED_EXTENSIONS.values() for e in group]

DEFAULT_MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "carga_archivos",
    "charset": "utf8mb4",
}

def load_mysql_config():
    # Primero intentar variables de entorno (para Docker)
    env_config = {
        "host": os.getenv("MYSQL_HOST"),
        "port": int(os.getenv("MYSQL_PORT", 3306)),
        "user": os.getenv("MYSQL_USER"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "carga_archivos"),
        "charset": "utf8mb4",
    }
    
    # Si hay variables de entorno configuradas, usarlas
    if env_config["host"]:
        return env_config
    
    # Si no, usar archivo de configuración
    if DB_CONFIG_FILE.exists():
        try:
            with open(DB_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_MYSQL_CONFIG.copy()

MYSQL_CONFIG = load_mysql_config()

for d in (UPLOAD_IMAGEN, UPLOAD_TEXTO, UPLOAD_XLS, THUMBNAILS_DIR):
    d.mkdir(parents=True, exist_ok=True)
