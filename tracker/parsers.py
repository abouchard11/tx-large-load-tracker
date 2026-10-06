"""Turn each source's page into items: {key, title, url, date (YYYY-MM-DD or None), extra}."""
from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from datetime import date
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional
from urllib.parse import urljoin

Item = Dict[str, object]

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def _text(fragment: str) -> str:
    return _WS.sub(" ", html.unescape(_TAG.sub(" ", fragment))).strip()


# ERCOT ---------------------------------------------------------------------
# Document links carry their posting date in the path: /files/docs/YYYY/MM/DD/name.ext
_ERCOT_DOC = re.compile(
    r'<a\b[^>]*href="([^"]*/files/docs/(\d{4})/(\d{2})/(\d{2})/[^"]+)"[^>]*>(.*?)</a>',
    re.S | re.I)


def parse_ercot_docs(body: str, base_url: str) -> List[Item]:
    items: Dict[str, Item] = {}
    for href, y, m, d, label in _ERCOT_DOC.findall(body):
        url = urljoin(base_url, html.unescape(href))
        title = _text(label) or url.rsplit("/", 1)[-1]
        items.setdefault(url, {"key": url, "title": title, "url": url, "date": f"{y}-{m}-{d}"})
    return list(items.values())


# PUCT Interchange ------------------------------------------------------------
_ROW = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S | re.I)
_CELL = re.compile(r"<td\b[^>]*>(.*?)</td>", re.S | re.I)
_HREF = re.compile(r'href="([^"]+)"', re.I)


def _us_date(value: str) -> Optional[str]:
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})$", value.strip())
    return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else None


def parse_puct_filings(body: str, base_url: str, project: str) -> List[Item]:
    out: List[Item] = []
    for row in _ROW.findall(body):
        cells = _CELL.findall(row)
        if len(cells) != 5:
            continue
        number = _text(cells[0])
        if not number.isdigit():
            continue
        href = _HREF.search(cells[0])
        url = urljoin(base_url, html.unescape(href.group(1))) if href else base_url
        out.append({
            "key": f"{project}:{number}",
            "title": _text(cells[4]),
            "url": url,
            "date": _us_date(_text(cells[1])),
            "extra": {"project": project, "item": int(number),
                      "party": _text(cells[2]), "type": _text(cells[3])},
        })
    return out


# Governor's office -------------------------------------------------------------
# List entries show "Oct" / "2" without a year; the year is inferred from the run date.
_GOV_BLOCK = re.compile(r'<div class="media-object m-b-4">', re.I)
_GOV_MONTH = re.compile(r'class="date-month">\s*([A-Za-z]{3})', re.I)
_GOV_DAY = re.compile(r'class="date-day">\s*(\d{1,2})', re.I)
_GOV_LINK = re.compile(
    r'<a\b[^>]*href="((?:https://gov\.texas\.gov)?/news/post/[^"]+)"[^>]*>(.*?)</a>', re.S | re.I)
_MONTHS = {name: i for i, name in enumerate(
    ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}


def _gov_date(block: str, today: date) -> Optional[str]:
    mon, day = _GOV_MONTH.search(block), _GOV_DAY.search(block)
    if not (mon and day):
        return None
    month = _MONTHS.get(mon.group(1).lower())
    if not month:
        return None
    year = today.year - 1 if month > today.month else today.year
    try:
        return date(year, month, int(day.group(1))).isoformat()
    except ValueError:
        return None


def parse_gov_news(body: str, base_url: str, today: date) -> List[Item]:
    items: Dict[str, Item] = {}
    for block in _GOV_BLOCK.split(body):
        when = _gov_date(block, today)
        for href, label in _GOV_LINK.findall(block):
            title = _text(label)
            if not title:
                continue                      # image links carry no text; the title link follows
            url = urljoin(base_url, html.unescape(href))
            if url not in items:
                items[url] = {"key": url, "title": title, "url": url, "date": when}
            elif items[url]["date"] is None and when:
                items[url]["date"] = when
    return list(items.values())


# RSS (Google News) ------------------------------------------------------------------
def parse_rss(body: str) -> List[Item]:
    root = ET.fromstring(body.encode("utf-8"))
    out: List[Item] = []
    for node in root.iter("item"):
        title = (node.findtext("title") or "").strip()
        link = (node.findtext("link") or "").strip()
        if not (title and link):
            continue
        when = None
        pub = node.findtext("pubDate")
        if pub:
            try:
                when = parsedate_to_datetime(pub).date().isoformat()
            except (TypeError, ValueError, IndexError):
                when = None
        out.append({"key": (node.findtext("guid") or link).strip(), "title": title, "url": link,
                    "date": when, "extra": {"publisher": (node.findtext("source") or "").strip()}})
    return out


def parse(source, body: str, today: date) -> List[Item]:
    if source.kind == "ercot_docs":
        return parse_ercot_docs(body, source.url)
    if source.kind == "puct_filings":
        return parse_puct_filings(body, source.url, source.project or "")
    if source.kind == "gov_news":
        return parse_gov_news(body, source.url, today)
    if source.kind == "rss":
        return parse_rss(body)
    raise ValueError(f"unknown source kind: {source.kind}")
