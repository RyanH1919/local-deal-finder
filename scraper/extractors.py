"""Extraction strategies and the dispatch that routes a page to them.

Tiers, cheapest first:
  1. JSON-LD / schema.org structured data  — precise, free, often present
  2. structure-preserving HTML text         — keeps menus/price tables legible for the AI
  3. (hooks) SPA render / PDF / image-vision — detected & counted now, built in Phase 2

`extract_deals(ctx)` picks the right tier(s) for a classified page and returns
`(deals, outcome)`, where `outcome` is a label for the coverage metrics.
"""

import json

from .types import DealText, PageContext, PageType

# A page/link "smells like" a deal if it mentions any of these.
DEAL_KEYWORDS = {
    "deal", "deals", "special", "specials", "offer", "offers",
    "promo", "promotion", "promotions", "discount", "coupon",
    "happy-hour", "happyhour", "happy hour", "savings", "sale",
    "bogo", "combo", "bundle", "% off", "percent off",
}

# Links worth following even without the word "deal" — specials often live on
# menu / events / happy-hour pages.
_NAV_KEYWORDS = {
    "menu", "menus", "special", "specials", "offer", "offers", "deal", "deals",
    "event", "events", "happy-hour", "happyhour", "promo", "promotions",
    "lunch", "dinner", "brunch", "catering", "whats-on",
}

# Tags that never carry deal content — removed before reading text.
_BOILERPLATE_TAGS = ("script", "style", "nav", "footer", "header",
                     "meta", "noscript", "svg", "form", "aside")

# schema.org keys that indicate offers/pricing we care about.
_PRICEY_KEYS = ("price", "lowprice", "highprice", "pricerange",
                "pricecurrency", "discount")

_MAX_BODY = 5000   # cap text sent downstream (cost control)


def _has_deal_signal(text: str, href: str = "") -> bool:
    combined = (text + " " + href).lower()
    return any(kw in combined for kw in DEAL_KEYWORDS)


def should_follow_link(text: str, href: str = "") -> bool:
    combined = (text + " " + href).lower()
    return any(kw in combined for kw in _NAV_KEYWORDS)


def _page_title(soup, fallback: str) -> str:
    if soup is not None and soup.title and soup.title.string:
        return soup.title.string.strip()
    return fallback


# --------------------------------------------------------------------------- #
# Tier 1 — JSON-LD / schema.org
# --------------------------------------------------------------------------- #

def extract_jsonld(ctx: PageContext) -> list:
    """Pull schema.org Offer/Menu/Event/price data from <script type=ld+json>.

    Far more reliable than scraping rendered text when present — and it's commonly
    embedded even on JS-heavy sites, so it can rescue some SPA shells for free.
    """
    soup = ctx.soup
    if soup is None:
        return []

    lines = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = tag.string or tag.get_text()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            continue
        _walk_jsonld(data, lines)

    # de-dupe, preserve order
    seen, uniq = set(), []
    for ln in lines:
        if ln not in seen:
            seen.add(ln)
            uniq.append(ln)
    if not uniq:
        return []

    body = "structured data:\n" + "\n".join(uniq)
    return [DealText(title=f"{ctx.business_name} — structured data",
                     body=body[:_MAX_BODY], source_url=ctx.url)]


def _walk_jsonld(node, out: list):
    """Recursively collect readable name/description/price lines from JSON-LD."""
    if isinstance(node, list):
        for item in node:
            _walk_jsonld(item, out)
        return
    if not isinstance(node, dict):
        return

    lower = {str(k).lower(): v for k, v in node.items()}
    name = lower.get("name")
    desc = lower.get("description")
    has_price = any(k in lower for k in _PRICEY_KEYS) or "offers" in lower

    if isinstance(name, str) and (has_price or isinstance(desc, str)):
        bits = [name.strip()]
        if isinstance(desc, str) and desc.strip():
            bits.append(desc.strip())
        price = lower.get("price") or lower.get("lowprice")
        if price is not None:
            bits.append(f"{price} {lower.get('pricecurrency', '')}".strip())
        line = " — ".join(b for b in bits if b)
        if line:
            out.append(line)

    # recurse into nested offers / menus / items
    for value in node.values():
        if isinstance(value, (list, dict)):
            _walk_jsonld(value, out)


# --------------------------------------------------------------------------- #
# Tier 2 — structure-preserving HTML text
# --------------------------------------------------------------------------- #

_BLOCK_TAGS = ["h1", "h2", "h3", "h4", "h5", "li", "p", "tr", "blockquote", "dd", "dt"]


