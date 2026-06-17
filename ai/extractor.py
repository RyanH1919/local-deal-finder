import json
from typing import Optional
import anthropic
from config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

_total_input_tokens = 0
_total_output_tokens = 0

SYSTEM_PROMPT = """You are a deal extractor for a local deal finder app.

You are a deal extractor for a local deal finder app. Extract deal details from a post and return a JSON object with exactly these fields:

{
  "is_deal": true or false,
  "category": "one of: food, grocery, electronics, services, clothing, software, other",
  "business_name": "name of the business, or null if unknown",
  "deal_description": "1-2 sentence plain English description focused on WHAT the deal is, not background context",
  "price_deal": "the deal price as a string (e.g. '$8.95', '$25', 'from $13.95', '2 for $20') or null if no specific price mentioned",
  "price_original": "the regular/was price if stated (e.g. '$35.00') or null",
  "discount_label": "short savings summary if calculable or stated (e.g. '50% off', 'BOGO', 'save $10', '$5 off') or null",
  "min_spend": "minimum purchase required to unlock the deal (e.g. '$50 minimum') or null",
  "location": "city or neighbourhood if mentioned, or null",
  "urgency": "limited_time or ongoing or unknown",
  "expires": "expiry date or time window as a short string if mentioned (e.g. 'ends Sunday', 'Mon-Fri until 10am') or null"
}

Rules:
- is_deal: false only if on closer reading this is not actually a deal
- category: 'food' for restaurants/cafes/food trucks, 'grocery' for supermarkets/raw ingredients, 'electronics' for tech/gadgets, 'services' for dental/medical/professional, 'clothing' for apparel, 'software' for apps/subscriptions, 'other' for anything else
- price_deal: capture the actual price you pay. For ranges use 'from $X' or '$X-$Y'
- price_original: only fill if the original price is explicitly stated — do not estimate
- discount_label: derive from the text. If post says '50% off' use that. If post says was $20 now $10, use 'save $10 (50% off)'
- deal_description: focus on the deal terms — what you get and for how much. Omit backstory
- urgency: limited_time if end date/today only/this week; ongoing if permanent menu item or loyalty program; unknown if unclear
- Return only the JSON object, no explanation"""


def extract_post(post: dict, use_haiku: bool = False) -> Optional[dict]:
    global _total_input_tokens, _total_output_tokens
    text = f"Title: {post['title']}\n\nBody: {post['body']}"
    model = "claude-haiku-4-5-20251001" if use_haiku else "claude-sonnet-4-6"
    message = client.messages.create(
        model=model,
        max_tokens=400,
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
        extracted["source_url"] = post["source_url"]
        extracted["subreddit"] = post["subreddit"]
        extracted["posted_at"] = post["posted_at"]
        return extracted
    except json.JSONDecodeError:
        print(f"[extractor] failed to parse JSON for: {post['title'][:60]}")
        return None


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
