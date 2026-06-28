# Frontend Foundation Plan — Local Deal Finder

A learning-oriented plan for building the React feed that displays our deals. This is
**planning only** — no frontend code has been written yet. It's written for someone
building their first real frontend, so it explains *what* each piece is and *why* it
exists, not just *what to type*.

The plan is split into two layers on purpose:

- **Layer 1 — Structure (build now).** Everything that does *not* depend on what the
  app looks like: the React project, talking to the API, rendering data, filters,
  dismiss. A card that shows a business name and a dismiss button is the same component
  whether it ends up blue or green.
- **Layer 2 — Skin (after Noah).** The visual/UX design: colours, layout, branding,
  which existing deals site we model the look on. These are marked as TODO placeholders
  because they need a conversation with Noah first.

Good React apps separate these anyway — logic lives in components, appearance lives in
CSS — so we can build the working skeleton now and layer the design on top later
without rewriting the logic.

---

## How the backend actually behaves (ground truth)

Everything below was read directly from our code so the plan matches reality, not
assumptions.

### The API surface (`api/routes.py`)

**`GET /deals`** — returns a JSON array of active deals (newest first). It supports four
**optional** query parameters, all combinable:

| Param      | Match type                          | Example values                                                              |
|------------|-------------------------------------|----------------------------------------------------------------------------|
| `location` | case-insensitive **substring**      | `Mississauga`, `Ontario` (matches if the text appears anywhere in location) |
| `urgency`  | **exact** match                     | `limited_time`, `ongoing`, `unknown`                                        |
| `scope`    | **exact** match                     | `local`, `online`                                                          |
| `category` | **exact** match                     | `food`, `grocery`, `electronics`, `services`, `clothing`, `software`, `other` |

Example request the frontend will make:
```
GET http://localhost:8000/deals?category=food&scope=local
```

**Important for the UI:** `location` is a loose substring search (good for a free-text
box), but `urgency`, `scope`, and `category` are **exact** matches. That means our
dropdowns must send *exactly* the values the backend expects — `limited_time`, not
`Limited Time`. We'll map pretty labels → exact values in the frontend.

**`POST /deals/{deal_id}/dismiss`** — marks one deal as expired in the database and
returns `{"success": true}`. After this, that deal no longer appears in `GET /deals`
(the backend filters out expired deals). Note: this is **permanent and global** —
there's no per-user state and no undo. (Flagged as an open question below.)

### What the backend only serves "clean" deals

`get_active_deals()` in `database/db.py` runs:
```sql
SELECT * FROM deals WHERE is_expired = 0 AND ai_processed = 1 ORDER BY fetched_at DESC
```
So the frontend automatically only ever sees AI-processed, non-expired deals, newest
first. We don't have to filter junk on the frontend — the quality gate already happened.

### The fields on each deal (from `database/models.py`)

Every deal object the API returns has these fields. The ones the UI will actually use
are marked.

| Field              | Type          | UI use                                              |
|--------------------|---------------|-----------------------------------------------------|
| `id`               | int           | **Yes** — needed for the dismiss call               |
| `business_name`    | string\|null  | **Yes** — card title (can be null! handle it)       |
| `deal_description` | string        | **Yes** — main card body                            |
| `category`         | string        | **Yes** — badge + filter                            |
| `scope`            | string        | **Yes** — badge + filter (`local`/`online`)         |
| `location`         | string\|null  | **Yes** — show where it is; also the location filter |
| `urgency`          | string        | **Yes** — badge + filter                            |
| `source_url`       | string        | **Yes** — "View original" link                      |
| `posted_at`        | datetime\|null| Maybe — Reddit deals have it, website deals don't   |
| `fetched_at`       | datetime      | Maybe — "found on" date; this is the sort key       |
| `source_type`      | string        | Maybe — `social` vs `website` (could show source)   |
| `source_name`      | string        | Maybe — e.g. `reddit` or `pizzaiolo.ca`             |
| `lat` / `lng`      | float\|null   | Future — only website deals have these (map view)   |
| `subreddit`        | string\|null  | Optional — Reddit deals only                        |
| `content_hash`     | string\|null  | **No** — internal dedup field, ignore in UI         |
| `ai_processed`     | bool          | **No** — always 1 for served deals, ignore          |
| `is_expired`       | bool          | **No** — always 0 for served deals, ignore          |

