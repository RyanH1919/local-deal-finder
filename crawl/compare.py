"""Peer comparison for the catalogue.

Scores each deal against the SAME thing at the OTHER businesses in the set — per
business by entry price (robust, always works with >=2 priced businesses) and
per item where sizes match. This is the only data-grounded "saving" for a plain
menu price: precise, from your own crawl, not a vague regional average. Annotates
deals in place (deal['vs_peers'] + products[i]['vs_peers']) and returns them.
"""

import json
import re
import statistics

_SIZES = ("x-large", "xlarge", "extra large", "xl", "large", "medium",
          "small", "party", "regular", "personal")
_MULTI = ("2 ", "two ", "pair", "combo", "bundle", "family", "multi", "3 ", "4 ")


def _price_num(s):
    if s is None:
        return None
    m = re.search(r"(\d+(?:\.\d{1,2})?)", str(s))
    return float(m.group(1)) if m else None


def _size(name):
    n = (name or "").lower()
    for sz in _SIZES:
        if sz in n:
            return sz
    return ""


def _is_single(name):
    n = (name or "").lower()
    return not any(m in n for m in _MULTI)


def _money(x):
    return "$" + f"{x:.2f}".rstrip("0").rstrip(".")


def _baseline(by_biz: dict):
    """(median of each business's price, business count) — or None if < 2 peers."""
    vals = list(by_biz.values())
    return (statistics.median(vals), len(vals)) if len(vals) >= 2 else None


def _phrase(price, base):
    median, n = base
    if median <= 0:
        return None
    pct = round((median - price) / median * 100)
    if pct >= 1:
        return f"~{pct}% below {n - 1} nearby"
    if pct <= -1:
        return f"~{abs(pct)}% above {n - 1} nearby"
    return f"about the same as {n - 1} nearby"


def annotate_peer_savings(deals: list) -> list:
    parsed = []          # (deal, products, min_entry_price)
    by_cat = {}          # category -> {business: min entry price}
    by_item = {}         # (category, size) -> {business: min price}

    for d in deals:
        try:
            prods = json.loads(d.get("products") or "[]")
        except (ValueError, TypeError):
            prods = []
        biz = d.get("business_name")
        cat = d.get("category", "other")
        prices = [p for p in (_price_num(x.get("price")) for x in prods) if p is not None]
        min_price = min(prices) if prices else _price_num(d.get("price_deal"))
        if min_price is not None:
            cur = by_cat.setdefault(cat, {})
            cur[biz] = min(cur.get(biz, min_price), min_price)
        for p in prods:
            price = _price_num(p.get("price"))
            sz = _size(p.get("name"))
            if price is None or not sz or not _is_single(p.get("name")):
                continue
            grp = by_item.setdefault((cat, sz), {})
            grp[biz] = min(grp.get(biz, price), price)
        parsed.append((d, prods, min_price))

    cat_base = {c: _baseline(m) for c, m in by_cat.items()}
    item_base = {k: _baseline(m) for k, m in by_item.items()}

    for d, prods, min_price in parsed:
        d["vs_peers"] = None
        base = cat_base.get(d.get("category", "other"))
        if base and min_price is not None:
            ph = _phrase(min_price, base)
            if ph:
                d["vs_peers"] = f"from {_money(min_price)} — {ph}"
        for p in prods:
            p["vs_peers"] = None
            price = _price_num(p.get("price"))
            sz = _size(p.get("name"))
            if price is None or not sz or not _is_single(p.get("name")):
                continue
            ib = item_base.get((d.get("category", "other"), sz))
            if ib:
                p["vs_peers"] = _phrase(price, ib)
        d["products"] = json.dumps(prods)
    return deals
