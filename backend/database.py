import re
import pymysql
from pymysql.cursors import DictCursor

from config import MYSQL_CONFIG


def _connect(use_db=True):
    cfg = {k: v for k, v in MYSQL_CONFIG.items()}
    if not use_db:
        cfg.pop("database", None)
    return pymysql.connect(**cfg, cursorclass=DictCursor)


def ensure_database():
    conn = _connect(use_db=False)
    try:
        db_name = MYSQL_CONFIG["database"]
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
    finally:
        conn.close()


def _sanitize_table_name(name: str) -> str:
    safe = re.sub(r"[^\w]", "_", name).strip("_").lower()
    if not safe or safe[0].isdigit():
        safe = "tbl_" + safe
    return safe[:60]


def _sanitize_column_name(name: str) -> str:
    safe = re.sub(r"[^\w]", "_", str(name)).strip("_").lower()
    if not safe:
        safe = "columna"
    if safe[0].isdigit():
        safe = "col_" + safe
    return safe[:60]


def _infer_mysql_type(value) -> str:
    if value is None:
        return "TEXT"
    if isinstance(value, bool):
        return "TINYINT(1)"
    if isinstance(value, int):
        return "BIGINT"
    if isinstance(value, float):
        return "DOUBLE"
    s = str(value)
    if len(s) <= 255:
        return "VARCHAR(255)"
    return "TEXT"


def import_excel_to_mysql(file_path, table_name: str) -> dict:
    ext = str(file_path).lower()
    
    if ext.endswith('.xls'):
        return _import_xls(file_path, table_name)
    else:
        return _import_xlsx(file_path, table_name)


def _import_xls(file_path, table_name: str) -> dict:
    import xlrd
    
    wb = xlrd.open_workbook(file_path)
    ws = wb.sheet_by_index(0)
    
    if ws.nrows == 0:
        return {"table": table_name, "rows": 0, "columns": 0, "error": "Archivo vacio"}
    
    raw_headers = [ws.cell_value(0, col) for col in range(ws.ncols)]
    
    headers = []
    seen = {}
    for h in raw_headers:
        col = _sanitize_column_name(h if h else "columna")
        if col in seen:
            seen[col] += 1
            col = f"{col}_{seen[col]}"
        else:
            seen[col] = 0
        headers.append(col)
    
    if not headers:
        return {"table": table_name, "rows": 0, "columns": 0, "error": "Sin columnas"}
    
    data_rows = []
    for row_idx in range(1, ws.nrows):
        row = [ws.cell_value(row_idx, col) for col in range(ws.ncols)]
        data_rows.append(row)
    
    col_types = ["TEXT"] * len(headers)
    sample = data_rows[:50]
    for row in sample:
        for i, val in enumerate(row):
            if i >= len(headers):
                break
            if col_types[i] == "TEXT":
                inferred = _infer_mysql_type(val)
                if inferred != "TEXT":
                    col_types[i] = inferred
    
    safe_table = _sanitize_table_name(table_name)
    
    ensure_database()
    conn = _connect()
    inserted = 0
    try:
        with conn.cursor() as cur:
            col_defs = ", ".join(
                f"`{h}` {col_types[i]}" for i, h in enumerate(headers)
            )
            cur.execute(f"DROP TABLE IF EXISTS `{safe_table}`")
            cur.execute(
                f"CREATE TABLE `{safe_table}` ({col_defs}) "
                f"ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
            )
            
            placeholders = ", ".join(["%s"] * len(headers))
            col_names = ", ".join(f"`{h}`" for h in headers)
            insert_sql = f"INSERT INTO `{safe_table}` ({col_names}) VALUES ({placeholders})"
            
            for row in data_rows:
                values = []
                for i, val in enumerate(row):
                    if i >= len(headers):
                        break
                    if isinstance(val, bool):
                        values.append(int(val))
                    elif val is None or val == "":
                        values.append(None)
                    else:
                        values.append(val)
                while len(values) < len(headers):
                    values.append(None)
                cur.execute(insert_sql, values)
                inserted += 1
        
        conn.commit()
    finally:
        conn.close()
    
    return {
        "table": safe_table,
        "rows": inserted,
        "columns": len(headers),
    }


def _import_xlsx(file_path, table_name: str) -> dict:
    from openpyxl import load_workbook

    wb = load_workbook(file_path, read_only=True, data_only=True)
    ws = wb.active

    rows_iter = ws.iter_rows(values_only=True)

    raw_headers = next(rows_iter, None)
    if raw_headers is None:
        wb.close()
        return {"table": table_name, "rows": 0, "columns": 0, "error": "Archivo vacio"}

    headers = []
    seen = {}
    for h in raw_headers:
        col = _sanitize_column_name(h if h is not None else "columna")
        if col in seen:
            seen[col] += 1
            col = f"{col}_{seen[col]}"
        else:
            seen[col] = 0
        headers.append(col)

    if not headers:
        wb.close()
        return {"table": table_name, "rows": 0, "columns": 0, "error": "Sin columnas"}

    data_rows = list(rows_iter)
    wb.close()

    col_types = ["TEXT"] * len(headers)
    sample = data_rows[:50]
    for row in sample:
        for i, val in enumerate(row):
            if i >= len(headers):
                break
            if col_types[i] == "TEXT":
                inferred = _infer_mysql_type(val)
                if inferred != "TEXT":
                    col_types[i] = inferred

    safe_table = _sanitize_table_name(table_name)

    ensure_database()
    conn = _connect()
    inserted = 0
    try:
        with conn.cursor() as cur:
            col_defs = ", ".join(
                f"`{h}` {col_types[i]}" for i, h in enumerate(headers)
            )
            cur.execute(f"DROP TABLE IF EXISTS `{safe_table}`")
            cur.execute(
                f"CREATE TABLE `{safe_table}` ({col_defs}) "
                f"ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
            )

            placeholders = ", ".join(["%s"] * len(headers))
            col_names = ", ".join(f"`{h}`" for h in headers)
            insert_sql = f"INSERT INTO `{safe_table}` ({col_names}) VALUES ({placeholders})"

            for row in data_rows:
                values = []
                for i, val in enumerate(row):
                    if i >= len(headers):
                        break
                    if isinstance(val, bool):
                        values.append(int(val))
                    elif val is None:
                        values.append(None)
                    else:
                        values.append(val)
                while len(values) < len(headers):
                    values.append(None)
                cur.execute(insert_sql, values)
                inserted += 1

        conn.commit()
    finally:
        conn.close()

    return {
        "table": safe_table,
        "rows": inserted,
        "columns": len(headers),
    }
