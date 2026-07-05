import filetype
from fastapi import UploadFile

from config import ALL_ALLOWED_EXTENSIONS, ALL_ALLOWED_MIMES, MAX_FILE_SIZE_BYTES


class FileValidationError(Exception):
    def __init__(self, detail: str):
        self.detail = detail


async def validate_file(file: UploadFile) -> tuple[str, str]:
    content = await file.read()
    await file.seek(0)

    if len(content) > MAX_FILE_SIZE_BYTES:
        raise FileValidationError(
            f"El archivo supera el tamano maximo de {MAX_FILE_SIZE_BYTES // (1024*1024)}MB"
        )

    if len(content) == 0:
        raise FileValidationError("El archivo esta vacio")

    ext = _get_extension(file.filename)
    if ext not in ALL_ALLOWED_EXTENSIONS:
        raise FileValidationError(
            f"Extension '{ext}' no permitida. Permitidas: {ALL_ALLOWED_EXTENSIONS}"
        )

    real_mime = _detect_real_mime(content)
    if real_mime not in ALL_ALLOWED_MIMES:
        raise FileValidationError(
            f"Tipo MIME real '{real_mime}' no permitido. El archivo podria ser malicioso."
        )

    declared = file.content_type or ""
    if declared and declared != real_mime:
        if not _mime_compatible(declared, real_mime):
            raise FileValidationError(
                f"El MIME declarado '{declared}' no coincide con el real '{real_mime}'"
            )

    return real_mime, ext


def _get_extension(filename: str | None) -> str:
    if not filename or "." not in filename:
        raise FileValidationError("Nombre de archivo invalido o sin extension")
    return "." + filename.rsplit(".", 1)[-1].lower()


def _detect_real_mime(content: bytes) -> str:
    kind = filetype.guess(content)
    if kind is None:
        return "text/plain"
    return kind.mime


def _mime_compatible(declared: str, real: str) -> bool:
    top_decl = declared.split("/")[0]
    top_real = real.split("/")[0]
    return top_decl == top_real
