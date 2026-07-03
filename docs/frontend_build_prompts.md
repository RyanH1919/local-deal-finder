# Frontend Build Prompts

Two tracks per stage:
- **BUILD** — paste into Fable. Pure execution, no explanation requested (keeps its
  expensive output tokens focused on code, not prose).
- **EXPLAIN** — paste into a cheaper model (Sonnet, or Haiku if you want it leaner) AFTER
  the build step lands. Read-only: it reads whatever Fable just wrote and teaches it to
  you. This is where the "explain as it's built" pass actually happens now.

Run in order: Build 1 → Explain 1 → verify in browser → Build 2 → Explain 2 → ... Don't
skip the verify step between stages even though there are fewer of them now — each stage
still bundles a few checkpoints from the original plan, so there's more that could go
wrong per stage than before.

Shared ground truth: repo root `c:\Projects\local-deal-finder`. Backend (`api/`,
`database/`, etc.) is done and running separately — nobody touches it except to start it.
Work stays inside `frontend/`.

**Design latitude:** `stitch-export.html` is a rough reference, not a spec to replicate.
You have real creative freedom on anything visual or UX-related — layout, spacing,
colors, typography, card design, copy, which decorative elements to keep/cut/invent,
overall look and feel. If you have a better idea than the wireframe, use it; we may not
even keep the current look. The one thing that is NOT a creative decision: the field
mappings and exact API values spelled out in each stage below (e.g. `urgency=
limited_time`, not "Limited Time"). Those aren't style, they're the contract with a real
backend — get them wrong and the app breaks silently (blank fields, filters that return
nothing) rather than just looking different.

---

## Stage 1 — Scaffold, Tailwind, wireframe port, API layer

### BUILD 1 (Fable)
```
Build the frontend for Local Deal Finder. Backend is a FastAPI app already running at
http://localhost:8000 — don't touch it. Do not add commentary or explain your choices,
just build; keep responses terse.

Stack (final, don't relitigate): Vite + React, plain JavaScript (not TypeScript),
Tailwind CSS configured properly via PostCSS (NOT the CDN <script> tag), Google Fonts
(Hanken Grotesk / Inter / JetBrains Mono) + Material Symbols Outlined via <link> tags.

There's a wireframe at frontend/stitch-export.html — a static HTML/Tailwind mockup
(hardcoded data, fake CSS-hover dropdowns, placeholder map) that was an early visual
reference, not a spec. You have creative freedom here: use its structure/theme as a
starting point, but improve on it where you see fit (layout, spacing, colors,
typography, information hierarchy) — we're not attached to it and may not keep the
current look as-is.

Do this:
1. Scaffold a Vite + React app inside frontend/ (currently just an empty src/ and
   stitch-export.html there — keep stitch-export.html, don't delete it).
2. Install and configure Tailwind for real. Port the exact theme extension (colors,
   borderRadius, spacing, fontFamily) from the <script id="tailwind-config"> block in
   stitch-export.html into a real tailwind.config.js.
3. Port the custom CSS classes from stitch-export.html (.card-shadow, .glass-header,
   .map-container, .map-pin, @keyframes pulse, etc.) into src/index.css.
4. Add the Google Fonts + Material Symbols <link> tags from stitch-export.html's <head>
   into the real index.html.
5. Copy the wireframe's <body> markup into App.jsx as one static component for now
   (class→className, void tags closed, data still hardcoded). Don't extract
   sub-components yet.
6. Create frontend/src/api.js:
   - const API_BASE = "http://localhost:8000"
   - getDeals(filters) — filters is an object like {category:"food", scope:"local"}.
     Build a query string with URLSearchParams, only including keys with a truthy
     value. GET /deals?<query>, return parsed JSON, throw on non-OK response.
   - dismissDeal(id) — POST /deals/{id}/dismiss, return parsed JSON.
7. In App.jsx add a useEffect that calls getDeals({}) once on mount and
   console.log()s the result — pure smoke test, don't render it yet.
8. Confirm it runs at localhost:5173.

At the end, list the files you created/changed — no other narration needed.
```

