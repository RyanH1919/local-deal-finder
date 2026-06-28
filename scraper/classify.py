"""Tier 0 — rule-based page classification.

Given a fetched `PageContext`, decide which extraction strategy applies. This is
pure heuristics (no AI, no token cost), matching the Flow 2 decision to keep
classification cheap. The orchestrator routes each `PageType` to its extractor.
"""

from .types import PageContext, PageType

# Image / PDF file extensions we might link to directly.
_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff")

# Mount-point ids frameworks render into — a near-empty <body> with one of these
# is the classic single-page-app shell that plain `requests` can't see into.
_SPA_ROOT_IDS = ("root", "app", "__next", "__nuxt", "q-app", "gatsby-focus-wrapper")
_SPA_HINTS = ("react", "vue", "next", "nuxt", "ng-version", "svelte", "__next_data__")

# Below this many characters of visible text, a 200-OK HTML page is probably an
# unrendered shell rather than real content.
_MIN_TEXT_LEN = 200


def classify(ctx: PageContext) -> PageType:
    """Return the `PageType` for a fetched page."""
    if ctx.page_type == PageType.ERROR:
        return PageType.ERROR

    ct = ctx.content_type
    path = ctx.url.lower().split("?")[0].split("#")[0]

    if "application/pdf" in ct or path.endswith(".pdf"):
        return PageType.PDF
    if ct.startswith("image/") or path.endswith(_IMAGE_EXTS):
        return PageType.IMAGE

    # Server told us a non-HTML type we don't handle — bail early.
    if ct and "html" not in ct and "xml" not in ct:
        return PageType.NON_HTML

    # Otherwise treat as HTML and decide server-rendered vs JS shell.
    if _looks_like_spa(ctx):
        return PageType.SPA
    return PageType.STATIC_HTML


def _looks_like_spa(ctx: PageContext) -> bool:
    """Heuristic: very little visible text *and* a framework mount point/hint."""
    soup = ctx.soup
    if soup is None:
        return False

    if len(" ".join(soup.stripped_strings)) >= _MIN_TEXT_LEN:
        return False  # there's real content — extract it the normal way

    has_root = any(soup.find(id=rid) is not None for rid in _SPA_ROOT_IDS)
    html_lower = (ctx.html or "").lower()
    has_hint = any(h in html_lower for h in _SPA_HINTS)
    return has_root or has_hint
