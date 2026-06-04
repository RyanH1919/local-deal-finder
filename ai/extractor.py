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
        extracted["source_url"] = post["source_url"]
        extracted["subreddit"] = post["subreddit"]
        extracted["posted_at"] = post["posted_at"]
        extracted["scope"] = scope
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
