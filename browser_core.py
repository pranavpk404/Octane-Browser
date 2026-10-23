"""Pure helpers shared by the Octane browser shell and its tests."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import quote_plus, urlparse

DEFAULT_SEARCH_ENGINE = "https://duckduckgo.com/"
SEARCH_TEMPLATES = {
    "google.com": "https://www.google.com/search?q={query}",
    "bing.com": "https://www.bing.com/search?q={query}",
    "duckduckgo.com": "https://duckduckgo.com/?q={query}",
}
MAX_HISTORY = 200
MAX_BOOKMARKS = 100
MAX_TITLE_LENGTH = 160


def _hostname(value: str) -> str:
    try:
        return (urlparse(value).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def valid_search_engine(value: str | None) -> str:
    candidate = (value or "").strip()
    return candidate if _hostname(candidate) in SEARCH_TEMPLATES else DEFAULT_SEARCH_ENGINE


def load_search_engine(path: Path) -> str:
    try:
        return valid_search_engine(path.read_text(encoding="utf-8").splitlines()[0])
    except (OSError, IndexError, UnicodeDecodeError):
        return DEFAULT_SEARCH_ENGINE


def save_search_engine(path: Path, value: str) -> str:
    selected = valid_search_engine(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(f"{selected}\n", encoding="utf-8")
    temporary.replace(path)
    return selected


def valid_page_url(value: str | None) -> str | None:
    candidate = (value or "").strip()
    try:
        parsed = urlparse(candidate)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        return None
    return candidate


def _page_record(value: object) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    url = valid_page_url(value.get("url"))
    title = value.get("title")
    visited_at = value.get("visited_at")
    if not url or not isinstance(title, str) or not title.strip() or not isinstance(visited_at, str):
        return None
    return {"url": url, "title": title.strip()[:MAX_TITLE_LENGTH], "visited_at": visited_at[:40]}


def load_page_list(path: Path, limit: int) -> list[dict[str, str]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return []
    if not isinstance(raw, dict) or raw.get("version") != 1 or not isinstance(raw.get("items"), list):
        return []
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in raw["items"][:limit]:
        record = _page_record(item)
        if record and record["url"] not in seen:
            seen.add(record["url"])
            result.append(record)
    return result


def save_page_list(path: Path, items: list[dict[str, str]], limit: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "items": items[:limit]}
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")
    temporary.replace(path)


def add_page(items: list[dict[str, str]], url: str, title: str, visited_at: str, limit: int) -> list[dict[str, str]]:
    record = _page_record({"url": url, "title": title, "visited_at": visited_at})
    if not record:
        return items[:limit]
    return [record, *[item for item in items if item.get("url") != record["url"]]][:limit]


def search_url(homepage: str, query: str) -> str:
    template = SEARCH_TEMPLATES.get(_hostname(homepage), SEARCH_TEMPLATES["duckduckgo.com"])
    return template.format(query=quote_plus(query.strip()))


def _looks_like_host(value: str) -> bool:
    return bool(re.match(r"^(?:localhost|(?:[a-z0-9-]+\.)+[a-z]{2,})(?::\d+)?(?:/|$)", value, re.IGNORECASE))


def normalize_address(value: str, homepage: str) -> str:
    text = value.strip()
    if not text:
        return valid_search_engine(homepage)
    if re.match(r"^[a-z][a-z0-9+.-]*://", text, re.IGNORECASE):
        candidate = text
    elif _looks_like_host(text):
        candidate = f"https://{text}"
    else:
        return search_url(homepage, text)
    try:
        parsed = urlparse(candidate)
    except ValueError:
        return search_url(homepage, text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        return search_url(homepage, text)
    return candidate
