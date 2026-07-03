import { useEffect, useMemo, useState } from "react";
import { getDeals, dismissDeal } from "./api";
import Header from "./components/Header";
import FilterBar, { EMPTY_FILTERS } from "./components/FilterBar";
import DealList from "./components/DealList";
import MapPanel from "./components/MapPanel";
import useDebounce from "./hooks/useDebounce";

export default function App() {
  const [deals, setDeals] = useState([]);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [filters, setFilters] = useState({ ...EMPTY_FILTERS });
  const [reloadKey, setReloadKey] = useState(0);

  // Debounce free-text location so we don't fire a request per keystroke;
  // select filters apply immediately.
  const debouncedLocation = useDebounce(filters.location, 300);
  const queryFilters = useMemo(
    () => ({
      location: debouncedLocation,
      category: filters.category,
      scope: filters.scope,
      urgency: filters.urgency,
    }),
    [debouncedLocation, filters.category, filters.scope, filters.urgency]
  );
  const filtersActive = Object.values(queryFilters).some(Boolean);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setFetching(true);
      setError(null);
      try {
        const data = await getDeals(queryFilters, { signal: controller.signal });
        setDeals(data);
        setHasLoaded(true);
      } catch (err) {
        if (err.name !== "AbortError") setError(err);
      } finally {
        if (!controller.signal.aborted) setFetching(false);
      }
    }
    load();
    return () => controller.abort();
  }, [queryFilters, reloadKey]);

  const retry = () => setReloadKey((k) => k + 1);

  const handleDismiss = async (id) => {
    setActionError(null);
    const snapshot = deals;
    setDeals(snapshot.filter((d) => d.id !== id));
    try {
      await dismissDeal(id);
    } catch (err) {
      console.error("Dismiss failed:", err);
      setDeals(snapshot);
      setActionError("Couldn't dismiss that deal — please try again.");
    }
  };

  const showInitialLoading = !hasLoaded && fetching;
  const showFullError = error && !hasLoaded;

  return (
    <div className="bg-background text-on-background min-h-screen">
      <Header />
      <div className="pt-[60px] flex h-screen overflow-hidden">
        <main className="w-full lg:w-1/2 flex-shrink-0 px-margin-mobile md:px-margin-desktop overflow-y-auto pb-lg h-full border-r border-outline-variant">
          <FilterBar filters={filters} onFilterChange={setFilters} />

          {actionError && (
            <div role="alert" className="flex items-center gap-xs mb-sm px-sm py-xs rounded-lg bg-error-container/20 border border-error/30 text-error font-body-md text-body-md">
              <span className="material-symbols-outlined text-[18px]" aria-hidden="true">warning</span>
              {actionError}
            </div>
          )}

          {showInitialLoading ? (
            <div role="status" className="flex flex-col items-center gap-sm py-xl text-center">
              <span className="material-symbols-outlined text-[40px] text-outline animate-spin" aria-hidden="true">progress_activity</span>
              <p className="font-body-md text-body-md text-on-surface-variant">Loading deals…</p>
            </div>
          ) : showFullError ? (
            <div role="alert" className="flex flex-col items-center gap-sm py-xl text-center">
              <span className="material-symbols-outlined text-[40px] text-error" aria-hidden="true">error</span>
              <p className="font-body-md text-body-md text-on-surface-variant">Couldn't load deals. Is the API running?</p>
              <button
                onClick={retry}
                className="bg-primary text-on-primary hover:bg-primary-fixed-dim font-label-caps text-label-caps px-md py-xs rounded-full transition-colors"
              >
                RETRY
              </button>
            </div>
          ) : (
            <>
              {error && (
                <div role="alert" className="flex items-center justify-between gap-xs mb-sm px-sm py-xs rounded-lg bg-error-container/20 border border-error/30 text-error font-body-md text-body-md">
                  <span>Couldn't refresh deals.</span>
                  <button onClick={retry} className="underline hover:text-on-error-container transition-colors">Retry</button>
                </div>
              )}
              <div aria-busy={fetching} className={fetching ? "opacity-60 transition-opacity" : "transition-opacity"}>
                <DealList deals={deals} onDismiss={handleDismiss} filtersActive={filtersActive} />
              </div>
            </>
          )}
        </main>
        <MapPanel dealCount={deals.length} />
      </div>
    </div>
  );
}