**Price fields (added after this table was first written)** — these ride on every deal
alongside the columns above. All `TEXT`, all nullable:

| Field             | Type         | UI use                                              |
|-------------------|--------------|-----------------------------------------------------|
| `price_deal`      | string\|null | **Yes** — the price, shown prominently on the card  |
| `price_original`  | string\|null | Maybe — struck-through "was" price                  |
| `discount_label`  | string\|null | Maybe — savings badge (e.g. "50% off", "BOGO")      |
| `min_spend`       | string\|null | Optional — "min. $50" note near the price           |
| `expires`         | string\|null | Optional — expiry text shown with the urgency badge |

Heads-up: these come from the **Reddit** extractor only for now — website deals leave them
`null`, and even Reddit deals fill them only when a price was actually found. So treat them
exactly like the nullable fields below: render each one only when present.

**Two null-handling rules the UI must respect:**
1. `business_name` can be `null` (some Reddit deals have no named business). Fall back
   to something like the category or "Deal" so the card never shows "null".
2. `posted_at`, `location`, `lat`/`lng`, and all the Flow 2 fields below can be `null`.
   Only render them when present.

### Flow 2 additions (built — use these for the deal card)

The website-crawl flow (`crawl/`) now returns richer deals. New on `GET /deals`:

**New query params** (combine with the existing ones):

| Param         | Meaning                                                             |
|---------------|---------------------------------------------------------------------|
| `lat` & `lng` | user's location → resolved to its geohash cell ("deals in my cell") |
| `cell`        | a geohash cell id directly                                          |

`GET /deals?lat=43.73&lng=-79.60` returns just that cell's deals.

**New deal fields:**

| Field            | Type          | UI use                                                            |
|------------------|---------------|-------------------------------------------------------------------|
| `price_deal`     | string\|null  | headline price (e.g. "from $10.99")                               |
| `discount_label` | string\|null  | advertised discount (e.g. "50% off") — null if none stated        |
| `products`       | JSON string   | the tenant's offers: list of `{name, price, price_original, discount, vs_peers}` |
| `vs_peers`       | string\|null  | deal-level price standing in its cell ("from $10.99 — ~8% below 1 nearby") |
| `geohash`        | string\|null  | the deal's cell id (website deals only)                           |

`products` is a JSON **string** — `JSON.parse` it. Each product may carry its own
`vs_peers` ("~17% below 2 nearby"). Everything here is null/empty when the data isn't
available (Reddit deals, or a page with no comparable peer) — render only when present.

Example website deal:
```json
{
  "business_name": "City South Pizza",
  "price_deal": "from $10.99",
  "discount_label": null,
  "vs_peers": "from $10.99 — ~8% below 1 nearby",
  "products": "[{\"name\":\"Single Topping Pizza\",\"price\":\"$10.99\",\"vs_peers\":null}]",
  "category": "food", "scope": "local", "geohash": "dpz2u9"
}
```

---

# LAYER 1 — Structure (build now)

## 1. Stack choice: Vite + React (and why)

**React** is the library that lets us describe the UI as reusable "components"
(functions that return HTML-like markup). Instead of manually updating the page when
data changes, we describe *what the page should look like for a given set of data*, and
React updates the DOM for us. This is the dominant frontend skill on resumes, which
matters for your goal.

**Vite** is the build tool / dev server that runs React during development. It gives us:
- A dev server with instant hot-reload (you save a file, the browser updates immediately).
- A simple `npm create vite` scaffold so we don't hand-wire the build.
- A default dev port of **5173**.

**Why this specifically fits us:** our API's CORS is already configured to allow exactly
`http://localhost:5173` (see `api/routes.py`). CORS is a browser security rule — by
default a page served from one origin (`localhost:5173`) is **not allowed** to call an
API on a different origin (`localhost:8000`) unless the API explicitly permits it. Our
backend already permits `5173`, which is Vite's default. So if we use Vite and don't
change the port, API calls will "just work." If we used a different tool/port, we'd have
to update the backend CORS list first.

