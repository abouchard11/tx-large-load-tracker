# Texas large-load tracker

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23502963.svg)](https://doi.org/10.5281/zenodo.23502963)

Watches the public record on large-load (mostly data-center) interconnection in ERCOT and writes a
dated digest: what changed since the last run, which deadlines are coming, and whether every source
was actually read.

Rebuilt 2026-10-06 from the archived `ercot-datacenter-bot` (Nov 2025). `docs/ORIGIN.md` says what
was wrong with the old bot and what changed in Texas since.

## What it watches

| Source | Why it matters |
|---|---|
| ERCOT Large Load Integration page (documents) | Batch Zero forms, RFIs and guidance appear here first |
| PUCT Project 58481 filings | 16 TAC §25.194: the large-load interconnection standards (adopted Sept 18, 2026, effective Oct 8) |
| PUCT Project 58317 filings | SB 6 implementation; public comment on data centers lands here |
| Governor's office news (filtered) | The Aug 3 audit and the Sept 21 permit freeze both came from here |
| Google News: "Batch Zero" ERCOT | Developer disclosures and trade coverage of classifications |
| Google News: Texas data-center policy | Audit, moratorium, TCEQ and PUCT coverage |
| Google News: Anthropic / Fluidstack in Texas | Sites that matter for the Anthropic capacity story |

Milestones (with their sources) live in `tracker/sources.py`. Dates marked "press report" still need
a primary document.

## Run it

```
python3 track.py run            # fetch, diff, write reports/latest.md and reports/<date>.md
python3 track.py run --notify   # same, plus a macOS notification when something is new or a source failed
python3 track.py status         # last run's source health
python3 -m unittest discover -s tests   # offline tests against pages saved 2026-10-06
```

Exit code 2 means a source failed (blocked, error, parse error, or suspiciously few items). A failed
source never advances its saved state, so nothing gets skipped; it is retried on the next run. A
source's first good run records a baseline instead of reporting everything as new.

Standard library only. It must keep running on macOS's `/usr/bin/python3` (3.9), which the scheduled
job uses.

## Scheduled run

LaunchAgent `dev.midnightdev.tx-large-load-tracker` (copy in `ops/`) runs `track.py run --notify`
daily at 7:37 AM Central. If the Mac is asleep, it runs on wake. Output goes to `logs/launchd.log`.
Stop it with:

```
launchctl bootout gui/$(id -u)/dev.midnightdev.tx-large-load-tracker
```

## Layout

```
track.py             CLI
tracker/sources.py   sources + milestones (edit here)
tracker/fetch.py     HTTP with honest outcomes (ok / blocked / error)
tracker/parsers.py   one parser per source type
tracker/core.py      run: fetch, diff, record (data/state.json, data/items.jsonl, data/runs.jsonl)
tracker/report.py    markdown digest
tests/               offline tests + saved pages
ops/                 LaunchAgent plist
```

`data/`, `reports/` and `logs/` are generated and stay out of git.

## Limits

- Public sources only, no credentials. Google News links are redirect URLs.
- ERCOT document dates come from the file path, which is the upload date, not always the
  document's own date.
- This tracks filings and coverage. It is not legal advice and it does not predict which projects
  clear the audit.
