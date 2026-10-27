"""Download, validate, deduplicate, and index chapter illustrations."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import time

import requests
from PIL import Image

from .constants import IMAGE_FORMATS
from .net import get
from .util import atomic_json, atomic_write, sha256_bytes


def save_images(session: requests.Session, images: list[dict], folder: Path,
                referer: str, min_size: int = 400, stats: dict | None = None,
                delay: float = 0) -> dict:
    """Save accepted images and a manifest that records their text position."""
    folder.mkdir(parents=True, exist_ok=True)
    manifest = {"images": [], "errors": []}
    hashes = set()

    for index, candidate in enumerate(images):
        url = candidate["url"]
        if index and delay:
            time.sleep(delay)
        try:
            data = get(session, url, referer, stats).content
            image = Image.open(BytesIO(data))
            image.verify()
            image = Image.open(BytesIO(data))
            if min(image.size) < min_size:
                continue
            digest = sha256_bytes(data)
            if digest in hashes:
                continue
            hashes.add(digest)
            extension = IMAGE_FORMATS.get(image.format)
            if extension is None:
                manifest["errors"].append({
                    "url": url,
                    "error": "unsupported image format",
                })
                continue
            name = f"{len(manifest['images']) + 1:02d}{extension}"
            atomic_write(folder / name, data)
            manifest["images"].append({
                "file": name,
                "after_para": candidate["after_para"],
                "alt": candidate.get("alt", ""),
                "sha256": digest,
            })
        except (requests.RequestException, OSError, ValueError) as exc:
            manifest["errors"].append({
                "url": url,
                "error": f"{type(exc).__name__}: {exc}",
            })

    atomic_json(folder / "_manifest.json", manifest)
    return manifest
