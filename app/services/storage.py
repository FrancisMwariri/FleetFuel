import hashlib
import os
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image, UnidentifiedImageError

IMAGE_SIGNATURES = {
    "image/jpeg": (b"\xff\xd8\xff", ".jpg"),
    "image/png": (b"\x89PNG\r\n\x1a\n", ".png"),
}


def store_image(data: bytes, content_type: str, directory: str) -> tuple[str, int, str]:
    signature = IMAGE_SIGNATURES.get(content_type)
    if signature is None or not data.startswith(signature[0]):
        raise ValueError("Only valid JPEG and PNG images are accepted")
    try:
        with Image.open(BytesIO(data)) as image:
            expected_format = "JPEG" if content_type == "image/jpeg" else "PNG"
            if image.format != expected_format:
                raise ValueError("Image content does not match its declared type")
            if image.width * image.height > 20_000_000:
                raise ValueError("Image dimensions exceed the supported limit")
            image.verify()
    except (UnidentifiedImageError, OSError):
        raise ValueError("Image data is invalid or incomplete") from None
    root = Path(directory).resolve()
    root.mkdir(parents=True, exist_ok=True)
    key = f"{uuid4().hex}{signature[1]}"
    destination = root / key
    temporary = root / f".{key}.tmp"
    try:
        temporary.write_bytes(data)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return key, len(data), hashlib.sha256(data).hexdigest()


def resolve_storage_key(key: str, directory: str) -> Path:
    root = Path(directory).resolve()
    candidate = (root / key).resolve()
    if candidate.parent != root:
        raise ValueError("Invalid storage key")
    return candidate
