"""Turn one chapter page into a title, paragraphs, images, and next URL."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .constants import CONTENT_SELECTORS, IMAGE_SOURCES, NEXT_WORDS, SKIP_TAGS


def find_content(soup: BeautifulSoup, selector: str | None):
    if selector:
        node = soup.select_one(selector)
        if node is None:
            raise ValueError(f"İçerik seçicisi bulunamadı: {selector}")
        return node
    for choice in CONTENT_SELECTORS:
        node = soup.select_one(choice)
        if node and len(node.get_text(" ", strip=True)) >= 200:
            return node
    candidates = soup.select("section, div")
    if candidates:
        node = max(candidates, key=lambda x: len(x.get_text(" ", strip=True)))
        if len(node.get_text(" ", strip=True)) >= 200:
            return node
    return soup.body or soup


def extract(html: str, url: str, content_selector: str | None = None,
            next_selector: str | None = None):
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find("h1")
    page_title = soup.title.get_text(" ", strip=True) if soup.title else ""
    heading_text = heading.get_text(" ", strip=True) if heading else ""
    title = (heading_text if heading_text and heading_text.casefold() in page_title.casefold()
             else page_title or heading_text or urlparse(url).path.strip("/"))

    content = find_content(soup, content_selector)
    # Parse a separate copy; keep the document intact for next-link discovery.
    body = BeautifulSoup(str(content), "html.parser")
    for tag in body.select(SKIP_TAGS):
        tag.decompose()

    paragraphs, illustrations = [], []
    for tag in body.find_all(["p", "img"]):
        if tag.name == "img":
            source = next((tag.get(key) for key in IMAGE_SOURCES if tag.get(key)), None)
            if source and not source.startswith(("data:", "blob:")):
                illustrations.append({
                    "url": urljoin(url, source),
                    "after_para": len(paragraphs) - 1,
                    "alt": tag.get("alt", ""),
                })
        else:
            if tag.find("br"):
                for br in tag.find_all("br"):
                    br.replace_with("\n")
                paragraphs.extend(line.strip() for line in tag.get_text().splitlines()
                                  if line.strip())
            else:
                text = tag.get_text(" ", strip=True)
                if text:
                    paragraphs.append(text)

    if not paragraphs:
        paragraphs = [p.strip() for p in body.get_text("\n", strip=True).splitlines()
                      if p.strip()]

    next_link = soup.select_one(next_selector) if next_selector else None
    if next_link is None:
        next_link = soup.select_one('a[rel~="next"]')
    if next_link is None:
        next_link = next((a for a in soup.find_all("a", href=True)
                          if NEXT_WORDS.search(a.get_text(" ", strip=True))
                          and len(a.get_text(" ", strip=True)) < 70), None)
    next_url = urljoin(url, next_link["href"]) if next_link and next_link.get("href") else None
    if next_url and urlparse(next_url).netloc != urlparse(url).netloc:
        next_url = None
    return title, paragraphs, illustrations, next_url


def incomplete_reason(paragraphs: list[str]) -> str | None:
    """Detect bodies that are still loading instead of a finished chapter."""
    tail = " ".join(paragraphs[-2:]).strip().casefold()
    if re.search(r"(?:^|\s)(?:loading|yükleniyor)(?:\.{3}|…)?\s*$", tail):
        return "Bölüm gövdesi eksik/yükleniyor"
    if "bölüm içeriği yüklenemedi" in tail:
        return "Bölüm gövdesi yüklenemedi"
    return None
