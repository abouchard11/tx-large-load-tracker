"""HTTP fetch with honest outcomes: ok, blocked, or error. Never a silent empty."""
from __future__ import annotations

import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .sources import UA

BLOCKED_CODES = {401, 403, 407, 429, 451}


@dataclass
class FetchResult:
    status: str                 # ok | blocked | error
    http_code: Optional[int]
    body: str
    note: str = ""


def fetch(url: str, timeout: float = 30.0, retries: int = 2) -> FetchResult:
    note = ""
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                charset = resp.headers.get_content_charset() or "utf-8"
                return FetchResult("ok", resp.status, raw.decode(charset, errors="replace"))
        except urllib.error.HTTPError as exc:
            if exc.code in BLOCKED_CODES:
                return FetchResult("blocked", exc.code, "", f"HTTP {exc.code}")
            note = f"HTTP {exc.code}"
            if exc.code < 500:
                return FetchResult("error", exc.code, "", note)
        except (urllib.error.URLError, socket.timeout, ConnectionError, TimeoutError) as exc:
            note = f"{type(exc).__name__}: {getattr(exc, 'reason', exc)}"
        if attempt < retries:
            time.sleep(2 * (attempt + 1))
    return FetchResult("error", None, "", note)


def fetch_fixture(path: Path) -> FetchResult:
    """Offline stand-in for tests. A file holding just 'HTTP 403' simulates that response."""
    if not path.exists():
        return FetchResult("error", None, "", f"missing fixture {path.name}")
    body = path.read_text(encoding="utf-8", errors="replace")
    head = body.strip()
    if head.startswith("HTTP ") and len(head) < 20:
        code = int(head.split()[1])
        return FetchResult("blocked" if code in BLOCKED_CODES else "error", code, "", f"HTTP {code}")
    return FetchResult("ok", 200, body)
