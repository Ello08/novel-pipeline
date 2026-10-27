"""Small filesystem and validation helpers."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

SLUG_PATTERN = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,99}")


def validate_slug(slug: str) -> None:
    """Reject slugs that could escape the output directory."""
    if not SLUG_PATTERN.fullmatch(slug):
        raise ValueError("--slug yalnız harf, rakam, - ve _ içerebilir")


def atomic_json(path: Path, data: dict) -> None:
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def atomic_write(path: Path, data: bytes) -> None:
    temp = path.with_name(path.name + ".tmp")
    temp.write_bytes(data)
    temp.replace(path)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
