import anthropic
from config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are a deal classifier for a local food deal finder app.

Your job is to read a Reddit post and decide if it contains a food or restaurant deal.

A deal is defined as: any post promoting a discount, free item, limited time offer, or grand opening tied to a real food business (restaurant, fast food, cafe, bakery, food truck, etc.). Also include posts recommending specific affordable or budget-friendly food options (e.g. "best cheap eats", "hidden gems under $15").

Do NOT classify as yes: grocery store flyers, supermarket weekly sales, Costco price drop reports, or any post about buying raw ingredients at a store.

Respond with exactly one word — no explanation, no punctuation:
- yes — clearly a food/restaurant deal or promotion
- no — not a food deal
- uncertain — could be a food deal but unclear"""


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
        label = classify_post(post)
        if label not in results:
            label = "uncertain"
        results[label].append(post)
        print(f"[classifier] {label.upper()} — {post['title'][:60]}")
    print(f"[classifier] yes={len(results['yes'])} uncertain={len(results['uncertain'])} no={len(results['no'])}")
    return results
