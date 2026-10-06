"""Offline tests against pages saved on 2026-10-06 (tests/fixtures/<source_id>.txt)."""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tracker.core import Store, run  # noqa: E402
from tracker.parsers import parse_ercot_docs, parse_gov_news, parse_puct_filings, parse_rss  # noqa: E402
from tracker.report import render  # noqa: E402
from tracker.sources import SOURCES  # noqa: E402

FIX = ROOT / "tests" / "fixtures"
TODAY = date(2026, 10, 6)
NOW = datetime(2026, 10, 6, 17, 0, tzinfo=timezone.utc)


def page(name: str) -> str:
    return (FIX / f"{name}.txt").read_text(encoding="utf-8", errors="replace")


def drop_puct_item(body: str, number: int) -> str:
    row = re.compile(r"<tr\b[^>]*>(?:(?!</tr>).)*?itemNumber=%d\"(?:(?!</tr>).)*?</tr>" % number, re.S)
    trimmed, n = row.subn("", body)
    assert n == 1, f"expected to remove exactly one row, removed {n}"
    return trimmed


class ParserTests(unittest.TestCase):
    def test_ercot_documents_take_their_date_from_the_path(self):
        items = parse_ercot_docs(page("ercot_large_load"), SOURCES[0].url)
        self.assertGreaterEqual(len(items), 20)
        guide = [i for i in items if "Verification RFI User Guide" in str(i["title"])]
        self.assertEqual(guide[0]["date"], "2026-09-11")
        self.assertTrue(all(str(i["url"]).startswith("https://www.ercot.com/files/docs/") for i in items))

    def test_puct_filings_include_the_adopted_rule(self):
        items = parse_puct_filings(page("puct_58481"), "https://interchange.puc.texas.gov/Search/Filings?ControlNumber=58481", "58481")
        self.assertEqual(len(items), 219)
        order = next(i for i in items if i["key"] == "58481:218")
        self.assertIn("ORDER ADOPTING NEW 16 TAC §25.194", order["title"])
        self.assertEqual(order["date"], "2026-09-18")
        self.assertTrue(str(order["url"]).startswith("https://interchange.puc.texas.gov/search/documents/"))
        self.assertIn("itemNumber=218", order["url"])

    def test_gov_news_urls_are_absolute_and_dates_never_in_the_future(self):
        items = parse_gov_news(page("gov_news"), "https://gov.texas.gov/news", TODAY)
        self.assertGreaterEqual(len(items), 5)
        self.assertTrue(all(str(i["url"]).startswith("https://gov.texas.gov/news/post/") for i in items))
        dated = [i for i in items if i["date"]]
        self.assertTrue(dated)
        self.assertTrue(all(str(i["date"]) <= TODAY.isoformat() for i in dated))

    def test_rss_items_have_iso_dates_and_publishers(self):
        items = parse_rss(page("news_batch_zero"))
        self.assertGreaterEqual(len(items), 10)
        self.assertTrue(all(len(str(i["date"])) == 10 for i in items if i["date"]))
        self.assertTrue(any(i["extra"]["publisher"] for i in items))


class RunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.fx = self.tmp / "fixtures"
        shutil.copytree(FIX, self.fx)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_first_run_is_a_baseline_and_later_runs_report_only_new_items(self):
        full = (self.fx / "puct_58481.txt").read_text(encoding="utf-8")
        (self.fx / "puct_58481.txt").write_text(drop_puct_item(full, 219), encoding="utf-8")
        first = run(self.tmp, fixtures=self.fx, now=NOW)
        self.assertEqual(first.failures, [])
        self.assertEqual(first.fresh, [])
        self.assertEqual(sorted(first.first_run_sources), sorted(s.id for s in SOURCES))
        (self.fx / "puct_58481.txt").write_text(full, encoding="utf-8")
        second = run(self.tmp, fixtures=self.fx, now=NOW)
        self.assertEqual([i["key"] for i in second.fresh], ["58481:219"])
        self.assertEqual(second.first_run_sources, [])
        third = run(self.tmp, fixtures=self.fx, now=NOW)
        self.assertEqual(third.fresh, [])

    def test_blocked_source_fails_loudly_and_keeps_its_state(self):
        (self.fx / "ercot_large_load.txt").write_text("HTTP 403", encoding="utf-8")
        res = run(self.tmp, fixtures=self.fx, now=NOW)
        status = {h["source"]: h["status"] for h in res.health}
        self.assertEqual(status["ercot_large_load"], "blocked")
        self.assertNotIn("ercot_large_load", Store(self.tmp).load_seen())
        (self.fx / "ercot_large_load.txt").write_text(page("ercot_large_load"), encoding="utf-8")
        retry = run(self.tmp, fixtures=self.fx, now=NOW)
        self.assertIn("ercot_large_load", retry.first_run_sources)   # baseline, not a flood of "new"
        self.assertEqual(retry.fresh, [])

    def test_a_page_that_parses_to_nothing_is_flagged(self):
        (self.fx / "puct_58317.txt").write_text("<html><body>Down for maintenance</body></html>", encoding="utf-8")
        res = run(self.tmp, fixtures=self.fx, now=NOW)
        h = next(h for h in res.health if h["source"] == "puct_58317")
        self.assertEqual(h["status"], "suspect_empty")
        self.assertNotIn("puct_58317", Store(self.tmp).load_seen())

    def test_governor_items_are_keyword_filtered(self):
        res = run(self.tmp, fixtures=self.fx, now=NOW)
        gov_source = next(s for s in SOURCES if s.id == "gov_news")
        pats = [re.compile(k) for k in gov_source.keywords]
        gov = [i for i in res.recorded if i["source"] == "gov_news"]
        self.assertTrue(all(any(p.search(i["title"].lower()) for p in pats) for i in gov))

    def test_report_has_milestones_and_source_health(self):
        text = render(run(self.tmp, fixtures=self.fx, now=NOW))
        self.assertIn("## Milestones", text)
        self.assertIn("Dec 10, 2026 | in 65 days", text)
        self.assertIn("## Source health", text)

    def test_cli_writes_reports_and_returns_2_on_failure(self):
        ok = subprocess.run([sys.executable, str(ROOT / "track.py"), "--root", str(self.tmp), "run",
                             "--fixtures", str(self.fx)], capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        self.assertTrue((self.tmp / "reports" / "latest.md").exists())
        (self.fx / "gov_news.txt").write_text("HTTP 500", encoding="utf-8")
        bad = subprocess.run([sys.executable, str(ROOT / "track.py"), "--root", str(self.tmp), "run",
                              "--fixtures", str(self.fx)], capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2, bad.stdout + bad.stderr)
        self.assertIn("FAILED gov_news", bad.stdout)


if __name__ == "__main__":
    unittest.main()