### EXPLAIN 1 (Sonnet/Haiku, run after Build 1 lands)
```
I'm a 3rd-year CS student, strong in Python/backend, brand new to frontend/React. Fable
(a different Claude model) just scaffolded the frontend of my project at
c:\Projects\local-deal-finder\frontend — a Vite + React + Tailwind app. Read what's
actually in frontend/ right now (package.json, vite.config.js, tailwind.config.js,
postcss.config.js, index.html, src/index.css, src/App.jsx, src/api.js) and explain it to
me:

1. What each config file (vite.config.js, tailwind.config.js, postcss.config.js) is
   responsible for and why Vite/Tailwind need each one.
2. How Tailwind's theme.extend in tailwind.config.js relates to the class names used in
   App.jsx / index.css.
3. What api.js's getDeals(filters) is actually doing with URLSearchParams — walk through
   an example call.
4. What the useEffect in App.jsx is doing, including why its dependency array is empty.
5. How to actually run this (both servers) and what I should see in the browser
   devtools console to confirm it's working.

Don't rewrite or "improve" any code — this is a read-only explanation pass.
```

**Verify before moving on:** both servers running, page looks like `stitch-export.html`,
browser console shows real deal data from the API.

---

## Stage 2 — Real feed: `DealCard`, `DealList`, loading/error/empty

### BUILD 2 (Fable)
```
Frontend scaffold is done — App.jsx has the wireframe markup with hardcoded data, and
api.js's getDeals()/dismissDeal() work and are smoke-tested. Now make the feed real. No
commentary, just build; terse responses only.

Field mapping (wireframe element → real field). Render each optional field only when
present — never show "null"/"undefined" in the UI:

| Wireframe element | Real field | Notes |
|---|---|---|
| Title | business_name | nullable — fall back to a readable category label or "Deal" |
| Price badge ($8.99 struck $12.99) | price_deal + price_original | strikethrough on price_original; hide whole badge if price_deal is null |
| Top-right label ("BOGO Free") | discount_label | show here only when there's no numeric price_deal |
| Category icon + label | category | food→restaurant, grocery→shopping_basket, electronics→devices, services→medical_services, clothing→checkroom, software→apps, other→sell (Material Symbols icon names) |
| Description | deal_description | keep line-clamp-2 |
| LOCAL/ONLINE badge | scope | |
| ENDING SOON/ONGOING badge | urgency | limited_time→"Ending Soon", ongoing→"Ongoing", unknown→hide or "Unknown" |
| Discount badge ("30% OFF") | discount_label | |
| Footer line ("12% below avg") | vs_peers | hide entirely if null |
| VIEW link | source_url | new tab, rel="noopener noreferrer" |
| Dismiss (X) | id | accept onDismiss prop, call with deal id — not functional yet, wired in stage 3 |

Remove anything in the wireframe with no backing data: "Rare deal", "Direct ship", "Low
stock", "Hot Deal", "Early Bird", "Evening Deal" labels and unique per-card icons that
aren't the category icon.

Card layout/visual design is your call — the table above says WHICH field goes where,
not how it has to look. Redesign the card if you think it should look different.

Do this:
1. Create frontend/src/components/DealCard.jsx (props: deal, onDismiss) using the
   mapping above.
2. Create frontend/src/components/DealList.jsx (props: deals, onDismiss) — maps deals to
   <DealCard key={deal.id} .../>. Owns the empty state: if deals.length === 0, show "No
   deals match your filters".
3. Rewrite App.jsx to hold real state: useState for deals (default []), loading (default
   true), error (default null). useEffect on mount: loading true → call getDeals({}) →
   setDeals on success / setError on failure (try/catch) → loading false in finally.
   Render: loading → "Loading deals…"; error → "Couldn't load deals. Is the API
   running?"; else → <DealList deals={deals} onDismiss={...} /> (onDismiss can be a
   no-op stub for now).

List the files you created/changed at the end, nothing else.
```

### EXPLAIN 2 (Sonnet/Haiku)
```
Same context as before — I'm learning frontend, strong in Python/backend. Fable just
built the real feed rendering for my project at c:\Projects\local-deal-finder\frontend.
Read src/components/DealCard.jsx, src/components/DealList.jsx, and the current
src/App.jsx and explain:

1. How props flow: App → DealList → DealCard. What "data flows down, events flow up"
   means concretely in this code (even though onDismiss isn't wired to anything real
   yet).
2. The null-handling patterns used in DealCard (e.g. `??`, conditional rendering with
   `&&` or ternaries) — show me each pattern used and what it does.
3. Why loading/error/empty are three separate states in App.jsx instead of one check,
   and how the try/catch/finally around the fetch produces them.
4. Anything about React's key prop on the mapped DealCard list — why it's there and why
   it's deal.id specifically.

Also point out any visual/UX decisions Fable made that go beyond just copying the
wireframe, and why they're reasonable (or not).

Read-only — don't modify anything.
```

**Verify before moving on:** full grid renders with real deals (including one with a
null field, if any exist, to confirm the fallback works); temporarily stop the backend
and confirm the error state shows.

