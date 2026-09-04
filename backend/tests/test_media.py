"""Media pipeline: EXIF (incl. GPS) stripped, sha of processed bytes, dedupe."""
from __future__ import annotations

import io

from PIL import Image

from conftest import wizard_payload


def jpeg_with_exif() -> bytes:
    img = Image.new("RGB", (2600, 1400), (120, 90, 60))
    exif = Image.Exif()
    exif[0x0110] = "SyntheticCam 3000"        # Model
    exif[0x9003] = "2026:08:20 10:11:12"      # DateTimeOriginal
    exif[0x010F] = "Synthetic Industries"     # Make
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=exif)
    return buf.getvalue()


def _submission(client, headers) -> str:
    r = client.post("/api/v1/submissions", headers=headers, json=wizard_payload())
    return r.get_json()["submission"]["public_id"]


def upload(client, headers, pid: str, data: bytes, name="photo.jpg"):
    return client.post(
        f"/api/v1/submissions/{pid}/media", headers=headers,
        data={"file": (io.BytesIO(data), name), "caption": "vue fictive"},
        content_type="multipart/form-data",
    )


def test_upload_strips_exif_and_caps_size(commons_app, contributor, tmp_path):
    client, headers = contributor
    pid = _submission(client, headers)
    raw = jpeg_with_exif()
    assert Image.open(io.BytesIO(raw)).getexif()  # premise: EXIF present in input

    r = upload(client, headers, pid, raw)
    assert r.status_code == 201
    body = r.get_json()
    assert body["width"] <= 2048 and body["height"] <= 2048

    media_root = commons_app.config["MEDIA_ROOT"]
    stored = media_root / body["sha256"][:2] / f"{body['sha256']}.jpg"
    assert stored.exists()
    processed = Image.open(stored)
    assert dict(processed.getexif()) == {}     # metadata gone
    # owner can fetch it back pre-publication; anonymous cannot
    assert client.get(f"/api/v1/media/{body['sha256']}").status_code == 200
    anon = commons_app.test_client()
    assert anon.get(f"/api/v1/media/{body['sha256']}").status_code == 404


def test_duplicate_upload_dedupes(contributor):
    client, headers = contributor
    pid = _submission(client, headers)
    raw = jpeg_with_exif()
    first = upload(client, headers, pid, raw).get_json()
    second = upload(client, headers, pid, raw).get_json()
    assert first["sha256"] == second["sha256"]
    detail = client.get(f"/api/v1/submissions/{pid}", headers=headers).get_json()
    assert len(detail["submission"]["media"]) == 1


def test_non_image_rejected(contributor):
    client, headers = contributor
    pid = _submission(client, headers)
    r = upload(client, headers, pid, b"not an image at all", name="x.jpg")
    assert r.status_code == 422
    assert r.get_json()["error"] == "media.not_an_image"


def test_oversize_rejected(contributor, monkeypatch):
    from openexits_panel.services import media_store
    monkeypatch.setattr(media_store, "MAX_UPLOAD_BYTES", 1000)
    client, headers = contributor
    pid = _submission(client, headers)
    r = upload(client, headers, pid, jpeg_with_exif())
    assert r.status_code == 422
    assert r.get_json()["error"] == "media.too_large"
