# STATE: tx-large-load-tracker

Updated 2026-10-06.

## Objective
A daily, sourced digest of ERCOT/Texas large-load interconnection (Batch Zero, the governor's audit
and permit freeze, 16 TAC §25.194) that runs through the Dec 10 / Dec 17 milestones. It supports
Alex's Anthropic Transaction Manager application as interview prep and as proof of AI-native ops.

## Authorization (2026-10-06, Alex in Cowork, project "AI resume")
- Chose "Anthropic application asset": rebuild the archived ercot-datacenter-bot as a Texas
  large-load tracker plus a short brief on what the freeze means for a capacity buyer.
- Approved redacting the plaintext Gmail app password from the archived bot's files (done).
- Not covered: external sends, adding this project to PORTFOLIO.yaml (portfolio decision).

## Done (2026-10-06)
- Tracker built (stdlib only); 10 offline tests pass on Python 3.10 (Linux) and 3.9.6 (macOS).
- First live run 2026-10-06 06:25 CT: 7/7 sources ok, 644 items recorded as baseline.
- Prep brief: ~/projects/AI resume/Job Search/applications/anthropic/texas-large-load-brief-2026-10-06.md

## Next
- Re-check the press-report milestones (Oct 19, Dec 10, Dec 17) against primary documents as they
  appear (PUCT open-meeting agenda; ERCOT filings in 58317/58481 or a new control number).
- After Dec 17: record the final Batch Zero classifications; decide whether to keep running.
- Possible next sources: ERCOT market notices; SEC filings of Texas data-center developers.

## Pending outside this repo
- Alex revokes the old Gmail app password in his Google account (only he can).
