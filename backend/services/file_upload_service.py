"""Shared safe upload helpers for bounded local file handling."""


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
