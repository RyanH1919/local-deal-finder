"""Yield metrics for a Flow 2 cell crawl.

Answers "how productive was this crawl?" — deals found per scraped business and per
query (category) — so we can see which categories and areas are worth crawling.
"""


class CrawlMetrics:
    def __init__(self, cell_id: str = ""):
        self.cell_id = cell_id
        self.businesses = 0          # distinct businesses discovered in the cell
        self.scraped = 0             # had a website and were scraped this run
        self.cached = 0              # skipped: recently scraped, or no website
        self.deals = 0               # real deals found (ai_processed)
        self.by_category = {}        # category -> {"found": int, "deals": int}

    def _cat(self, category: str) -> dict:
        return self.by_category.setdefault(category, {"found": 0, "deals": 0})

    def record_query(self, category: str, found: int):
        self._cat(category)["found"] += found

    def set_businesses(self, n: int):
        self.businesses = n

    def record_scraped(self):
        self.scraped += 1

    def record_cached(self):
        self.cached += 1

    def record_deal(self, category: str):
        self.deals += 1
        self._cat(category)["deals"] += 1

    def deals_per_business(self) -> float:
        return round(self.deals / self.scraped, 2) if self.scraped else 0.0

    def as_dict(self) -> dict:
        return {
            "businesses": self.businesses,
            "scraped": self.scraped,
            "cached": self.cached,
            "deals": self.deals,
            "deals_per_business": self.deals_per_business(),
            "by_category": self.by_category,
        }

    def summary(self) -> str:
        lines = [
            f"[yield] cell {self.cell_id} — {self.businesses} businesses "
            f"({self.scraped} scraped, {self.cached} skipped), {self.deals} deals",
            f"[yield]   deals per scraped business: {self.deals_per_business()}",
        ]
        for cat, c in self.by_category.items():
            found = c["found"]
            rate = round(c["deals"] / found, 2) if found else 0.0
            lines.append(f"[yield]   {cat}: {c['deals']} deals / {found} found ({rate} per result)")
        return "\n".join(lines)
