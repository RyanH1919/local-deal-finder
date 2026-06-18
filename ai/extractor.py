import json
from typing import Optional
import anthropic
from config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

_total_input_tokens = 0
_total_output_tokens = 0

SYSTEM_PROMPT = """You are a deal extractor for a GTA and Canada deal finder app.

You will receive a Reddit post that has been identified as a potential deal, along with a scope tag (local or online) pre-determined by a classifier. Extract the deal details and return them as a JSON object with exactly these fields:

{
  "is_deal": true or false,
  "category": "one of: food, grocery, electronics, services, clothing, software, other",
  "business_name": "name of the business, or null if unknown",
  "deal_description": "plain English description of the deal",
  "location": "city or neighbourhood if mentioned, or null",
  "urgency": "limited_time or ongoing or unknown"
}

Rules:
- is_deal should be false only if on closer reading this is not actually a deal
- category: use 'food' for restaurants/cafes/food trucks, 'grocery' for supermarkets/raw ingredients, 'electronics' for tech/gadgets, 'services' for dental/medical/professional, 'clothing' for apparel, 'software' for apps/subscriptions, 'other' for anything else
- business_name should be null if no specific business is named
- deal_description should be 1-2 sentences max, plain English
- location: if scope is local, try hard to extract a neighbourhood or city; if scope is online, set to null unless explicitly mentioned
- urgency is limited_time if the deal has an end date or says today only / this week etc, ongoing if it is a permanent menu item or loyalty program, unknown if unclear
- Return only the JSON object, no explanation"""


def extract_post(post: dict, use_haiku: bool = False) -> Optional[dict]:
    global _total_input_tokens, _total_output_tokens
    scope = post.get("scope", "online")
    text = f"Scope: {scope}\n\nTitle: {post['title']}\n\nBody: {post['body']}"
    model = "claude-haiku-4-5-20251001" if use_haiku else "claude-sonnet-4-6"
    message = client.messages.create(
        model=model,
        max_tokens=300,
        messages=[{"role": "user", "content": text}],
        system=SYSTEM_PROMPT,
    )
    _total_input_tokens += message.usage.input_tokens
    _total_output_tokens += message.usage.output_tokens
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        extracted = json.loads(raw.strip())
        extracted["source_url"]   = post["source_url"]
        extracted["subreddit"]    = post["subreddit"]
        extracted["posted_at"]    = post["posted_at"]
        extracted["scope"]        = scope
        extracted["source_type"]  = "social"
        extracted["source_name"]  = "reddit"
        extracted["ai_processed"] = True
        return extracted
    except json.JSONDecodeError:
        print(f"[extractor] failed to parse JSON for: {post['title'][:60]}")
        return None


def reset_token_counts():
    global _total_input_tokens, _total_output_tokens
    _total_input_tokens = 0
    _total_output_tokens = 0


def get_token_counts() -> tuple[int, int]:
    return _total_input_tokens, _total_output_tokens


WEBSITE_SYSTEM_PROMPT = """You are a deal extractor for a local business deal finder app in the GTA.

You will receive text scraped from a local business's own website. Decide whether the page is advertising a genuine customer deal (a discount, promotion, special, coupon, combo, limited-time offer, etc.) and extract it. We only care about four things: WHAT the deal is, the PRICE, the DISCOUNT, and WHERE. Return a JSON object with exactly these fields:

{
  "is_deal": true or false,
  "category": "one of: food, grocery, electronics, services, clothing, software, other",
  "deal_description": "the deal in ONE tight sentence — what the customer gets. No marketing fluff, no backstory, no hours",
  "price_deal": "the single headline price as a short string (e.g. '$13', 'from $9.99', '2 for $20') or null if no price is shown",
  "discount_label": "the savings as a short string (e.g. '50% off', 'BOGO', 'save $5', '$2 off') or null if not stated or derivable",
  "products": [{"name": "the item or combo", "price": "its price string", "discount": "its savings or null"}],
  "location": "neighbourhood or city if the page states one, or null",
  "urgency": "limited_time or ongoing or unknown",
  "scope": "local or online"
}

Rules:
- is_deal is TRUE whenever the page shows a specific priced offer — a combo, special, "X for $Y", bundle, multi-buy, discount, coupon, happy hour, or a deals/specials/combos menu. Ongoing offers count (a permanent combo is still a deal). Set is_deal false ONLY when there is no pricing and no offer at all (a pure about / contact / hours / generic info page). When false, set price_deal and discount_label to null, products to [], and say what the page is in deal_description.
- Whenever the page shows a price for a combo/deal/special, capture it in price_deal — even if the offer is ongoing rather than time-limited.
- price_deal: capture the real number(s) a customer pays. Keep it short — prices only, not a sentence. null if the page names no price.
- products: when the page lists SEVERAL priced offers (multiple combos, sizes, or specials), return one entry per distinct offer, each with its own name + price (+ discount if any). Use [] if there are none or only one. price_deal stays the single headline price; products is the full list.
- discount_label: derive it when you can. '50% off' -> '50% off'; 'was $20, now $10' -> 'save $10 (50% off)'. null if there's nothing to claim.
- deal_description: ONE sentence describing the offer itself (e.g. 'Large 2-topping pizza for $11.99 on Tuesdays'). Never "welcome to", company history, or opening hours.
- category: classify into one of the seven buckets. Use 'food' for restaurants/cafes/takeout.
- urgency: limited_time if there's an end date or "this week / today only"; ongoing for permanent specials or loyalty programs; unknown if unclear.
- scope: default to 'local' since this is a nearby business. Only use 'online' if the deal is clearly online-only or a national/chain-wide online promo (order-online-only, a promo code for the website).
- Return only the JSON object, no explanation."""


