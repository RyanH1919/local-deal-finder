"""Per-run coverage instrumentation for the scraper.

The point is to answer "where are deals being lost?" with numbers instead of
guesses — so any future investment in Tier-3 extractors (headless rendering, PDF,
vision) targets the dominant failure mode rather than a hunch.
"""

from collections import Counter


class ScrapeMetrics:
    """Accumulates per-page outcomes across one crawl run."""

    # outcomes that mean "a Tier-3 extractor would have helped here"
    _TIER3 = ("needs_render", "needs_pdf", "needs_vision")

    def __init__(self):
        self.sites = 0
        self.pages = 0
        self.deal_pages = 0
        self.outcomes = Counter()

    def record_site(self):
        self.sites += 1

    def record_page(self, outcome: str, n_deals: int = 0):
        self.pages += 1
        self.outcomes[outcome] += 1
        if n_deals:
            self.deal_pages += 1

    def as_dict(self) -> dict:
        return {
            "sites": self.sites,
            "pages": self.pages,
            "deal_pages": self.deal_pages,
            "outcomes": dict(self.outcomes),
        }

    def summary(self) -> str:
        lines = [
            f"[scraper] coverage — {self.sites} site(s), {self.pages} page(s), "
            f"{self.deal_pages} deal page(s) found"
        ]
        for outcome, n in self.outcomes.most_common():
            lines.append(f"[scraper]   {outcome}: {n}")
        gaps = {k: self.outcomes[k] for k in self._TIER3 if self.outcomes[k]}
        if gaps:
            lines.append(f"[scraper]   Tier-3 opportunities (Phase 2): {gaps}")
        return "\n".join(lines)