def extract_html_text(ctx: PageContext) -> list:
    """Readable text that keeps block structure (headings, list items, table rows),
    so a menu or price table survives instead of collapsing into one line. Only
    returns a result when the page actually shows a deal signal.
    """
    if ctx.soup is None or not ctx.html:
        return []

    # Work on a fresh copy so stripping boilerplate doesn't mutate ctx.soup
    # (the orchestrator still needs the original for link discovery).
    from .fetch import make_soup
    work = make_soup(ctx.html)
    for tag in work(_BOILERPLATE_TAGS):
        tag.decompose()

    text = _structured_text(work)
    if not _has_deal_signal(text):
        return []

    title = _page_title(ctx.soup, ctx.business_name)
    return [DealText(title=f"{ctx.business_name} — {title}",
                     body=text[:_MAX_BODY], source_url=ctx.url)]


def _structured_text(soup) -> str:
    """One line per leaf block element; table rows become 'cell | cell | cell'."""
    lines, seen = [], set()
    for el in soup.find_all(_BLOCK_TAGS):
        if el.find(_BLOCK_TAGS):
            continue  # container block — its children carry the text
        if el.name == "tr":
            cells = [c.get_text(" ", strip=True) for c in el.find_all(["td", "th"])]
            line = " | ".join(c for c in cells if c)
        else:
            line = el.get_text(" ", strip=True)
            if el.name == "li" and line:
                line = f"- {line}"
        if line and line not in seen:
            seen.add(line)
            lines.append(line)

    if not lines:  # no recognizable structure — fall back to a flat dump
        return " ".join(soup.stripped_strings)
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Tier 3 — escalation hooks (detected & counted now; built in Phase 2)
# --------------------------------------------------------------------------- #

def render_spa(ctx: PageContext) -> list:
    """Render a JS single-page app with a headless browser, then re-extract.

    Uses Playwright when it's installed (`pip install playwright` then
    `playwright install chromium`). If it isn't, returns [] so the pipeline
    degrades gracefully and the 'needs_render' metric still flags the page.
    """
    html = _render_html(ctx.url)
    if not html:
        return []
    from .fetch import make_soup
    rctx = PageContext(url=ctx.url, business_name=ctx.business_name, status=200,
                       content_type="text/html", html=html, soup=make_soup(html),
                       page_type=PageType.STATIC_HTML)
    return _merge_page(_dedupe(extract_jsonld(rctx) + extract_html_text(rctx)), rctx)


def _render_html(url: str):
    """Fully-rendered HTML via a headless browser, or None if unavailable/failed."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None   # Playwright not installed — caller degrades gracefully
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=15000)
                return page.content()
            finally:
                browser.close()
    except Exception as e:
        print(f"[scraper] render failed for {url}: {e}")
        return None


def extract_pdf(ctx: PageContext) -> list:
    """HOOK: extract text from a linked PDF menu (e.g. via pypdf). Phase 2.
    The 'needs_pdf' metric measures demand before we add the dependency.
    """
    return []


def extract_image(ctx: PageContext) -> list:
    """HOOK: read an image flyer via Claude vision (multimodal). Phase 2.
    Claude can interpret a flyer directly; gate behind cost controls. The
    'needs_vision' metric counts how often deals are locked inside images.
    """
    return []


# --------------------------------------------------------------------------- #
# Dispatch
# --------------------------------------------------------------------------- #

def extract_deals(ctx: PageContext):
    """Route a classified page to the right extractor(s).

    Returns `(deals, outcome)` where `outcome` is a coverage-metric label.
    """
    pt = ctx.page_type

    if pt == PageType.STATIC_HTML:
        deals = _merge_page(_dedupe(extract_jsonld(ctx) + extract_html_text(ctx)), ctx)
        return deals, ("deal_page" if deals else "no_signal")

    if pt == PageType.SPA:
        # JSON-LD is often present in the shell before JS runs — try it for free.
        deals = extract_jsonld(ctx)
        if deals:
            return deals, "deal_page_jsonld"
        rendered = render_spa(ctx)
        if rendered:
            return rendered, "deal_page_rendered"
        return [], "needs_render"

    if pt == PageType.PDF:
        return extract_pdf(ctx), "needs_pdf"

    if pt == PageType.IMAGE:
        return extract_image(ctx), "needs_vision"

    if pt == PageType.NON_HTML:
        return [], "non_html"

    return [], "error"


def _dedupe(deals: list) -> list:
    seen, out = set(), []
    for d in deals:
        if d.body and d.body not in seen:
            seen.add(d.body)
            out.append(d)
    return out


def _merge_page(deals: list, ctx: PageContext) -> list:
    """Collapse all extractions from one page into a single post.

    JSON-LD and the HTML text can each yield a deal for the same URL; emitting
    them separately would double the AI calls and collide on source_url in the DB.
    One page -> one post (combined body, one source_url).
    """
    if len(deals) <= 1:
        return deals
    body = "\n\n".join(d.body for d in deals)
    return [DealText(title=deals[-1].title, body=body[:_MAX_BODY], source_url=ctx.url)]
