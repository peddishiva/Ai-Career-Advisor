"""Shared safe upload helpers for bounded local file handling."""

import re
import zipfile
from pathlib import Path


MAX_DOCUMENT_UNCOMPRESSED_BYTES = 20 * 1024 * 1024
MAX_DOCUMENT_ZIP_MEMBERS = 500


class InvalidUploadContentError(ValueError):
    """Raised when a document's bytes do not match its declared extension."""


class UploadTooLargeError(ValueError):
    """Raised when a streamed upload exceeds its configured byte limit."""


def uploaded_file_size(file) -> int | None:
    """Return a best-effort size without consuming the upload stream."""
    size = getattr(file, "size", None)
    if isinstance(size, int) and size >= 0:
        return size

    try:
        current_position = file.file.tell()
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(current_position)
        return size
    except (AttributeError, OSError):
        return None


def copy_upload_with_limit(file, destination, max_bytes: int, chunk_size: int) -> int:
    """Copy an upload in bounded chunks and return the number of bytes written."""
    try:
        file.file.seek(0)
    except (AttributeError, OSError):
        pass

    bytes_written = 0
    while True:
        chunk = file.file.read(chunk_size)
        if not chunk:
            break
        bytes_written += len(chunk)
        if bytes_written > max_bytes:
            raise UploadTooLargeError
        destination.write(chunk)
    return bytes_written


def ensure_text_size(text: str, max_bytes: int) -> None:
    """Apply the same byte limit to pasted text as to uploaded documents."""
    if len(text.encode("utf-8")) > max_bytes:
        raise UploadTooLargeError


def sanitize_upload_filename(filename: str, max_length: int = 180) -> str:
    """Return a display-only basename without path or control characters."""
    normalized = str(filename or "").replace("\\", "/")
    basename = Path(normalized).name
    basename = "".join(character for character in basename if character.isprintable() and character not in {"/", "\\"})
    basename = re.sub(r"\s+", " ", basename).strip()
    return basename[:max_length]


def validate_document_content(file_path: Path, suffix: str) -> None:
    """Validate lightweight file signatures and bounded archive structure."""
    suffix = suffix.casefold()
    try:
        with file_path.open("rb") as handle:
            header = handle.read(8)
    except OSError as exc:
        raise InvalidUploadContentError from exc

    if suffix == ".pdf":
        if not header.startswith(b"%PDF-"):
            raise InvalidUploadContentError("PDF signature is missing")
        return

    if suffix == ".doc":
        if header != b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
            raise InvalidUploadContentError("legacy document signature is missing")
        return

    if suffix != ".docx" or header[:4] != b"PK\x03\x04":
        raise InvalidUploadContentError("document signature does not match its extension")

    try:
        with zipfile.ZipFile(file_path) as archive:
            members = archive.infolist()
            if len(members) > MAX_DOCUMENT_ZIP_MEMBERS:
                raise InvalidUploadContentError("document contains too many archive members")
            total_uncompressed = 0
            names = set()
            for member in members:
                name = member.filename.replace("\\", "/")
                parts = Path(name).parts
                if name.startswith("/") or ".." in parts or name in names:
                    raise InvalidUploadContentError("document contains an unsafe archive path")
                names.add(name)
                total_uncompressed += member.file_size
                if total_uncompressed > MAX_DOCUMENT_UNCOMPRESSED_BYTES:
                    raise InvalidUploadContentError("document expands beyond the safe limit")
            if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                raise InvalidUploadContentError("DOCX package is incomplete")
            if any(name.casefold().endswith("/vbaproject.bin") for name in names):
                raise InvalidUploadContentError("macro-enabled documents are not accepted")
            if archive.testzip() is not None:
                raise InvalidUploadContentError("document archive is corrupt")
    except InvalidUploadContentError:
        raise
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        raise InvalidUploadContentError("document archive is invalid") from exc
