import { useCallback, useEffect, useState } from "react";
import { getDeals, dismissDeal } from "./api";
import Header from "./components/Header";
import FilterBar, { EMPTY_FILTERS } from "./components/FilterBar";
import DealList from "./components/DealList";
import MapPanel from "./components/MapPanel";

export default function App() {
  const [deals, setDeals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({ ...EMPTY_FILTERS });

  const loadDeals = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setDeals(await getDeals(filters));
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadDeals();
  }, [loadDeals]);

  const handleDismiss = async (id) => {
    try {
      await dismissDeal(id);
      await loadDeals();
    } catch (err) {
      console.error("Dismiss failed:", err);
    }
  };

  return (
    <div className="bg-background text-on-background min-h-screen">
      <Header />
      <div className="pt-[60px] flex h-screen overflow-hidden">
        <div className="w-full lg:w-1/2 flex-shrink-0 px-margin-mobile md:px-margin-desktop overflow-y-auto pb-lg h-full border-r border-outline-variant">
          <FilterBar filters={filters} onFilterChange={setFilters} />
          {loading ? (
            <div className="flex flex-col items-center gap-sm py-xl text-center">
              <span className="material-symbols-outlined text-[40px] text-outline animate-spin">progress_activity</span>
              <p className="font-body-md text-body-md text-on-surface-variant">Loading deals…</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center gap-sm py-xl text-center">
              <span className="material-symbols-outlined text-[40px] text-error">error</span>
              <p className="font-body-md text-body-md text-on-surface-variant">Couldn't load deals. Is the API running?</p>
            </div>
          ) : (
            <DealList deals={deals} onDismiss={handleDismiss} />
          )}
        </div>
        <MapPanel dealCount={deals.length} />
      </div>
    </div>
  );
}
