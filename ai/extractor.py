import json
import anthropic
from config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are a deal extractor for a local food deal finder app.

You will receive a Reddit post that has been identified as a potential food deal. Extract the deal details and return them as a JSON object with exactly these fields:

{
  "is_deal": true or false,
  "business_name": "name of the restaurant or food business, or null if unknown",
  "deal_description": "plain English description of the deal",
  "location": "city or neighbourhood if mentioned, or null",
  "urgency": "limited_time or ongoing or unknown"
}

Rules:
- is_deal should be false only if on closer reading this is not actually a food deal or affordable food recommendation
- business_name should be null if no specific business is named
- deal_description should be 1-2 sentences max, plain English
- location should be null if not mentioned
- urgency is limited_time if the deal has an end date or says today only / this week etc, ongoing if it is a permanent menu item or loyalty program, unknown if unclear
- Return only the JSON object, no explanation"""


def extract_post(post: dict) -> dict | None:
    text = f"Title: {post['title']}\n\nBody: {post['body']}"
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": text}],
        system=SYSTEM_PROMPT,
    )
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


def extract_posts(posts: list[dict]) -> list[dict]:
    results = []
    for post in posts:
        result = extract_post(post)
        if result and result.get("is_deal"):
            results.append(result)
            print(f"[extractor] extracted — {result.get('business_name', 'Unknown')} | {result.get('deal_description', '')[:60]}")
        else:
            print(f"[extractor] skipped — {post['title'][:60]}")
    print(f"[extractor] {len(results)} deals extracted")
    return results