> **Decision needed (see open questions):** JavaScript vs TypeScript, and plain CSS vs a
> styling library. The rest of this plan assumes plain **JavaScript + plain CSS** to keep
> your first frontend simple, but both are easy to revisit.

## 2. Folder structure

We'll create a `frontend/` directory **inside the repo** (the Python backend stays at
the root; the frontend is a self-contained sub-project with its own `package.json`).

```
local-deal-finder/
├── api/                  # existing backend
├── frontend/             # NEW — the React app
│   ├── index.html        # the single HTML page React mounts into
│   ├── package.json      # frontend dependencies + scripts (npm run dev, etc.)
│   ├── vite.config.js    # Vite config (port, plugins)
│   └── src/
│       ├── main.jsx      # entry point — mounts <App> into index.html
│       ├── App.jsx       # top-level component: owns state, fetches data
│       ├── api.js        # tiny helper that wraps fetch() calls to our API
│       ├── components/
│       │   ├── FilterBar.jsx   # the filter controls
│       │   ├── DealList.jsx    # renders the list (and the empty state)
│       │   └── DealCard.jsx    # renders one deal
│       └── styles/             # placeholder CSS (Layer 2 fills this in)
└── ...
```

**Why a single `api.js` helper?** So every place that talks to the backend goes through
one file. If the API URL changes (e.g. when we deploy), we edit one line, not ten
scattered `fetch` calls. It also keeps components focused on *display*, not networking.

## 3. How the frontend talks to the API

All requests go to a base URL we'll define once in `api.js`:
```
const API_BASE = "http://localhost:8000";
```

Two functions live there (described, not coded):

- **`getDeals(filters)`** — builds a query string from the active filters and calls
  `GET /deals`. For example, `{ category: "food", scope: "local" }` becomes
  `GET /deals?category=food&scope=local`. Empty/unset filters are simply left out of the
  URL (so "no filter" returns everything). Returns the parsed JSON array.

- **`dismissDeal(id)`** — calls `POST /deals/{id}/dismiss`. Returns the success response.

**Building the query string:** the standard browser tool is `URLSearchParams` — you give
it an object of key/values and it produces `category=food&scope=local`, correctly
escaped. We only add a param if the user actually set it.

## 4. Component breakdown (what each piece owns)

Think of components as a tree. Data flows **down** (parent passes data to child via
"props"); events flow **up** (child calls a function the parent gave it).

- **`App`** — the brain. It owns:
  - the list of `deals` (fetched from the API),
  - the current `filters`,
  - `loading` and `error` status.
  It fetches data, and passes data + callbacks down to the children. Nothing else holds
  the source-of-truth state — this keeps things predictable.

- **`FilterBar`** — renders the controls: a free-text box for `location`, and dropdowns
  for `category`, `scope`, `urgency`. It doesn't *store* the filters itself; when the
  user changes a control, it calls a function from `App` (e.g. `onFilterChange`) so
  `App` updates the single source of truth. This is the "events flow up" idea.

- **`DealList`** — receives the `deals` array and maps each one to a `DealCard`. It also
  owns the **empty state** ("No deals match your filters") because "the list is empty" is
  a list-level concern.

- **`DealCard`** — receives one `deal` object and renders it: business name (with the
  null fallback), description, badges for category/scope/urgency, the location if
  present, a "View original" link to `source_url`, and a **Dismiss** button. The button
  calls a function from `App` (e.g. `onDismiss(deal.id)`).

**Why split it this way?** Each component has one job and is easy to reason about and
restyle later (Layer 2). `DealCard` in particular will get most of the visual design
work, and isolating it means design changes don't touch the data logic.

## 5. Data fetching + state approach

We use React's two core hooks:

- **`useState`** — holds values that change over time and should re-render the UI when
  they do. We'll have: `deals`, `filters`, `loading`, `error`.
