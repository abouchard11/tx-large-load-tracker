"""Render a run as a short markdown digest."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import List, Sequence

from .core import RunResult
from .sources import MILESTONES, SOURCES, Milestone, Source

try:
    from zoneinfo import ZoneInfo
    LOCAL = ZoneInfo("America/Chicago")
except Exception:  # pragma: no cover - no tz database on this machine
    LOCAL = None

MAX_PER_SOURCE = 12


def local_time(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts)
    return dt.astimezone(LOCAL) if LOCAL else dt


def _cell(value: object) -> str:
    return str(value or "").replace("|", "/").replace("\n", " ")


def _fmt_day(d: date) -> str:
    return f"{d:%b} {d.day}, {d.year}"


def _line(item: dict) -> str:
    extra = item.get("extra") or {}
    tag = extra.get("party") or extra.get("publisher") or ""
    title = str(item["title"]).replace("[", "(").replace("]", ")")
    return f"- {item.get('date') or 'undated'} · [{title}]({item['url']})" + (f" — {tag}" if tag else "")


def _newest_first(rows: List[dict]) -> List[dict]:
    return sorted(rows, key=lambda i: str(i.get("date") or ""), reverse=True)


def render(result: RunResult, sources: Sequence[Source] = SOURCES,
           milestones: Sequence[Milestone] = MILESTONES, recent_days: int = 60) -> str:
    when = local_time(result.run_at)
    today = when.date()
    labels = {s.id: s.label for s in sources}
    ok = sum(1 for h in result.health if h["status"] == "ok")
    status = f"{len(result.health)} sources · {ok} ok"
    if result.failures:
        status += f" · **{len(result.failures)} failed**"
    out: List[str] = [f"# Texas large-load tracker · {today.isoformat()}", "",
                      f"_Run {when.strftime('%Y-%m-%d %H:%M %Z')} · {status}_", ""]

    out += ["## Milestones", "", "| Date | When | What | Source |", "|---|---|---|---|"]
    for m in sorted(milestones, key=lambda m: m.date):
        day = date.fromisoformat(m.date)
        delta = (day - today).days
        if delta < -14:
            continue
        rel = "today" if delta == 0 else (f"in {delta} days" if delta > 0 else f"{-delta} days ago")
        flag = "" if m.confidence == "confirmed" else " _(press report)_"
        out.append(f"| {_fmt_day(day)} | {rel} | {_cell(m.what)}{flag} | {_cell(m.source)} |")
    out.append("")

    fresh = result.fresh
    out += [f"## New since last run ({len(fresh)})", ""]
    if not fresh:
        out += ["Nothing new.", ""]
    for s in sources:
        rows = [i for i in fresh if i["source"] == s.id]
        if not rows:
            continue
        out += [f"### {s.label}", ""]
        out += [_line(i) for i in _newest_first(rows)[:MAX_PER_SOURCE]]
        if len(rows) > MAX_PER_SOURCE:
            out.append(f"- ... and {len(rows) - MAX_PER_SOURCE} more in data/items.jsonl")
        out.append("")

    if result.first_run_sources:
        cutoff = (today - timedelta(days=recent_days)).isoformat()
        out += ["## Baseline", "",
                f"First run for {len(result.first_run_sources)} source(s): existing items were recorded, "
                f"not reported as new. Shown below: items dated {cutoff} or later.", ""]
        for sid in result.first_run_sources:
            mine = [i for i in result.recorded if i["source"] == sid]
            recent = [i for i in mine if str(i.get("date") or "") >= cutoff]
            out += [f"### {labels.get(sid, sid)} ({len(mine)} recorded)", ""]
            out += [_line(i) for i in _newest_first(recent)[:MAX_PER_SOURCE]] or ["- none dated in the window"]
            if len(recent) > MAX_PER_SOURCE:
                out.append(f"- ... and {len(recent) - MAX_PER_SOURCE} more in data/items.jsonl")
            out.append("")

    out += ["## Source health", "", "| Source | Status | Parsed | New | Note |", "|---|---|---|---|---|"]
    for h in result.health:
        st = h["status"] if h["status"] == "ok" else f"**{h['status']}**"
        out.append(f"| {_cell(labels.get(h['source'], h['source']))} | {st} | {h['parsed']} | "
                   f"{h['new']} | {_cell(h.get('note'))} |")
    out += ["", "_Public sources only. Open the linked primary document before quoting a number; "
                "milestones marked (press report) still need a primary source._", ""]
    return "\n".join(out)
