// price_deal / product prices are free-form text ("$8.99", "from $10.99").
// Best-effort: first number in the string, commas stripped.
export function parsePrice(text) {
  if (text == null) return null;
  const match = String(text).replace(/,/g, "").match(/(\d+(?:\.\d{1,2})?)/);
  return match ? Number(match[1]) : null;
}

// products is stored as a JSON string server-side; tolerate string, array, or junk.
export function parseProducts(raw) {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw;
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

// Filterable price for a deal: its headline price_deal if present, else the
// cheapest itemized product price. price_deal-first so the number we filter on
// matches the price shown on the card — a $3 side item shouldn't pull a
// "$10–$18" deal into an "Under $10" bucket. (The backend's peer-comparison
// uses cheapest-item as the "entry price"; that's the right metric for peer
// ranking but the wrong one for a user-facing price filter.)
export function dealMinPrice(deal) {
  const headline = parsePrice(deal.price_deal);
  if (headline != null) return headline;
  const productPrices = parseProducts(deal.products)
    .map((p) => parsePrice(p.price))
    .filter((n) => n != null);
  return productPrices.length > 0 ? Math.min(...productPrices) : null;
}

// range format: "min-max", either end empty. Half-open [min, max).
export function inPriceRange(price, range) {
  if (!range) return true;
  if (price == null) return false;
  const [min, max] = range.split("-");
  if (min !== "" && price < Number(min)) return false;
  if (max !== "" && price >= Number(max)) return false;
  return true;
}
