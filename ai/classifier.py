import anthropic
from config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are a deal classifier for a deal finder app covering the Greater Toronto Area (GTA) and Canada.

Your job is to read a Reddit post and decide two things:
1. Is this a real deal?
2. Is it online/Canada-wide, or local/GTA-specific?

A deal is any post that actively shares or promotes a discount, sale, promo code, free item, limited time offer, price drop, or clearly affordable find. All categories count: food, electronics, clothing, home goods, health, entertainment, and more.

Say NO if:
- The post is asking where to find a deal ("does anyone know a good deal on X?")
- There is no specific deal being shared, just general discussion
- The post is someone showing off a purchase at full price

For online vs local:
- online = deal available on a website, app, or Canada-wide (e.g. Amazon, Best Buy Canada, promo codes)
- local = deal tied to a specific physical store or restaurant in the GTA

Respond with exactly one of these labels — no explanation, no punctuation:
- yes_online — clearly a deal, available online or Canada-wide
- yes_local — clearly a deal, tied to a physical GTA location
- uncertain_online — might be a deal, seems online or Canada-wide
- uncertain_local — might be a deal, seems tied to a physical GTA location
- no — not a deal"""


def classify_post(post: dict) -> str:
    text = f"Title: {post['title']}\n\nBody: {post['body']}"
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=10,
        messages=[{"role": "user", "content": text}],
        system=SYSTEM_PROMPT,
    )
    return message.content[0].text.strip().lower()


def classify_posts(posts: list[dict]) -> dict[str, list[dict]]:
    results = {"yes": [], "no": [], "uncertain": []}
    for post in posts:
        raw = classify_post(post)
        parts = raw.split("_", 1)
        label = parts[0]
        scope = parts[1] if len(parts) > 1 else "online"

        if label not in results:
            label = "uncertain"

        results[label].append({**post, "scope": scope})
        print(f"[classifier] {raw.upper()} — {post['title'][:60]}")

    print(f"[classifier] yes={len(results['yes'])} uncertain={len(results['uncertain'])} no={len(results['no'])}")
    return results