def extract_website_deal(post: dict, business_name: str, location: str,
                         lat, lng, domain: str, content_hash: str,
                         use_haiku: bool = True) -> dict:
    """
    Flow 2: turn raw scraped website text into a clean, structured deal via Haiku.

    business_name / location / lat / lng come from Google Places — we already know
    them, so we don't waste tokens asking the AI. We always return a dict (never
    None): if it isn't a real deal or the AI response can't be parsed, we still
    return a row with ai_processed=False so the content_hash is stored and we never
    re-AI the same page. `products` is a JSON-encoded list of the page's offers.
    """
    global _total_input_tokens, _total_output_tokens
    model = "claude-haiku-4-5-20251001" if use_haiku else "claude-sonnet-4-6"

    # Safe defaults — used as-is if the page isn't a deal or parsing fails.
    ai_fields = {
        "is_deal": False,
        "category": "other",
        "deal_description": "(no deal detected on page)",
        "price_deal": None,
        "discount_label": None,
        "products": [],
        "location": None,
        "urgency": "unknown",
        "scope": "local",
    }

    try:
        message = client.messages.create(
            model=model,
            max_tokens=700,
            messages=[{"role": "user", "content": post["body"]}],
            system=WEBSITE_SYSTEM_PROMPT,
        )
        _total_input_tokens += message.usage.input_tokens
        _total_output_tokens += message.usage.output_tokens
        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        ai_fields.update(json.loads(raw.strip()))
    except (json.JSONDecodeError, KeyError, IndexError):
        print(f"[extractor] failed to parse website deal for: {business_name}")

    is_deal = bool(ai_fields.get("is_deal"))
    return {
        "business_name":    business_name,
        "deal_description": ai_fields.get("deal_description") or "(no description)",
        "price_deal":       ai_fields.get("price_deal"),
        "discount_label":   ai_fields.get("discount_label"),
        # The full list of offers on the page, JSON-encoded for the deals.products column.
        "products":         json.dumps(ai_fields.get("products") or []),
        "category":         ai_fields.get("category", "other"),
        "scope":            ai_fields.get("scope", "local"),
        "source_type":      "website",
        "source_name":      domain,
        # Prefer the precise Places location; fall back to anything the page named.
        "location":         location or ai_fields.get("location"),
        "lat":              lat,
        "lng":              lng,
        "source_url":       post["source_url"],
        "subreddit":        None,
        "posted_at":        None,
        "urgency":          ai_fields.get("urgency", "unknown"),
        "content_hash":     content_hash,
        "ai_processed":     is_deal,
    }


def extract_posts(posts: list[dict], use_haiku: bool = False) -> list[dict]:
    global _total_input_tokens, _total_output_tokens
    _total_input_tokens = 0
    _total_output_tokens = 0
    results = []
    for post in posts:
        result = extract_post(post, use_haiku=use_haiku)
        if result and result.get("is_deal"):
            results.append(result)
            print(f"[extractor] extracted — [{result.get('category', '?')}] {result.get('business_name', 'Unknown')} | {result.get('deal_description', '')[:60]}")
        else:
            print(f"[extractor] skipped — {post['title'][:60]}")
    print(f"[extractor] {len(results)} deals extracted")
    print(f"[extractor] tokens used — input={_total_input_tokens} output={_total_output_tokens}")
    return results
