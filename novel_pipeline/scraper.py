"""Chapter-by-chapter fetching, resume state, and output auditing."""

from __future__ import annotations

import json
from pathlib import Path
import time
from urllib.parse import urlparse

from .epub_builder import build_epub
from .extract import extract, incomplete_reason
from .images import save_images
from .net import BrowserFetcher, get, new_session
from .util import atomic_json, sha256_bytes, validate_slug


def probe(args) -> int:
    if args.headless and not args.browser:
        raise ValueError("--headless yalnız --browser ile kullanılabilir")
    if args.min_chars < 1:
        raise ValueError("--min-chars en az 1 olmalı")
    if args.browser:
        with BrowserFetcher(args.headless) as browser:
            html, page_url = browser.get(args.url, args.content_selector, args.min_chars)
    else:
        response = get(new_session(), args.url)
        html, page_url = response.text, response.url

    title, paragraphs, images, next_url = extract(
        html, page_url, args.content_selector, args.next_selector
    )
    count = sum(map(len, paragraphs))
    print(f"Başlık: {title}\nMetin: {count} karakter / {len(paragraphs)} paragraf"
          f"\nGörsel adayı: {len(images)}\nSonraki: {next_url or '-'}")
    if count < args.min_chars:
        print("UYARI: Metin yetersiz; bölüm gövdesi dinamik yükleniyor "
              "veya sayfa erişime kapalı olabilir.")
        return 1
    return 0