- **`useEffect`** — runs side effects (like fetching) in response to changes. We give it
  a "dependency array": when something in that array changes, the effect re-runs.

**The flow:**
1. On first load, `useEffect` runs once and calls `getDeals` with no filters → shows all
   deals.
2. We put `filters` in the effect's dependency array. So **whenever the user changes a
   filter, the effect re-runs and refetches** with the new query string. (Simple and
   correct; we can optimize later if needed.)
3. Around each fetch: set `loading = true` before, `loading = false` after, and catch
   errors into `error`.

**Why refetch on every filter change instead of filtering in the browser?** Because the
backend already implements the filters, refetching keeps one source of truth and means
the frontend doesn't duplicate filter logic. (If the dataset grew huge we might filter
client-side or paginate — noted as future work.)

## 6. Loading / error / empty states

A real UI must handle all three, not just the happy path:

- **Loading:** while a fetch is in flight, show a simple "Loading deals…" message (or
  later, a spinner/skeleton — Layer 2). Prevents a confusing blank flash.
- **Error:** if the API is down or the request fails, show "Couldn't load deals. Is the
  API running?" This is *very* common during dev when you forget to start the backend —
  a clear message saves confusion.
- **Empty:** the request succeeded but returned `[]` (e.g. filters too narrow, or the DB
  is empty). Show "No deals match your filters" — distinct from an error, because nothing
  went wrong.

These are three different situations and the user should see three different things.

## 7. The dismiss flow end to end

1. User clicks **Dismiss** on a `DealCard`.
2. `DealCard` calls `onDismiss(deal.id)` (passed down from `App`).
3. `App` calls `dismissDeal(id)` from `api.js` → `POST /deals/{id}/dismiss`.
4. On success, the deal must disappear from the feed. Two ways:
   - **Refetch** the whole list (simplest, guaranteed consistent — recommended to start).
   - **Optimistic update** (remove it from local `deals` immediately for snappier feel,
     then trust the backend). Slightly more code; we can upgrade to this later.
