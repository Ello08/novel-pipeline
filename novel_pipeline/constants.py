"""Shared defaults for page extraction."""

from __future__ import annotations

import re

USER_AGENT = "Mozilla/5.0 (compatible; ChapterPipeline/1.0)"
HEADERS = {"User-Agent": USER_AGENT}

NEXT_WORDS = re.compile(r"\b(next|sonraki|ileri|continue)\b", re.I)

CONTENT_SELECTORS = (
    ".chapter-content",
    ".reading-content",
    "#chapter-content",
    ".entry-content",
    "article",
    "main",
)

SKIP_TAGS = "script, style, nav, footer, header, aside, form"

IMAGE_SOURCES = ("data-src", "data-original", "src")

IMAGE_FORMATS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
    "GIF": ".gif",
}

MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}
