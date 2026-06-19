"""Offline test suite for Flow 2 (scraper + grid crawl + retrieval + peer pricing).

Runs without API keys or network: `config` is stubbed, the DB is a temp file, and
Google Places / the headless render / the AI are monkeypatched.

    python tests/test_flow2.py
"""

import os
import sys
import json
import types
import tempfile
import sqlite3

# Make the repo root importable, then stub config BEFORE importing project modules.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_TMP = os.path.join(tempfile.gettempdir(), "ldf_test_flow2.db")
if os.path.exists(_TMP):
    try:
        os.remove(_TMP)
    except OSError:
        pass
_cfg = types.ModuleType("config")
_cfg.DATABASE_PATH = _TMP
_cfg.ANTHROPIC_API_KEY = "test"
_cfg.GOOGLE_API_KEY = "test"
sys.modules["config"] = _cfg

from scraper.types import PageContext, PageType            # noqa: E402
from scraper.fetch import make_soup                         # noqa: E402
from scraper.classify import classify                       # noqa: E402
from scraper import extractors as SE                         # noqa: E402
from crawl import grid                                       # noqa: E402
from crawl.compare import annotate_peer_savings              # noqa: E402
import database.db as db                                     # noqa: E402
from crawl import catalogue as CAT                           # noqa: E402
import search.places as places                               # noqa: E402

_PASSED = []


def _ok(msg):
    _PASSED.append(msg)
    print("  ok  -", msg)


def _cols(table):
    c = sqlite3.connect(_TMP)
    try:
        return {r[1] for r in c.execute(f"PRAGMA table_info({table})")}
    finally:
        c.close()


def test_grid():
    assert grid.geohash_encode(57.64911, 10.40744, 11) == "u4pruydqqvj"
    cell = grid.cell_for_point(43.70, -79.40)
    assert grid.cell_id(cell["lat"], cell["lng"]) == cell["cell_id"]
    assert 100 < cell["radius_m"] < 2000
    assert len(grid.iter_cells((43.70, -79.42, 43.72, -79.40))) > 1
    _ok("grid: geohash vector, cell_for_point, iter_cells")


def test_classify():
    def ctx(url, html, ct="text/html"):
        c = PageContext(url=url, content_type=ct, html=html,
                        soup=make_soup(html) if ("html" in ct or not ct) else None)
        c.page_type = classify(c)
        return c
    big = "<html><body><h1>Menu</h1><p>" + ("food " * 60) + "</p></body></html>"
    assert ctx("/m", big).page_type == PageType.STATIC_HTML
    spa = '<html><head><script src="react.js"></script></head><body><div id="root"></div></body></html>'
    assert ctx("/", spa).page_type == PageType.SPA
    assert classify(PageContext(url="/x.pdf", content_type="application/pdf")) == PageType.PDF
    assert classify(PageContext(url="/i", content_type="image/png")) == PageType.IMAGE
    _ok("classify: static / spa / pdf / image")


def test_extractors():
    html = ('<html><head><title>Deals</title><script type="application/ld+json">'
            '{"@type":"Offer","name":"Combo","price":"9.99","priceCurrency":"CAD"}</script></head>'
            '<body><nav><a href="/">Home</a></nav><h2>Specials</h2>'
            '<ul><li>2-for-1 pizza deal Tuesdays</li></ul><footer>copyright</footer></body></html>')
    c = PageContext(url="https://x.example/deals", business_name="X", content_type="text/html",
                    html=html, soup=make_soup(html))
    c.page_type = classify(c)
    deals, outcome = SE.extract_deals(c)
    assert outcome == "deal_page" and len(deals) == 1                       # merged into one post
    assert "Combo" in deals[0].body and "2-for-1" in deals[0].body and "copyright" not in deals[0].body

    spa = '<html><head><script src="a.js"></script></head><body><div id="root"></div></body></html>'
    sc = PageContext(url="https://s.example/", business_name="S", content_type="text/html",
                     html=spa, soup=make_soup(spa))
    sc.page_type = classify(sc)
    SE._render_html = lambda u: None
    assert SE.extract_deals(sc) == ([], "needs_render")
    SE._render_html = lambda u: '<html><body><h2>Specials</h2><ul><li>Combo $15 deal</li></ul></body></html>'
    d2, o2 = SE.extract_deals(sc)
    assert o2 == "deal_page_rendered" and d2 and "Combo" in d2[0].body
    _ok("extractors: jsonld+html merged, boilerplate stripped, render_spa fallback")


