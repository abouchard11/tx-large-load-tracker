"""Sources and milestones. Everything here is public; this repo holds no credentials."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple
from urllib.parse import quote_plus

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
      "tx-large-load-tracker/0.1 (+https://midnightdev.dev)")


def google_news(query: str) -> str:
    return ("https://news.google.com/rss/search?q=" + quote_plus(query)
            + "&hl=en-US&gl=US&ceid=US:en")


@dataclass(frozen=True)
class Source:
    id: str
    kind: str                  # ercot_docs | puct_filings | gov_news | rss
    url: str
    label: str
    min_items: int             # fewer parsed items than this means the page changed or we got junk
    keywords: Tuple[str, ...] = ()   # optional regexes matched against the lowercased title
    project: Optional[str] = None    # PUCT control number
    fresh_days: Optional[int] = None  # first sightings dated older than this are recorded quietly


SOURCES: Tuple[Source, ...] = (
    Source("ercot_large_load", "ercot_docs",
           "https://www.ercot.com/services/rq/large-load-integration",
           "ERCOT · Large Load Integration documents", min_items=10),
    Source("puct_58481", "puct_filings",
           "https://interchange.puc.texas.gov/Search/Filings?ControlNumber=58481",
           "PUCT 58481 · large-load interconnection standards (16 TAC §25.194)",
           min_items=50, project="58481"),
    Source("puct_58317", "puct_filings",
           "https://interchange.puc.texas.gov/Search/Filings?ControlNumber=58317",
           "PUCT 58317 · SB 6 implementation", min_items=50, project="58317"),
    Source("gov_news", "gov_news", "https://gov.texas.gov/news",
           "Governor's office · news (filtered)", min_items=5,
           keywords=(r"\bdata cent(?:er|re)s?\b", r"\bercot\b", r"\belectric(?:ity|al)?\b",
                     r"\bgrid\b", r"\bpublic utility\b", r"\bpuc\b", r"\btceq\b",
                     r"\bwater development\b", r"\blarge loads?\b", r"\bpower\b")),
    Source("news_batch_zero", "rss", google_news('"Batch Zero" ERCOT'),
           "News · ERCOT Batch Zero", min_items=1, fresh_days=10),
    Source("news_tx_dc_policy", "rss",
           google_news('Texas "data center" (audit OR moratorium OR TCEQ OR PUCT)'),
           "News · Texas data-center policy", min_items=1, fresh_days=10),
    Source("news_anthropic_tx", "rss",
           google_news('(Anthropic OR Fluidstack) Texas "data center"'),
           "News · Anthropic / Fluidstack in Texas", min_items=0, fresh_days=10),
)


@dataclass(frozen=True)
class Milestone:
    date: str          # YYYY-MM-DD
    what: str
    source: str
    confidence: str    # "confirmed" = primary document; "reported" = press coverage only


MILESTONES: Tuple[Milestone, ...] = (
    Milestone("2026-10-08", "16 TAC §25.194 (large-load interconnection standards) takes effect",
              "PUCT Project 58481, items 218-219", "confirmed"),
    Milestone("2026-10-19", "TCEQ compliance report due to the governor on the data-center permit pause",
              "White & Case, Sept 25, 2026 (governor's Sept 21 letter)", "reported"),
    Milestone("2026-12-10", "ERCOT files Batch Zero verification and community-impact reports with the PUC",
              "San Angelo LIVE!, Sept 15, 2026; White & Case, Sept 25, 2026", "reported"),
    Milestone("2026-12-17", "PUC open meeting expected to take up the audit reports",
              "San Angelo LIVE!, Sept 15, 2026", "reported"),
)
