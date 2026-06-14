import json
import threading
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from utils.logger import setup_logger
logger = setup_logger(__name__)

SAVE_DIR = Path(__file__).resolve().parent.parent / "scraped_content"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# ----------------------------------------------------------------
# HTTP client with connection pooling (keep-alive + HTTP/2)
# ----------------------------------------------------------------

_HTTP_CLIENT: httpx.Client | None = None


def _get_http_client() -> httpx.Client:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None:
        _HTTP_CLIENT = httpx.Client(
            headers=_HEADERS,
            timeout=httpx.Timeout(20.0, connect=10.0, read=10.0),
            limits=httpx.Limits(max_keepalive_connections=10),
            http2=True,
        )
    return _HTTP_CLIENT


def _fetch_raw(url: str) -> str | None:
    try:
        resp = _get_http_client().get(url)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        logger.info(f"HTTP fetch failed: {e}")
        return None


# ----------------------------------------------------------------
# Persistent Playwright browser (launched once, reused across calls)
# ----------------------------------------------------------------

_PLAYWRIGHT = None
_BROWSER = None
_PW_LOCK = threading.Lock()


def _get_browser():
    global _PLAYWRIGHT, _BROWSER
    if _BROWSER is None:
        with _PW_LOCK:
            if _BROWSER is None:
                try:
                    _PLAYWRIGHT = sync_playwright().start()
                    _BROWSER = _PLAYWRIGHT.firefox.launch(
                        headless=True,
                        args=["--disable-gpu", "--no-sandbox"],
                    )
                except Exception as e:
                    logger.error(f"Failed to launch Playwright browser: {e}")
                    return None
    return _BROWSER


def _fallback_playwright(url: str) -> str | None:
    browser = _get_browser()
    if browser is None:
        logger.info("Playwright browser unavailable")
        return None

    context = None
    try:
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent=_HEADERS["User-Agent"],
        )
        page = context.new_page()
        page.route(
            "**/*",
            lambda route: route.abort()
            if route.request.resource_type
            in ("image", "stylesheet", "font", "media")
            else route.continue_(),
        )
        page.goto(url, wait_until="load", timeout=10000)
        text = page.evaluate("document.body.innerText")
        return text
    except Exception as e:
        logger.info(f"Playwright render failed: {e}")
        return None
    finally:
        if context:
            try:
                context.close()
            except Exception:
                pass


# ----------------------------------------------------------------
# Raw HTML cache (TTL: 5 minutes)
# ----------------------------------------------------------------

_RAW_CACHE: dict[str, tuple[float, str]] = {}
_CACHE_TTL = 300


def _get_cached_html(url: str) -> str | None:
    entry = _RAW_CACHE.get(url)
    if entry and time.time() - entry[0] < _CACHE_TTL:
        logger.info(f"Raw HTML cache hit: {url}")
        return entry[1]
    return None


def _set_cached_html(url: str, html: str):
    _RAW_CACHE[url] = (time.time(), html)


# ----------------------------------------------------------------
# HTML processing helpers
# ----------------------------------------------------------------

def _clean_soup(soup: BeautifulSoup) -> None:
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "noscript"]):
        tag.decompose()
    for tag in soup.find_all(class_=lambda c: c and any(
        kw in (c or "").lower() for kw in ["sidebar", "ad-", "advertisement", "cookie", "popup", "modal"]
    )):
        tag.decompose()


def _find_main_content(soup: BeautifulSoup) -> BeautifulSoup:
    for selector in ["article", "main", '[role="main"]', '[role="article"]']:
        el = soup.select_one(selector)
        if el:
            return el
    return soup


def _extract_main_content(soup: BeautifulSoup) -> str:
    _clean_soup(soup)
    return _find_main_content(soup).get_text("\n", strip=True)


def _html_to_markdown(soup: BeautifulSoup) -> str:
    try:
        import html2text
        h = html2text.HTML2Text()
        h.body_width = 0
        h.ignore_links = False
        h.ignore_images = False
        h.ignore_emphasis = False
        h.protect_links = True
        h.unicode_snob = True
        return h.handle(str(soup)).strip()
    except ImportError:
        pass

    lines = []
    for el in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "pre", "blockquote", "hr", "br"]):
        tag = el.name
        text = el.get_text(strip=True)
        if tag == "hr":
            lines.append("---")
        elif tag == "br":
            lines.append("")
        elif tag in ("h1",):
            lines.append(f"# {text}")
        elif tag in ("h2",):
            lines.append(f"## {text}")
        elif tag in ("h3",):
            lines.append(f"### {text}")
        elif tag in ("h4", "h5", "h6"):
            prefix = "#" * int(tag[1])
            lines.append(f"{prefix} {text}")
        elif tag == "li":
            lines.append(f"- {text}")
        elif tag == "blockquote":
            lines.append(f"> {text}")
        elif tag == "pre":
            lines.append(f"```\n{text}\n```")
        elif tag == "p":
            lines.append(text)
            lines.append("")

    return "\n".join(lines).strip()


# ----------------------------------------------------------------
# fetch_url — full page content extraction
# ----------------------------------------------------------------

