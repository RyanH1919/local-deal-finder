import anthropic
from config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

_total_input_tokens = 0
_total_output_tokens = 0

BATCH_SIZE = 10

VALID_LABELS = {"yes_online", "yes_local", "uncertain_online", "uncertain_local", "no"}

SYSTEM_PROMPT = """You are a deal classifier for a deal finder app covering the Greater Toronto Area (GTA) and Canada.

Your job is to read posts and decide if each contains a real deal, and whether it is online or local.

A deal is any post that actively shares or promotes a discount, sale, promo code, free item, limited time offer, price drop, or clearly affordable find. All categories count: food, electronics, clothing, home goods, health, entertainment, and more.

Say no if:
- The post is asking where to find a deal
- There is no specific deal being shared, just general discussion
- The post is someone showing off a purchase at full price

For online vs local:
- online = deal available on a website, app, or Canada-wide (e.g. Amazon, Best Buy Canada, promo codes)
- local = deal tied to a specific physical store or restaurant in the GTA

You will receive multiple numbered posts. Respond with one line per post in this exact format:
1. yes_local
2. no
3. uncertain_online

Valid labels: yes_online, yes_local, uncertain_online, uncertain_local, no"""


def _classify_batch(posts: list) -> list:
    global _total_input_tokens, _total_output_tokens
    lines = []
    for i, post in enumerate(posts, 1):
        title = post["title"]
        body = post["body"][:300]
        lines.append(f"{i}. Title: {title}\n   Body: {body}")
    user_content = "\n\n".join(lines)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=BATCH_SIZE * 12,
        messages=[{"role": "user", "content": user_content}],
        system=SYSTEM_PROMPT,
    )
    _total_input_tokens += message.usage.input_tokens
    _total_output_tokens += message.usage.output_tokens
    labels = []
    for line in message.content[0].text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(".", 1)
        if len(parts) == 2:
            label = parts[1].strip().lower()
            if label not in VALID_LABELS:
                label = "uncertain_local"
            labels.append(label)
    while len(labels) < len(posts):
        labels.append("uncertain_local")
    return labels[:len(posts)]


def classify_post(post: dict) -> str:
    return _classify_batch([post])[0]


def classify_posts(posts: list) -> dict:
    global _total_input_tokens, _total_output_tokens
    _total_input_tokens = 0
    _total_output_tokens = 0
    results = {label: [] for label in VALID_LABELS}
    for batch_start in range(0, len(posts), BATCH_SIZE):
        batch = posts[batch_start: batch_start + BATCH_SIZE]
        labels = _classify_batch(batch)
        for post, label in zip(batch, labels):
            scope = label.split("_")[1] if "_" in label else "online"
            results[label].append({**post, "scope": scope})
            print(f"[classifier] {label.upper()} — {post['title'][:60]}")
    yes_count = len(results["yes_local"]) + len(results["yes_online"])
    unc_count = len(results["uncertain_local"]) + len(results["uncertain_online"])
    print(f"[classifier] yes={yes_count} uncertain={unc_count} no={len(results['no'])}")
    print(f"[classifier] tokens used — input={_total_input_tokens} output={_total_output_tokens} (batched {BATCH_SIZE}/call)")
    return results
