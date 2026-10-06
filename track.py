#!/usr/bin/env python3
"""Texas large-load tracker.

  python3 track.py run [--notify] [--fixtures DIR] [--root DIR]
  python3 track.py status [--root DIR]

`run` fetches every source, records what is new in data/, and writes reports/latest.md plus
reports/<date>.md. Exit code 2 means at least one source failed (blocked, error, parse error,
or suspiciously empty); that source's state is untouched and it is retried on the next run.
Standard library only; runs on macOS's /usr/bin/python3 (3.9).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from tracker.core import Store, run  # noqa: E402
from tracker.report import local_time, render  # noqa: E402


def notify(message: str) -> None:
    if sys.platform != "darwin":
        return
    safe = message.replace("\\", "").replace('"', "'")
    subprocess.run(["osascript", "-e", f'display notification "{safe}" with title "TX large-load tracker"'],
                   check=False, timeout=15)


def cmd_run(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    result = run(root, fixtures=Path(args.fixtures).resolve() if args.fixtures else None)
    text = render(result)
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    day = local_time(result.run_at).date().isoformat()
    (reports / f"{day}.md").write_text(text, encoding="utf-8")
    (reports / "latest.md").write_text(text, encoding="utf-8")
    failed = len(result.failures)
    summary = (f"{len(result.health)} sources, {len(result.health) - failed} ok, "
               f"{len(result.fresh)} new, {len(result.recorded) - len(result.fresh)} baseline")
    print(f"{local_time(result.run_at):%Y-%m-%d %H:%M %Z} | {summary} | reports/{day}.md")
    for h in result.failures:
        print(f"  FAILED {h['source']}: {h['status']} {h.get('note') or ''}".rstrip())
    if args.notify and (result.fresh or failed):
        notify(f"{len(result.fresh)} new item(s), {failed} source failure(s)")
    return 2 if failed else 0


def cmd_status(args: argparse.Namespace) -> int:
    rows = Store(Path(args.root).resolve()).last_run()
    if not rows:
        print("no runs recorded yet")
        return 1
    print(f"last run {rows[0]['run_at']}")
    for r in rows:
        print(f"  {r['source']:<20} {r['status']:<14} parsed={r['parsed']:<4} new={r['new']:<4} {r.get('note') or ''}")
    return 2 if any(r["status"] != "ok" for r in rows) else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=str(HERE), help="project directory holding data/ and reports/")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_run = sub.add_parser("run", help="fetch, diff, write the digest")
    p_run.add_argument("--fixtures", help="read saved pages from this directory instead of the network")
    p_run.add_argument("--notify", action="store_true", help="macOS notification when something is new or failed")
    p_run.set_defaults(func=cmd_run)
    sub.add_parser("status", help="show the last run's source health").set_defaults(func=cmd_status)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
