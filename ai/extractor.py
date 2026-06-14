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

You will receive text scraped from a local business's own website. Decide whether the page is advertising a genuine customer deal (a discount, promotion, special, coupon, combo, limited-time offer, etc.) and extract it. Return a JSON object with exactly these fields:

{
  "is_deal": true or false,
  "category": "one of: food, grocery, electronics, services, clothing, software, other",
  "deal_description": "plain English description of the deal, 1-2 sentences",
  "urgency": "limited_time or ongoing or unknown",
  "scope": "local or online"
}

Rules:
- is_deal is false if the page is just a menu, hours, an about page, or general info with no actual deal or promotion.
- category: classify the business/deal into one of the seven buckets. Use 'food' for restaurants/cafes/takeout.
- deal_description: 1-2 sentences, plain English, no marketing fluff. If is_deal is false, briefly say what the page is instead.
- urgency: limited_time if there's an end date or "this week / today only" language; ongoing for permanent specials or loyalty programs; unknown if unclear.
- scope: default to 'local' since this is a nearby business. Only use 'online' if the deal is clearly online-only or a national/chain-wide online promo (order-online-only, a promo code for the website).
- Return only the JSON object, no explanation."""


def extract_website_deal(post: dict, business_name: str, location: str,
                         lat, lng, domain: str, content_hash: str,
                         use_haiku: bool = True) -> dict:
    """
    Flow 2 (Phase 2): turn raw scraped website text into a clean deal via Haiku.

    business_name / location / lat / lng come from Google Places — we already know
    them, so we don't waste tokens asking the AI. We always return a dict (never
    None): if it isn't a real deal or the AI response can't be parsed, we still
    save a row with ai_processed=False so the content_hash is stored and we never
    re-AI the same page.
    """
    global _total_input_tokens, _total_output_tokens
    model = "claude-haiku-4-5-20251001" if use_haiku else "claude-sonnet-4-6"

    # Safe defaults — used as-is if the page isn't a deal or parsing fails.
    ai_fields = {
        "is_deal": False,
        "category": "other",
        "deal_description": "(no deal detected on page)",
        "urgency": "unknown",
        "scope": "local",
    }

    try:
        message = client.messages.create(
            model=model,
            max_tokens=300,
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
        "category":         ai_fields.get("category", "other"),
        "scope":            ai_fields.get("scope", "local"),
        "source_type":      "website",
        "source_name":      domain,
        "location":         location,
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
