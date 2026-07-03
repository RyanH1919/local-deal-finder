import DealCard from "./DealCard";

export default function DealList({ deals, onDismiss, filtersActive = false }) {
  if (deals.length === 0) {
    return (
      <div role="status" className="flex flex-col items-center gap-sm py-xl text-center">
        <span className="material-symbols-outlined text-[40px] text-outline" aria-hidden="true">search_off</span>
        <p className="font-body-md text-body-md text-on-surface-variant">
          {filtersActive ? "No deals match your filters" : "No deals yet — check back soon"}
        </p>
      </div>
    );
  }

  return (
    <ul className="grid grid-cols-1 xl:grid-cols-2 gap-sm list-none p-0 m-0">
      {deals.map((deal) => (
        <li key={deal.id} className="flex">
          <DealCard deal={deal} onDismiss={onDismiss} />
        </li>
      ))}
    </ul>
  );
}