def scrape(args) -> int:
    validate_slug(args.slug)
    if args.max_chapters < 0:
        raise ValueError("--max-chapters negatif olamaz")
    if args.delay < 0:
        raise ValueError("--delay negatif olamaz")
    if args.min_chars < 1:
        raise ValueError("--min-chars en az 1 olmalı")
    if args.headless and not args.browser:
        raise ValueError("--headless yalnız --browser ile kullanılabilir")

    root = Path(args.output)
    text_dir = root / "txt" / args.slug
    image_dir = root / "img" / args.slug
    text_dir.mkdir(parents=True, exist_ok=True)

    session = new_session()
    state_path = text_dir / "_state.json"
    report_path = text_dir / "_report.json"
    stats = {"requests": 0, "network_errors": 0, "statuses": {}}
    recent_lengths = [
        len(path.read_text(encoding="utf-8"))
        for path in sorted(text_dir.glob("[0-9][0-9][0-9][0-9].txt"))[-5:]
    ]

    state = {"start_url": args.url, "next_url": args.url, "completed": 0}
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("start_url") != args.url:
            raise ValueError("Aynı slug farklı bir başlangıç adresine ait; başka slug kullanın")
        print(f"Devam: {state['completed']} kayıtlı bölüm atlanıyor", flush=True)

    url = state.get("next_url")
    seen = set()
    index = int(state.get("completed", 0)) + 1
    host = urlparse(url).netloc if url else ""
    browser = BrowserFetcher(args.headless) if args.browser else None

    try:
        while url and (args.max_chapters == 0 or index <= args.max_chapters):
            if url in seen or urlparse(url).netloc != host:
                break
            seen.add(url)

            if args.browser:
                html, page_url = browser.get(url, args.content_selector, args.min_chars)
                stats["browser_pages"] = stats.get("browser_pages", 0) + 1
            else:
                response = get(session, url, stats=stats)
                html, page_url = response.text, response.url
            if urlparse(page_url).netloc != host:
                raise ValueError(f"Başka alana yönlendirme: {page_url}")

            title, paragraphs, images, next_url = extract(
                html, page_url, args.content_selector, args.next_selector
            )
            count = sum(map(len, paragraphs))
            reason = incomplete_reason(paragraphs)
            if reason:
                raise ValueError(f"{reason} ({index}, {url}); kaydedilmedi")
            if count < args.min_chars:
                raise ValueError(f"Kısa/boş bölüm ({index}, {url}, {count} karakter); "
                                 f"kaydedilmedi")
            if recent_lengths and count < 1500 and count < min(recent_lengths[-3:]) / 4:
                stats.setdefault("suspect_short", []).append({
                    "chapter": index,
                    "characters": count,
                    "url": url,
                })
                print(f"UYARI {index:04d}: Önceki bölümlere göre kısa "
                      f"({count} karakter); elle kontrol edin", flush=True)

            target = text_dir / f"{index:04d}.txt"
            if not target.exists():
                temp = target.with_name(target.name + ".tmp")
                temp.write_text("\n\n".join([title, *paragraphs]) + "\n", encoding="utf-8")
                temp.replace(target)

            if args.images:
                folder = image_dir / f"{index:04d}"
                manifest_path = folder / "_manifest.json"
                should_save = True
                if manifest_path.is_file():
                    previous = json.loads(manifest_path.read_text(encoding="utf-8"))
                    should_save = bool(previous.get("errors"))
                    if not should_save:
                        print(f"{index:04d}: mevcut bölüm/görsel manifesti", flush=True)
                if should_save:
                    result = save_images(session, images, folder, page_url,
                                         stats=stats, delay=args.delay)
                    print(f"{index:04d}: {count} karakter, "
                          f"{len(result['images'])} görsel", flush=True)
            else:
                print(f"{index:04d}: {count} karakter", flush=True)

            url = next_url if next_url != page_url else None
            state = {"start_url": args.url, "next_url": url, "completed": index}
            atomic_json(state_path, state)
            recent_lengths.append(count)
            index += 1
            if url and args.delay and (args.max_chapters == 0 or index <= args.max_chapters):
                time.sleep(args.delay)
    except Exception as exc:
        stats["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        if browser:
            browser.close()
        stats["completed"] = state["completed"]
        stats["last_url"] = url
        atomic_json(report_path, stats)
        print(f"Rapor: {report_path} | HTTP: {stats['statuses']}", flush=True)
    return 0


def audit(root: Path, slug: str, expected: int = 0, min_chars: int = 200) -> int:
    validate_slug(slug)
    if expected < 0:
        raise ValueError("--expected negatif olamaz")
    if min_chars < 0:
        raise ValueError("--min-chars negatif olamaz")
    folder = root / "txt" / slug
    chapters = sorted(folder.glob("[0-9][0-9][0-9][0-9].txt"))
    if not chapters:
        raise ValueError("Kontrol edilecek bölüm yok")

    lengths = [len(path.read_text(encoding="utf-8")) for path in chapters]
    numbers = {int(path.stem) for path in chapters}
    missing = sorted(set(range(1, max(numbers) + 1)) - numbers)
    short = [{"file": path.name, "characters": length}
             for path, length in zip(chapters, lengths) if length < min_chars]

    duplicates = []
    seen = {}
    for path in chapters:
        digest = sha256_bytes(path.read_bytes())
        if digest in seen:
            duplicates.append((seen[digest], path.name))
        seen[digest] = path.name

    report_path = folder / "_report.json"
    report = (json.loads(report_path.read_text(encoding="utf-8"))
              if report_path.is_file() else {})
    print(f"Bölüm: {len(chapters)} | karakter min/max: {min(lengths)}/{max(lengths)}"
          f"\nHedef: {expected or '-'}"
          f"\nEksik numara: {missing or '-'} | birebir aynı dosyalar: {duplicates or '-'}"
          f"\nKısa dosyalar (<{min_chars}): {short or '-'}"
          f"\nSon koşu HTTP: {report.get('statuses', {})}"
          f"\nŞüpheli kısa: {report.get('suspect_short', []) or '-'}"
          f"\nHata: {report.get('error', '-')}")

    failed = (bool(missing) or bool(duplicates) or bool(short)
              or bool(report.get("error")) or bool(report.get("suspect_short"))
              or bool(expected and len(chapters) < expected))
    return 1 if failed else 0


def fetch_epub(args) -> int:
    destination = build_epub(Path(args.output), args.slug, args.title,
                             args.author, args.lang)
    chapters = len(list((Path(args.output) / "txt" / args.slug).glob("[0-9][0-9][0-9][0-9].txt")))
    print(f"{chapters} bölüm → {destination}")
    return 0
