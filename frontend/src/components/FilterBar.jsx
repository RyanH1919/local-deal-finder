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

const EMPTY_FILTERS = { location: "", category: "", scope: "", urgency: "" };

const selectClass =
  "flex-1 min-w-[120px] pl-sm pr-lg py-xs rounded-lg border border-outline-variant bg-surface-container hover:bg-surface-container-high focus:border-primary focus:ring-1 focus:ring-primary outline-none font-body-md text-body-md text-on-surface cursor-pointer transition-colors";

function FilterSelect({ placeholder, options, value, onChange }) {
  return (
    <select aria-label={placeholder} className={selectClass} value={value} onChange={(e) => onChange(e.target.value)}>
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

  return (
    <section className="bg-surface-container-low border border-outline-variant rounded-xl p-xs mb-sm mt-sm shadow-sm flex flex-col gap-xs sticky top-0 z-40">
      <div className="relative w-full">
        <span aria-hidden="true" className="material-symbols-outlined absolute left-sm top-1/2 transform -translate-y-1/2 text-outline text-[18px]">location_on</span>
        <input
          aria-label="Filter by location"
          className="w-full pl-lg pr-sm py-xs rounded-lg bg-surface-container border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary outline-none font-body-md text-body-md text-on-surface transition-all placeholder:text-outline"
          placeholder="Location..."
          type="text"
          value={filters.location}
          onChange={(e) => set("location")(e.target.value)}
        />
      </div>
      <div className="flex gap-xs w-full flex-wrap">
        <FilterSelect placeholder="Category" options={CATEGORY_OPTIONS} value={filters.category} onChange={set("category")} />
        <FilterSelect placeholder="Scope" options={SCOPE_OPTIONS} value={filters.scope} onChange={set("scope")} />
        <FilterSelect placeholder="Urgency" options={URGENCY_OPTIONS} value={filters.urgency} onChange={set("urgency")} />
        <button
          onClick={() => onFilterChange({ ...EMPTY_FILTERS })}
          disabled={!Object.values(filters).some(Boolean)}
          className="flex items-center gap-xs px-sm py-xs rounded-lg text-on-surface-variant hover:text-primary hover:bg-primary/10 transition-colors font-body-md text-body-md active:scale-95 duration-150 disabled:opacity-40 disabled:pointer-events-none"
        >
          <span aria-hidden="true" className="material-symbols-outlined text-[18px]">restart_alt</span>
          <span>Reset</span>
        </button>
      </div>
    </section>
  );
}

export { EMPTY_FILTERS };