---

## Stage 3 — Interactivity: `FilterBar` + dismiss

### BUILD 3 (Fable)
```
The feed renders real data with loading/error/empty states working. Now add filtering
and dismiss. No commentary, terse responses only.

Backend filter semantics (GET /deals query params, all optional/combinable):
- location — free-text, case-insensitive SUBSTRING match
- category — EXACT: food | grocery | electronics | services | clothing | software | other
- scope — EXACT: local | online
- urgency — EXACT: limited_time | ongoing | unknown

Dropdown labels shown to the user must map to these exact values before being sent —
e.g. "Ending Soon" → urgency=limited_time. Category label set (final — replaces the
wireframe's invented "Drinks"): Food, Grocery, Electronics, Services, Clothing,
Software, Other.

Do this:
1. Create frontend/src/components/FilterBar.jsx: a text input for location, three real
   <select> dropdowns (category/scope/urgency) built from the label→value maps above,
   and a Reset button. It does not store filter state itself — every change calls an
   onFilterChange(newFilters) prop from App. How this looks/is arranged is your call —
   the label→value maps are the only fixed part, not the visual design.
2. In App.jsx: lift filters into useState (default: all unset). Add filters to the
   fetch effect's dependency array so any filter change refetches via getDeals(filters).
   Wire Reset to clear filters and refetch.
3. Wire real dismiss: DealCard's dismiss button → onDismiss(deal.id) → App calls
   dismissDeal(id) from api.js → on success, refetch the list (getDeals(filters) again;
   simplest correct approach, no optimistic update needed).

List the files you created/changed at the end, nothing else.
```

### EXPLAIN 3 (Sonnet/Haiku)
```
Same context — learning frontend, strong in Python/backend. Fable just wired filtering
and dismiss for my project at c:\Projects\local-deal-finder\frontend. Read
src/components/FilterBar.jsx and the current src/App.jsx and explain:

1. What a "controlled component" is and how FilterBar's inputs/selects demonstrate it.
2. Why filters live in App's state instead of FilterBar's own state — walk through what
   would break if FilterBar tried to own it locally.
3. Why adding `filters` to the fetch effect's dependency array causes a refetch on every
   change, and why we refetch from the backend instead of filtering the already-fetched
   array client-side.
4. The full dismiss flow end to end, from clicking the X button to the deal disappearing
   from the grid.

Also point out any visual/UX decisions Fable made that go beyond just copying the
wireframe, and why they're reasonable (or not).

Read-only — don't modify anything.
```

**Verify before moving on:** each filter, changed individually, produces the correct
query param + value in devtools network tab (not the pretty label); dismissing a real
deal removes it from the grid and the POST returns `{"success": true}`. Note: dismiss is
permanent — this actually deletes the deal from the database.

---

## Stage 4 — Header + cleanup

### BUILD 4 (Fable)
```
Everything else works end to end (fetch, filter, dismiss, null handling, loading/error/
empty states). This is a small finishing pass. No commentary, terse responses only.

Do this:
1. Extract the header markup from App.jsx into frontend/src/components/Header.jsx (logo/
   app name). The wireframe's decorative account icon has no backing auth — drop it or
   leave as a visual-only stub, your call. Design/branding here is open — app name,
   colors, styling are not locked to the wireframe.
2. Pass over App.jsx and extract anything still left over from the original wireframe
   paste that should have become a component in an earlier stage but didn't.
3. Confirm nothing still references stitch-export.html or hardcoded sample data.

List the final file tree under frontend/src and nothing else.
```

### EXPLAIN 4 (Sonnet/Haiku)
```
Same context — learning frontend. Fable just finished the frontend build for my project
at c:\Projects\local-deal-finder\frontend. Read the final src/ tree (all files) and give
me:
1. A one-paragraph summary of what each file owns.
2. A simple diagram (text is fine) of the component tree and how data/events flow
   through it.
3. Anything you'd flag as worth understanding before I show this project in an
   interview — i.e. the 2-3 React/JS concepts in this codebase most worth being able to
   explain out loud.

Also point out any visual/UX decisions Fable made that go beyond just copying the
wireframe, and why they're reasonable (or not).

Read-only — don't modify anything.
```

**Verify:** full manual walkthrough — load, filter, dismiss, refresh — one last time.

---

## Not in this sequence (Layer 2 — later, separate session)
- `MapPanel.jsx` with real Leaflet, plotting deals with non-null lat/lng
- Client-side price-range filtering (no backend param exists yet)
- Rendering the `products` JSON field
- Any restyling beyond what the wireframe already specifies