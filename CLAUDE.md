# tx-large-load-tracker: agent contract

- Purpose: keep a current, sourced view of ERCOT/Texas large-load interconnection, through the
  Dec 10, 2026 audit filing and the Dec 17 PUC meeting. It backs Alex's interview prep for
  Anthropic's Transaction Manager (data-center capacity) role.
- Verify: `python3 -m unittest discover -s tests` (offline, must pass on /usr/bin/python3 3.9).
  Live check: `python3 track.py run`; exit 2 = a source failed. Read `reports/latest.md`.
- Standard library only. The LaunchAgent runs /usr/bin/python3, so don't add dependencies.
- Never add credentials. No email, Slack or other external sends from here without Alex's explicit go.
- A source that parses fewer than `min_items` is a failure, never a quiet zero. Keep that rule.
- When a page layout changes: save the new page as `tests/fixtures/<source_id>.txt`, fix the
  parser, and keep the tests green.
- `data/` is append-only history (items.jsonl, runs.jsonl). Don't rewrite it.
- Commits are attributed to Alex alone. No AI trailers.
- State and next steps: `.planning/STATE.md`.