5. Remember the backend dismiss is **permanent** — once dismissed it won't come back
   from `GET /deals`. (See open questions about whether that's the behavior we want.)

## 8. Dev workflow — running both servers together

The frontend and backend are **two separate processes**. You'll have two terminals open.

**Terminal 1 — backend (from repo root):**
```
.venv\Scripts\Activate.ps1
python -m uvicorn api.routes:app --port 8000
```
Leave it running. It serves the API at `http://localhost:8000`.

**Terminal 2 — frontend (from the frontend/ folder):**
```
cd frontend
npm install      # first time only — installs dependencies
npm run dev      # starts Vite on http://localhost:5173
```

Then open **`http://localhost:5173`** in the browser. The React app loads there and
makes API calls to `localhost:8000`. (Opening `8000` directly just shows raw JSON — that's
the API, not the app.)

**Make sure the DB has data first:** run `python main.py --test` (Flow 1) and/or
`python main.py --search ...` (Flow 2) so `GET /deals` returns something to display.

## 9. Numbered build order

Do these in order — each step is verifiable before moving on, so you're never debugging
ten things at once.

1. **Scaffold** the Vite React app in `frontend/` (`npm create vite`), then `npm install`.
2. **Run it** (`npm run dev`) and confirm the default Vite page loads at `localhost:5173`.
   (Proves the toolchain works before we add anything.)
3. **Write `api.js`** with `API_BASE` and a `getDeals()` that ignores filters for now.
4. **Fetch in `App`** with `useEffect` and `console.log` the result. Open the browser
   console and confirm you see our deals array. **This is the CORS smoke test** — if it
   fails here, the issue is connection/CORS, isolated from any UI work.
5. **Build `DealCard`** with hardcoded/static text first, then wire it to a real `deal`
   prop. Handle the `business_name` null fallback.
6. **Build `DealList`** to map `deals` → `DealCard`s. Now the real feed renders.
7. **Add loading / error / empty states** in `App`/`DealList`.
8. **Build `FilterBar`**, lift `filters` into `App`, and add `filters` to the `useEffect`
   dependency array so changing a filter refetches.
9. **Wire dismiss**: button → `onDismiss` → `dismissDeal` → refetch.
10. **Drop in placeholder CSS** so it's legible (not designed — just readable).
11. **(Layer 2, with Noah)** apply the real visual design.

By step 9 you have a fully functional app. Steps 10–11 are appearance only.

---

# LAYER 2 — Skin (after discussing with Noah)

These are deliberately **not decided yet** — they need Noah. Listed as TODO placeholders
so Layer 1 can proceed without them.

- **TODO (Noah):** Which existing deals site do we model the look on? (e.g. RedFlagDeals,
  Flipp, Honey, a generic card-feed). This anchors every other visual decision.
- **TODO (Noah):** Colour palette, fonts, logo, and the app's display name/branding.
- **TODO (Noah):** `DealCard` visual design — what's most prominent at a glance? Badges
  for urgency/scope/category — colours and shapes?
- **TODO (Noah):** Layout — single column feed? grid of cards? sidebar for filters vs a
  top bar?
- **TODO (Noah):** Mobile-first or desktop-first? Responsive breakpoints.
- **TODO (Noah):** Visual treatment of loading (spinner vs skeleton cards) and empty
  states (illustration vs plain text).
- **TODO (Noah):** Do we want a **map view** eventually? Website deals have `lat`/`lng`,
  so it's possible later — but it's a bigger feature, not part of the foundation.

---

# Closing: open questions & possible backend tweaks

## (1) Open questions for both

- **JavaScript or TypeScript?** Recommendation: plain **JavaScript** for your first
  frontend (less to learn at once). TypeScript is a resume plus and we can migrate later
  — but it adds type syntax on top of everything new here.
- **Plain CSS, CSS Modules, or a library (Tailwind/MUI)?** Recommendation: start with
  **plain CSS** so styling stays decoupled until Noah weighs in. (Borders on Layer 2, but
  it's also a setup decision, so it's here.)
- **Should dismiss be permanent?** Right now it's permanent and global. Is that what you
  want for a demo, or should "dismiss" just hide locally (so a refresh brings it back)?
- **"View original" link** — confirm we want each card to link out to `source_url`
  (opens the Reddit post or business page). I assumed yes.
- **What name should the app display** in the header? (Even a placeholder.)

## (2) Open questions for both

- Which existing deals site is our visual reference?
- Branding: colours, logo, app name, overall vibe (clean/minimal vs bold/dense)?
- `DealCard` design — what info matters most to a user scanning the feed?
- Single-column feed vs grid? Filters in a sidebar vs a top bar?
- Mobile-first or desktop-first?
- Is a map view a goal we should design toward, or skip for now?

## (3) Backend/API tweaks that would help the frontend

None are required to start — Layer 1 works against the API as-is. These are
"nice to have," in rough priority order:

- **A small `/meta` (or `/filters`) endpoint** returning the valid `category`, `scope`,
  and `urgency` values. Right now the frontend would **hardcode** these dropdown options.
  Hardcoding is fine to start, but an endpoint keeps frontend and backend in sync if we
  ever change the category list. *Low priority.*
- **Pagination / a result limit** on `GET /deals`. Today it returns *everything*. Fine
  while the dataset is small; we'd want `?limit=` & `?offset=` (or cursor paging) before
  the feed gets large. *Future.*
- **Dismiss semantics.** If we decide dismiss should be undoable or per-session rather
  than permanent+global, that's a backend change (e.g. a separate "hidden" concept vs the
  permanent `is_expired` flag). Depends on the open question above. *Depends.*
- **A health-check endpoint** (e.g. `GET /health` → `{"ok": true}`) so the frontend can
  show "API is offline" cleanly instead of inferring it from a failed deals request.
  *Optional, minor.*
- **Deployment CORS.** `allow_origins` is hardcoded to `localhost:5173`. Purely a dev
  setting — we'll need to add the real domain when we deploy. *Note for later, not now.*

---

*Next step when Ryan is back: review this together, answer the open questions in section
(1), and decide whether to start Layer 1 now or wait for Noah's input on Layer 2.*
