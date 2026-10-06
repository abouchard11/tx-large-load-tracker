"""One run: fetch every source, diff against what we've seen, record it.

Rules that keep "quiet" from meaning "missed":
- a source that is blocked, errors, fails to parse, or parses suspiciously few items is a
  failure, and its saved state is left untouched so nothing is skipped on the next run;
- the first successful run of a source records a baseline instead of reporting everything as new.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set

from .fetch import FetchResult, fetch, fetch_fixture
from .parsers import parse
from .sources import SOURCES, Source

OK = "ok"


@dataclass
class RunResult:
    run_at: str
    health: List[dict]
    recorded: List[dict]                      # everything first seen this run, baseline included
    first_run_sources: List[str] = field(default_factory=list)

    @property
    def failures(self) -> List[dict]:
        return [h for h in self.health if h["status"] != OK]

    @property
    def fresh(self) -> List[dict]:
        return [i for i in self.recorded if not i.get("baseline")]


class Store:
    """Plain files under data/: state.json (seen keys), items.jsonl, runs.jsonl (append-only)."""

    def __init__(self, root: Path):
        self.dir = Path(root) / "data"
        self.state_path = self.dir / "state.json"
        self.items_path = self.dir / "items.jsonl"
        self.runs_path = self.dir / "runs.jsonl"

    def load_seen(self) -> Dict[str, Set[str]]:
        if not self.state_path.exists():
            return {}
        raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        return {k: set(v) for k, v in raw.get("seen", {}).items()}

    def save_seen(self, seen: Dict[str, Set[str]], run_at: str) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        payload = {"last_run": run_at, "seen": {k: sorted(v) for k, v in sorted(seen.items())}}
        tmp = self.state_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.state_path)

    def append(self, path: Path, rows: Iterable[dict]) -> None:
        rows = list(rows)
        if not rows:
            return
        self.dir.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    def last_run(self) -> List[dict]:
        if not self.runs_path.exists():
            return []
        rows = [json.loads(line) for line in self.runs_path.read_text(encoding="utf-8").splitlines()
                if line.strip()]
        if not rows:
            return []
        last = rows[-1]["run_at"]
        return [r for r in rows if r["run_at"] == last]


def _fetch(src: Source, fixtures: Optional[Path]) -> FetchResult:
    if fixtures is not None:
        return fetch_fixture(Path(fixtures) / f"{src.id}.txt")
    return fetch(src.url)


def run(root: Path, sources: Sequence[Source] = SOURCES, fixtures: Optional[Path] = None,
        now: Optional[datetime] = None) -> RunResult:
    store = Store(root)
    seen = store.load_seen()
    now = now or datetime.now(timezone.utc)
    run_at = now.isoformat(timespec="seconds")
    health: List[dict] = []
    recorded: List[dict] = []
    first_run: List[str] = []

    for src in sources:
        res = _fetch(src, fixtures)
        h = {"run_at": run_at, "source": src.id, "status": res.status, "http": res.http_code,
             "parsed": 0, "new": 0, "note": res.note}
        health.append(h)
        if res.status != OK:
            continue
        try:
            items = parse(src, res.body, now.date())
        except Exception as exc:  # a broken parser is a failure, never a quiet zero
            h.update(status="parse_error", note=f"{type(exc).__name__}: {exc}")
            continue
        h["parsed"] = len(items)
        if len(items) < src.min_items:
            h.update(status="suspect_empty",
                     note=f"parsed {len(items)}, expected at least {src.min_items}; the page may have changed")
            continue
        if src.keywords:
            patterns = [re.compile(k) for k in src.keywords]
            items = [i for i in items if any(p.search(str(i["title"]).lower()) for p in patterns)]
        is_first = src.id not in seen
        known = seen.setdefault(src.id, set())
        fresh: List[dict] = []
        for item in items:
            if item["key"] in known:
                continue
            known.add(item["key"])
            item.update(source=src.id, first_seen=run_at, baseline=is_first)
            fresh.append(item)
        if is_first:
            first_run.append(src.id)
        else:
            h["new"] = len(fresh)
        recorded.extend(fresh)

    store.append(store.items_path, recorded)
    store.append(store.runs_path, health)
    store.save_seen(seen, run_at)
    return RunResult(run_at, health, recorded, first_run)
