"""Content-addressed media store (FOUNDATION_PLAN §8.3).

Ingest: decode-verify with Pillow -> capture EXIF date for the DB -> re-encode
WITHOUT metadata (GPS in a photo can reveal a contributor's home) -> cap the
long edge at 2048 px -> sha256 of the PROCESSED bytes is the identity forever.
Duplicate sha = dedupe. Binaries never enter git; the commons gets refs only.
"""
from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ExifTags

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_LONG_EDGE = 2048
ALLOWED_FORMATS = {"JPEG": ("image/jpeg", ".jpg"), "PNG": ("image/png", ".png"),
                   "WEBP": ("image/webp", ".webp")}


class MediaError(Exception):
    def __init__(self, key: str):
        super().__init__(key)
        self.key = key


@dataclass
class ProcessedMedia:
    sha256: str
    mime_type: str
    size_bytes: int
    width: int
    height: int
    storage_path: str            # relative to MEDIA_ROOT
    exif_taken_at: str | None    # read BEFORE stripping; DB-only


def _exif_taken_at(img: Image.Image) -> str | None:
    try:
        exif = img.getexif()
        for tag_id, name in ExifTags.TAGS.items():
            if name == "DateTimeOriginal" and tag_id in exif:
                return str(exif[tag_id])
        return str(exif.get(306)) if 306 in exif else None  # DateTime
    except Exception:
        return None


def process_and_store(raw: bytes, media_root: Path) -> ProcessedMedia:
    if len(raw) > MAX_UPLOAD_BYTES:
        raise MediaError("media.too_large")
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception:
        raise MediaError("media.not_an_image")
    fmt = (img.format or "").upper()
    if fmt not in ALLOWED_FORMATS:
        raise MediaError("media.format_unsupported")
    mime, ext = ALLOWED_FORMATS[fmt]

    taken_at = _exif_taken_at(img)

    if max(img.size) > MAX_LONG_EDGE:
        img.thumbnail((MAX_LONG_EDGE, MAX_LONG_EDGE), Image.Resampling.LANCZOS)

    # Re-encode from pixel data only: no exif=, no icc, no xmp -> metadata gone.
    out = io.BytesIO()
    if fmt == "JPEG":
        img = img.convert("RGB")
        img.save(out, "JPEG", quality=88, optimize=True)
    elif fmt == "PNG":
        clean = Image.new(img.mode, img.size)
        clean.putdata(list(img.getdata()))
        clean.save(out, "PNG", optimize=True)
    else:
        img.save(out, "WEBP", quality=88)
    data = out.getvalue()

    sha = hashlib.sha256(data).hexdigest()
    rel = f"{sha[:2]}/{sha}{ext}"
    dest = media_root / rel
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        tmp.write_bytes(data)
        tmp.replace(dest)  # atomic on Windows too

    width, height = img.size
    return ProcessedMedia(sha256=sha, mime_type=mime, size_bytes=len(data),
                          width=width, height=height, storage_path=rel,
                          exif_taken_at=taken_at)