def fetch_url(parameters: dict, player=None, progress=None, **kwargs) -> str:
    url = (parameters or {}).get("url", "").strip()
    fmt = (parameters or {}).get("format", "text").strip().lower()
    mode = (parameters or {}).get("mode", "article").strip().lower()

    if not url:
        return "Please provide a URL."

    if player:
        player.write_log(f"[Fetch] {url}")

    logger.info(f"Fetching: {url}  mode={mode}  format={fmt}")

    if progress:
        progress(5, f"Connecting to {url[:50]}...")

    # Cached or fresh fetch
    pw_tried = False
    html = _get_cached_html(url)
    if html is None:
        html = _fetch_raw(url)
        if not html:
            if progress:
                progress(20, "JS render required — launching Playwright...")
            html = _fallback_playwright(url)
            pw_tried = True
        if html:
            _set_cached_html(url, html)

    if not html:
        return "Failed to fetch the page."

    if progress:
        progress(40, "Parsing HTML...")

    soup = BeautifulSoup(html, "html.parser")

    if fmt == "markdown":
        _clean_soup(soup)
        if progress:
            progress(60, "Cleaning content...")
        content = _find_main_content(soup)
        if progress:
            progress(75, "Converting to markdown...")
        text = _html_to_markdown(content)
    elif mode == "article":
        if progress:
            progress(60, "Extracting article...")
        text = _extract_main_content(soup)
    elif mode == "raw":
        text = soup.get_text("\n", strip=True)
    else:
        body = soup.find("body") or soup
        text = body.get_text("\n", strip=True)

    # Second-chance Playwright only if raw HTTP succeeded but got hollow content
    if len(text) < 100 and not pw_tried:
        logger.info(f"Only {len(text)} chars — trying Playwright fallback")
        if progress:
            progress(80, "Low content — retrying with JS engine...")
        pw_text = _fallback_playwright(url)
        if pw_text and len(pw_text) > len(text):
            text = pw_text

    text = text.strip()
    if not text:
        return "Page appears to be empty or requires JavaScript."

    if len(text) > 8000:
        text = text[:8000] + "\n\n[...truncated]"

    if progress:
        progress(100, "Done")

    logger.info(f"Fetched {len(text):,} chars")
    return text


# ----------------------------------------------------------------
# scrape_url — structured data extraction via CSS selectors
# ----------------------------------------------------------------

def scrape_url(parameters: dict, player=None, progress=None, **kwargs) -> str:
    url = (parameters or {}).get("url", "").strip()
    selectors_raw = (parameters or {}).get("selectors", "{}")
    attribute = (parameters or {}).get("attribute", "text").strip().lower()

    if not url:
        return "Please provide a URL."

    try:
        selectors = json.loads(selectors_raw) if isinstance(selectors_raw, str) else selectors_raw
    except json.JSONDecodeError as e:
        return f"Invalid selectors JSON: {e}"

    if not isinstance(selectors, dict) or not selectors:
        return "Please provide a valid selectors object."

    if player:
        player.write_log(f"[Scrape] {url}")

    logger.info(f"Scraping: {url}  selectors={selectors}  attr={attribute}")

    if progress:
        progress(5, f"Fetching {url[:50]}...")

    html = _get_cached_html(url)
    if html is None:
        html = _fetch_raw(url)
        if not html:
            if progress:
                progress(30, "JS fallback...")
            html = _fallback_playwright(url)
        if html:
            _set_cached_html(url, html)

    if not html:
        return "Failed to fetch the page."

    if progress:
        progress(50, "Parsing with selectors...")

    soup = BeautifulSoup(html, "html.parser")
    result = {}

    total = len(selectors)
    for i, (field, selector) in enumerate(selectors.items()):
        if progress:
            pct = 50 + int((i / total) * 40)
            progress(pct, f"Extracting '{field}'...")
        elements = soup.select(str(selector))
        if not elements:
            result[field] = None
            continue
        if attribute == "text":
            result[field] = [el.get_text(strip=True) for el in elements]
        elif attribute == "html":
            result[field] = [str(el) for el in elements]
        elif attribute == "href":
            result[field] = [el.get("href") for el in elements if el.get("href")]
        elif attribute == "src":
            result[field] = [el.get("src") for el in elements if el.get("src")]
        else:
            result[field] = [el.get(attribute) for el in elements]

    if progress:
        progress(95, "Formatting...")

    output = json.dumps(result, indent=2, ensure_ascii=False)
    logger.info(f"Scraped {len(output):,} chars")

    if progress:
        progress(100, "Done")

    return output


# ----------------------------------------------------------------
# save_content — write scraped data to disk
# ----------------------------------------------------------------

def save_content(parameters: dict, player=None, **kwargs) -> str:
    filename = (parameters or {}).get("filename", "").strip()
    content = (parameters or {}).get("content", "").strip()
    fmt = (parameters or {}).get("format", "txt").strip().lower()

    if not filename or not content:
        return "Please provide both filename and content."

    if fmt not in ("txt", "md", "html"):
        fmt = "txt"

    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    filepath = SAVE_DIR / f"{filename}.{fmt}"
    filepath.write_text(content, encoding="utf-8")

    msg = f"Saved to {filepath}."
    logger.info(msg)
    if player:
        player.write_log(msg)
    return str(filepath)
