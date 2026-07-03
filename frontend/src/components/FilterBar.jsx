const CATEGORY_OPTIONS = [
  { label: "Food", value: "food" },
  { label: "Grocery", value: "grocery" },
  { label: "Electronics", value: "electronics" },
  { label: "Services", value: "services" },
  { label: "Clothing", value: "clothing" },
  { label: "Software", value: "software" },
  { label: "Other", value: "other" },
];

const SCOPE_OPTIONS = [
  { label: "Local", value: "local" },
  { label: "Online", value: "online" },
];

const URGENCY_OPTIONS = [
  { label: "Ending Soon", value: "limited_time" },
  { label: "Ongoing", value: "ongoing" },
  { label: "Unknown", value: "unknown" },
];

// Applied client-side (no backend param) — values are "min-max" half-open ranges.
const PRICE_OPTIONS = [
  { label: "Under $10", value: "0-10" },
  { label: "$10–$25", value: "10-25" },
  { label: "$25–$50", value: "25-50" },
  { label: "$50+", value: "50-" },
];

const EMPTY_FILTERS = { location: "", category: "", scope: "", urgency: "", price: "" };

const fieldClass =
  "h-9 rounded-lg border border-line bg-surface-2 text-sm text-ink placeholder:text-ink-faint outline-none transition-colors hover:border-line-2 focus:border-brand/60 focus:ring-1 focus:ring-brand/40";

function FilterSelect({ placeholder, options, value, onChange }) {
  return (
    <select
      aria-label={placeholder}
      className={`${fieldClass} flex-1 min-w-[110px] pl-sm pr-lg cursor-pointer ${value ? "" : "text-ink-dim"}`}
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      <option value="">{placeholder}</option>
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}

export default function FilterBar({ filters, onFilterChange }) {
  const set = (key) => (value) => onFilterChange({ ...filters, [key]: value });
  const filtersActive = Object.values(filters).some(Boolean);

  return (
    <section className="sticky top-0 z-40 bg-bg/90 backdrop-blur-md pt-md pb-sm mb-sm border-b border-line flex flex-col gap-sm">
      <div className="relative w-full">
        <span aria-hidden="true" className="material-symbols-outlined absolute left-sm top-1/2 -translate-y-1/2 text-ink-faint text-[18px]">search</span>
        <input
          aria-label="Filter by location"
          className={`${fieldClass} w-full pl-[36px] pr-sm`}
          placeholder="Search by location…"
          type="text"
          value={filters.location}
          onChange={(e) => set("location")(e.target.value)}
        />
      </div>
      <div className="flex gap-xs w-full flex-wrap items-center">
        <FilterSelect placeholder="Any Price" options={PRICE_OPTIONS} value={filters.price} onChange={set("price")} />
        <FilterSelect placeholder="Category" options={CATEGORY_OPTIONS} value={filters.category} onChange={set("category")} />
        <FilterSelect placeholder="Scope" options={SCOPE_OPTIONS} value={filters.scope} onChange={set("scope")} />
        <FilterSelect placeholder="Urgency" options={URGENCY_OPTIONS} value={filters.urgency} onChange={set("urgency")} />
        <button
          onClick={() => onFilterChange({ ...EMPTY_FILTERS })}
          disabled={!filtersActive}
          className="h-9 flex items-center gap-xs px-sm rounded-lg text-sm text-ink-dim hover:text-ink hover:bg-surface-3 transition-colors active:scale-95 duration-150 disabled:opacity-40 disabled:pointer-events-none"
        >
          <span aria-hidden="true" className="material-symbols-outlined text-[18px]">restart_alt</span>
          Reset
        </button>
      </div>
    </section>
  );
}

export { EMPTY_FILTERS };