def test_db_roundtrip():
    # An old-schema deals table (missing newer columns) must self-heal on init_db.
    c = sqlite3.connect(_TMP)
    c.execute("CREATE TABLE deals (id INTEGER PRIMARY KEY AUTOINCREMENT, business_name TEXT, "
              "deal_description TEXT NOT NULL, location TEXT, source_url TEXT NOT NULL UNIQUE, "
              "urgency TEXT, is_expired BOOLEAN, category TEXT)")
    c.commit()
    c.close()
    db.init_db()
    assert {"content_hash", "price_deal", "discount_label", "products", "geohash",
            "scope", "ai_processed"} <= _cols("deals")

    deal = {"business_name": "Joe", "deal_description": "pizza", "price_deal": "$10",
            "discount_label": None, "products": json.dumps([{"name": "Large", "price": "$10"}]),
            "category": "food", "scope": "local", "source_type": "website", "source_name": "joe.ca",
            "location": "TO", "lat": 43.7, "lng": -79.4, "source_url": "https://joe.ca/d",
            "subreddit": None, "posted_at": None, "urgency": "ongoing", "content_hash": "h",
            "ai_processed": True, "geohash": "dpz2u9"}
    db.save_deals([deal])
    got = [r for r in db.get_active_deals() if r["source_url"] == "https://joe.ca/d"][0]
    assert json.loads(got["products"])[0]["price"] == "$10" and got["geohash"] == "dpz2u9"
    assert any(r["source_url"] == "https://joe.ca/d" for r in db.get_deals_in_cell("dpz2u9"))
    assert any(r["source_url"] == "https://joe.ca/d" for r in db.get_deals_in_cell("dpz2"))   # prefix
    assert not db.get_deals_in_cell("zzzz")
    _ok("db: migration, products+geohash round-trip, get_deals_in_cell (exact+prefix)")


def test_compare():
    mk = lambda b, cat, prods: {"business_name": b, "category": cat, "price_deal": None,
                                "products": json.dumps(prods)}
    out = annotate_peer_savings([
        mk("A", "food", [{"name": "Large Pizza", "price": "$20"}]),
        mk("B", "food", [{"name": "Large Pizza", "price": "$24"}]),
        mk("C", "food", [{"name": "Large Pizza", "price": "$28"}]),
        mk("D", "electronics", [{"name": "Case", "price": "$10"}]),   # lone in category
    ])
    by = {d["business_name"]: d for d in out}
    assert "below" in (by["A"]["vs_peers"] or "")
    assert "above" in (by["C"]["vs_peers"] or "")
    assert by["D"]["vs_peers"] is None
    assert "below" in (json.loads(by["A"]["products"])[0]["vs_peers"] or "")
    _ok("compare: peer below/above + no-peer fallback")


def test_places_pagination():
    class _R:
        def __init__(self, p):
            self._p = p

        def raise_for_status(self):
            pass

        def json(self):
            return self._p

    biz = lambda n, la, lo, pid: {"name": n, "vicinity": "x", "place_id": pid,
                                  "geometry": {"location": {"lat": la, "lng": lo}}}
    calls = {"n": 0}

    def fake(url, params=None, timeout=None):
        calls["n"] += 1
        if "pagetoken" in (params or {}):
            return _R({"status": "OK", "results": [biz("C", 43.72, -79.42, "3"), biz("D", 43.73, -79.43, "4")]})
        return _R({"status": "OK", "next_page_token": "T",
                   "results": [biz("A", 43.70, -79.40, "1"), biz("B", 43.71, -79.41, "2")]})

    places.requests.get = fake
    places.time = types.SimpleNamespace(sleep=lambda *a, **k: None)
    res = places.find_nearby(43.70, -79.40, "pizza", radius_m=1000)
    assert len(res) == 4 and calls["n"] == 2
    _ok("places: pagination across 2 pages")


def test_crawl_cell():
    found = [{"name": "Biz1", "address": "1", "lat": 43.7, "lng": -79.4, "place_id": "p1",
              "rating": 4.5, "distance_m": 100, "distance_label": "100m"},
             {"name": "Biz2", "address": "2", "lat": 43.71, "lng": -79.41, "place_id": "p2",
              "rating": 4.0, "distance_m": 200, "distance_label": "200m"}]
    CAT.find_nearby = lambda lat, lng, item, radius_m=None: list(found)
    CAT.get_place_website = lambda pid: "https://biz1.example" if pid == "p1" else None
    CAT.scrape_business_website = lambda website, name, metrics=None: [
        {"title": "t", "body": "deal", "source_url": website + "/d", "subreddit": "website", "posted_at": None}]
    CAT.extract_website_deal = lambda post, business_name, location, lat, lng, domain, content_hash, use_haiku=True: {
        "business_name": business_name, "deal_description": "$10 pizza", "price_deal": "$10",
        "discount_label": None, "products": json.dumps([{"name": "Large", "price": "$10"}]),
        "category": "food", "scope": "local", "source_type": "website", "source_name": domain,
        "location": location, "lat": lat, "lng": lng, "source_url": post["source_url"],
        "subreddit": None, "posted_at": None, "urgency": "ongoing", "content_hash": content_hash,
        "ai_processed": True}
    res = CAT.crawl_cell(43.70, -79.40, categories=["pizza"], force=True)
    assert (res["businesses"], res["scraped"], res["deals"]) == (2, 1, 1)
    assert res["deals_per_business"] == 1.0
    _ok("crawl_cell: discover/scrape/extract/save + yield metrics (mocked)")


if __name__ == "__main__":
    for t in (test_grid, test_classify, test_extractors, test_db_roundtrip,
              test_compare, test_places_pagination, test_crawl_cell):
        t()
    try:
        os.remove(_TMP)
    except OSError:
        pass
    print(f"\nALL {len(_PASSED)} FLOW 2 CHECKS PASSED")
