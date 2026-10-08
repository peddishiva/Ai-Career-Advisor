"""Private object-storage abstraction with safe local and Supabase adapters."""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path, PurePosixPath
import secrets
from typing import BinaryIO, Any
from urllib.parse import quote

import requests

from config.storage_config import StorageConfig, load_storage_config


class StorageError(RuntimeError):
    """Safe storage failure without provider internals."""


class InvalidStoragePath(StorageError):
    pass


@dataclass(frozen=True)
class StorageObjectMetadata:
    owner_id: str
    object_name: str
    storage_path: str
    size_bytes: int
    content_type: str | None
    etag: str


def _read_bounded(content: bytes | bytearray | BinaryIO, max_bytes: int) -> bytes:
    if isinstance(content, (bytes, bytearray)):
        data = bytes(content)
        if len(data) > max_bytes:
            raise StorageError("storage object exceeds the configured size limit")
        return data
    if not hasattr(content, "read"):
        raise StorageError("unsupported storage content")
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = content.read(min(1024 * 1024, max_bytes + 1 - total))
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise StorageError("storage object exceeds the configured size limit")
        chunks.append(chunk)
    return b"".join(chunks)


def _safe_path(owner_id: str, object_name: str) -> tuple[str, str]:
    owner = str(owner_id or "").strip()
    if not owner or owner in {".", ".."} or any(separator in owner for separator in ("/", "\\")):
        raise InvalidStoragePath("invalid storage owner scope")
    raw_name = str(object_name or "").strip().replace("\\", "/")
    path = PurePosixPath(raw_name)
    if not raw_name or path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise InvalidStoragePath("invalid storage object path")
    safe_name = "/".join(path.parts)
    return f"users/{owner}/{safe_name}", safe_name


class StorageService:
    def upload(
        self,
        owner_id: str,
        object_name: str,
        content: bytes | bytearray | BinaryIO,
        content_type: str | None = None,
    ) -> StorageObjectMetadata:
        raise NotImplementedError

    def download_signed(self, owner_id: str, object_name: str, expires_in: int = 300) -> str:
        raise NotImplementedError

    def delete(self, owner_id: str, object_name: str) -> None:
        raise NotImplementedError

    def exists(self, owner_id: str, object_name: str) -> bool:
        raise NotImplementedError

    def metadata(self, owner_id: str, object_name: str) -> StorageObjectMetadata | None:
        raise NotImplementedError


