"""HTTP requests, retries, and the optional Selenium browser."""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import shutil
import time

import requests

from .constants import HEADERS


def new_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def get(session: requests.Session, url: str, referer: str | None = None,
        stats: dict | None = None, retries: int = 3) -> requests.Response:
    """GET a URL with Retry-After aware backoff for 429 and 5xx responses."""
    headers = {"Referer": referer} if referer else None
    for attempt in range(retries + 1):
        try:
            response = session.get(url, headers=headers, timeout=30)
        except (requests.Timeout, requests.ConnectionError):
            if stats is not None:
                stats["network_errors"] += 1
            if attempt == retries:
                raise
            time.sleep(min(2 ** attempt * 3, 60))
            continue
        if stats is not None:
            stats["requests"] += 1
            status = str(response.status_code)
            stats["statuses"][status] = stats["statuses"].get(status, 0) + 1
        if response.status_code == 429 or 500 <= response.status_code <= 599:
            if attempt < retries:
                retry_after = response.headers.get("Retry-After", "")
                try:
                    wait = float(retry_after)
                except ValueError:
                    try:
                        wait = (parsedate_to_datetime(retry_after)
                                - datetime.now(timezone.utc)).total_seconds()
                    except (TypeError, ValueError, OverflowError):
                        wait = 2 ** attempt * 3
                wait = max(1, min(wait, 120))
                print(f"HTTP {response.status_code}: {wait:.0f} sn bekle, "
                      f"yeniden dene ({attempt + 1}/{retries})", flush=True)
                time.sleep(wait)
                continue
        response.raise_for_status()
        return response
    raise RuntimeError("İstek tamamlanamadı")


class BrowserFetcher:
    """Reuse one visible browser session for JavaScript-rendered pages."""

    def __init__(self, headless: bool = False):
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service

        options = Options()
        browser_bin = shutil.which("chromium-browser") or shutil.which("chromium")
        if browser_bin:
            options.binary_location = browser_bin
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver_bin = shutil.which("chromedriver")
        self.driver = webdriver.Chrome(
            service=Service(driver_bin) if driver_bin else Service(),
            options=options,
        )

    def get(self, url: str, selector: str | None, min_chars: int,
            timeout: int = 60) -> tuple[str, str]:
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.common.exceptions import TimeoutException
        from bs4 import BeautifulSoup

        from .extract import find_content

        self.driver.get(url)

        def loaded(_driver):
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            try:
                node = find_content(soup, selector)
            except ValueError:
                return False
            text = node.get_text(" ", strip=True)
            return len(text) >= min_chars and "yüklenemedi" not in text.casefold()

        try:
            WebDriverWait(self.driver, timeout, poll_frequency=2).until(loaded)
        except TimeoutException as exc:
            raise ValueError(
                f"Tarayıcıda bölüm metni yüklenmedi ({url}); kayıt yapılmadı"
            ) from exc
        return self.driver.page_source, self.driver.current_url

    def close(self) -> None:
        self.driver.quit()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
