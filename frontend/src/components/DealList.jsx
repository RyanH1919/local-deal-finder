import DealCard from "./DealCard";

export default function DealList({ deals, onDismiss }) {
  if (deals.length === 0) {
    return (
      <div className="flex flex-col items-center gap-sm py-xl text-center">
        <span className="material-symbols-outlined text-[40px] text-outline">search_off</span>
        <p className="font-body-md text-body-md text-on-surface-variant">No deals match your filters</p>
      </div>
    );
  }

  return (
    <main className="grid grid-cols-1 xl:grid-cols-2 gap-sm">
      {deals.map((deal) => (
        <DealCard key={deal.id} deal={deal} onDismiss={onDismiss} />
      ))}
    </main>
  );
}
