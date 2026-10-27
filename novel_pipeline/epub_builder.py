"""Build an EPUB from downloaded chapter text and image manifests."""

from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path

from ebooklib import epub

from .constants import MEDIA_TYPES
from .util import validate_slug


def build_epub(root: Path, slug: str, title: str = "", author: str = "",
               lang: str = "en") -> Path:
    validate_slug(slug)
    chapters = sorted((root / "txt" / slug).glob("[0-9][0-9][0-9][0-9].txt"))
    if not chapters:
        raise ValueError("EPUB için kayıtlı bölüm yok")

    book = epub.EpubBook()
    book.set_identifier(f"novel-pipeline-{slug}")
    book.set_title(title or slug.replace("-", " ").title())
    book.set_language(lang)
    if author:
        book.add_author(author)

    style = epub.EpubItem(
        uid="style",
        file_name="style/book.css",
        media_type="text/css",
        content=("body{font-family:serif;line-height:1.5}"
                 "img{max-width:100%;height:auto}h1{text-align:center}"),
    )
    book.add_item(style)

    spine = []
    for path in chapters:
        number = path.stem
        chunks = [x.strip() for x in re.split(r"\n\s*\n", path.read_text(encoding="utf-8"))
                  if x.strip()]
        chapter_title = chunks[0] if chunks else f"Chapter {number}"
        paragraphs = chunks[1:] if chunks else []

        images: dict[int, list[tuple[str, str]]] = {}
        manifest_path = root / "img" / slug / number / "_manifest.json"
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for image in manifest.get("images", []):
                source = root / "img" / slug / number / image["file"]
                media_type = MEDIA_TYPES.get(source.suffix.lower())
                if not source.is_file() or media_type is None:
                    continue
                destination = f"images/{number}_{source.name}"
                book.add_item(epub.EpubImage(
                    uid=f"img_{number}_{source.stem}",
                    file_name=destination,
                    media_type=media_type,
                    content=source.read_bytes(),
                ))
                images.setdefault(image.get("after_para", -1), []).append(
                    (destination, image.get("alt", ""))
                )

        def figures(at: int) -> str:
            return "".join(
                f'<figure><img src="{escape(dest, quote=True)}" '
                f'alt="{escape(alt, quote=True)}"/></figure>'
                for dest, alt in images.get(at, [])
            )

        content = [f"<h1>{escape(chapter_title)}</h1>", figures(-1)]
        for index, paragraph in enumerate(paragraphs):
            content.extend((f"<p>{escape(paragraph)}</p>", figures(index)))

        chapter = epub.EpubHtml(
            title=chapter_title,
            file_name=f"chapter_{number}.xhtml",
            lang=lang,
        )
        chapter.content = "\n".join(content)
        chapter.add_item(style)
        book.add_item(chapter)
        spine.append(chapter)

    book.toc = tuple(spine)
    book.spine = ["nav", *spine]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    destination = root / "epub" / f"{slug}.epub"
    destination.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(destination), book)
    return destination
