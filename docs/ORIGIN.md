# Origin

This project replaces `~/projects/.archive/stale-repos/ercot-datacenter-bot`, built Nov 11-15, 2025
as the lead engine for a "Houston Data Center Permitting Accelerator."

## What the old bot got wrong
- Its main monitor read ERCOT's generation interconnection queue (via gridstatus). All 1,810 rows
  were batteries, solar, wind and gas; its data-center flag was False on every row. The "Houston
  data centers" list it produced included a wind/solar project and a gas plant. The Nov 14 hybrid
  monitor caught this and moved to ERCOT large-load documents and news.
- Its ERCOT task-force URLs returned 404s and two news sites blocked or 404'd it, and the runs kept
  going as if nothing was wrong. This tracker treats blocked, failed or empty sources as failures
  and doesn't advance their state.
- No outreach was ever logged. The contact database was mostly guessed email patterns. The revenue
  table was an untested projection.
- A Gmail app password sat in plain text in its docs and config. It was redacted on 2026-10-06; the
  password itself still has to be revoked in the Google account.

## What changed in Texas since (as of 2026-10-06)
- ~474 GW of large-load requests in ERCOT, ~90% data centers (governor, Aug 3, 2026).
- PUCT approved ERCOT's Batch Zero batch-study process in June 2026; the Aug 3 audit directive paused
  classifications and the energization of new data-center and crypto loads.
- Conditional classifications went to TSPs on Sept 3: 362 loads (~192 GW) in base or studied
  categories, 373 projects (302.2 GW) excluded (ERCOT Board, Sept 14-15).
- 16 TAC §25.194 adopted Sept 18, effective Oct 8: $100k study fee and $50k/MW security before study.
- Sept 21: TCEQ told to suspend data-center permits until the ERCOT and TWDB audits are done.

The constraint moved from city permitting to grid interconnection, and the state froze it. Selling
"faster permits" stopped making sense, so the old bot's goal is retired.

## Kept from the old bot
The news-monitoring idea and the Google News RSS approach. Not the code: it was rewritten small,
standard-library only, with tests.