class LocalStorageAdapter(StorageService):
    """Private local adapter for development and interface tests."""

    def __init__(self, config: StorageConfig | None = None, signing_key: bytes | None = None) -> None:
        self.config = config or load_storage_config()
        self.root = self.config.local_root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._signing_key = signing_key or secrets.token_bytes(32)

    def _path(self, owner_id: str, object_name: str) -> tuple[Path, str]:
        storage_path, _ = _safe_path(owner_id, object_name)
        base = self.root.resolve()
        candidate = (base / storage_path).resolve()
        if candidate.parent != base and base not in candidate.parents:
            raise InvalidStoragePath("storage path escaped the configured root")
        return candidate, storage_path

    def upload(self, owner_id: str, object_name: str, content: bytes | bytearray | BinaryIO, content_type: str | None = None) -> StorageObjectMetadata:
        data = _read_bounded(content, self.config.max_object_bytes)
        path, storage_path = self._path(owner_id, object_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        if content_type:
            path.with_suffix(path.suffix + ".meta").write_text(json.dumps({"content_type": content_type}), encoding="utf-8")
        return StorageObjectMetadata(owner_id, object_name, storage_path, len(data), content_type, hashlib.sha256(data).hexdigest())

    def download_signed(self, owner_id: str, object_name: str, expires_in: int = 300) -> str:
        _, storage_path = self._path(owner_id, object_name)
        if not self.exists(owner_id, object_name):
            raise StorageError("storage object not found")
        expires_at = int(datetime.now(timezone.utc).timestamp()) + max(1, min(expires_in, 3600))
        payload = f"{storage_path}:{expires_at}".encode("utf-8")
        signature = hmac.new(self._signing_key, payload, hashlib.sha256).hexdigest()
        return f"local://{storage_path}?expires={expires_at}&signature={signature}"

    def delete(self, owner_id: str, object_name: str) -> None:
        path, _ = self._path(owner_id, object_name)
        if path.exists():
            path.unlink()
        metadata_path = path.with_suffix(path.suffix + ".meta")
        if metadata_path.exists():
            metadata_path.unlink()

    def exists(self, owner_id: str, object_name: str) -> bool:
        path, _ = self._path(owner_id, object_name)
        return path.is_file()

    def metadata(self, owner_id: str, object_name: str) -> StorageObjectMetadata | None:
        path, storage_path = self._path(owner_id, object_name)
        if not path.is_file():
            return None
        content_type = None
        metadata_path = path.with_suffix(path.suffix + ".meta")
        if metadata_path.exists():
            try:
                content_type = json.loads(metadata_path.read_text(encoding="utf-8")).get("content_type")
            except (OSError, ValueError, TypeError):
                content_type = None
        data = path.read_bytes()
        return StorageObjectMetadata(owner_id, object_name, storage_path, len(data), content_type, hashlib.sha256(data).hexdigest())


class SupabaseStorageAdapter(StorageService):
    """Private Supabase Storage adapter using a backend-only service key."""

    def __init__(self, config: StorageConfig | None = None, http_session: requests.Session | None = None) -> None:
        self.config = config or load_storage_config()
        if not self.config.supabase_url or not self.config.supabase_service_role_key:
            raise StorageError("Supabase Storage is not configured")
        self.session = http_session or requests.Session()

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        url = f"{self.config.supabase_url}/storage/v1/{path}"
        headers = kwargs.pop("headers", {})
        headers.update({
            "Authorization": f"Bearer {self.config.supabase_service_role_key}",
            "apikey": self.config.supabase_service_role_key,
        })
        try:
            response = self.session.request(method, url, headers=headers, timeout=10, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            raise StorageError("private storage operation failed") from exc

    def _object_path(self, owner_id: str, object_name: str) -> tuple[str, str]:
        return _safe_path(owner_id, object_name)

    def upload(self, owner_id: str, object_name: str, content: bytes | bytearray | BinaryIO, content_type: str | None = None) -> StorageObjectMetadata:
        data = _read_bounded(content, self.config.max_object_bytes)
        storage_path, _ = self._object_path(owner_id, object_name)
        path = f"object/{quote(self.config.supabase_bucket, safe='')}/{quote(storage_path, safe='/')}"
        self._request("POST", path, data=data, headers={"Content-Type": content_type or "application/octet-stream", "x-upsert": "false"})
        return StorageObjectMetadata(owner_id, object_name, storage_path, len(data), content_type, hashlib.sha256(data).hexdigest())

    def download_signed(self, owner_id: str, object_name: str, expires_in: int = 300) -> str:
        storage_path, _ = self._object_path(owner_id, object_name)
        path = f"object/sign/{quote(self.config.supabase_bucket, safe='')}/{quote(storage_path, safe='/')}"
        response = self._request("POST", path, json={"expiresIn": max(1, min(expires_in, 3600))})
        payload = response.json()
        signed = payload.get("signedURL") or payload.get("signedUrl")
        if not signed:
            raise StorageError("private storage did not return a signed URL")
        return signed if str(signed).startswith("http") else f"{self.config.supabase_url}/storage/v1{signed}"

    def delete(self, owner_id: str, object_name: str) -> None:
        storage_path, _ = self._object_path(owner_id, object_name)
        path = f"object/{quote(self.config.supabase_bucket, safe='')}"
        self._request("DELETE", path, json={"prefixes": [storage_path]})

    def exists(self, owner_id: str, object_name: str) -> bool:
        return self.metadata(owner_id, object_name) is not None

    def metadata(self, owner_id: str, object_name: str) -> StorageObjectMetadata | None:
        storage_path, _ = self._object_path(owner_id, object_name)
        path = f"object/info/{quote(self.config.supabase_bucket, safe='')}/{quote(storage_path, safe='/')}"
        try:
            response = self._request("GET", path)
        except StorageError:
            return None
        payload = response.json()
        size = int(payload.get("size", 0) or 0)
        return StorageObjectMetadata(owner_id, object_name, storage_path, size, payload.get("mimetype"), str(payload.get("etag", "")))


def build_storage_service(config: StorageConfig | None = None) -> StorageService:
    selected = config or load_storage_config()
    if selected.provider == "local":
        return LocalStorageAdapter(selected)
    if selected.provider == "supabase":
        return SupabaseStorageAdapter(selected)
    raise StorageError("unsupported storage provider")
