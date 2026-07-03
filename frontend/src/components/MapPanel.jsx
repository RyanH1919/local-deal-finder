import { useEffect, useMemo } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";

const DEFAULT_CENTER = [43.589, -79.6441]; // Mississauga
const DEFAULT_ZOOM = 11;

function FitBounds({ points }) {
  const map = useMap();
  useEffect(() => {
    if (points.length === 0) return;
    if (points.length === 1) {
      map.setView(points[0], 14);
    } else {
      map.fitBounds(points, { padding: [40, 40], maxZoom: 14 });
    }
  }, [points, map]);
  return null;
}

export default function MapPanel({ deals }) {
  const mapped = useMemo(
    () => deals.filter((d) => d.lat != null && d.lng != null),
    [deals]
  );
  const points = useMemo(() => mapped.map((d) => [d.lat, d.lng]), [mapped]);

  return (
    <aside className="hidden lg:block w-full lg:w-1/2 h-full relative" aria-label="Map of deals">
      <MapContainer
        center={DEFAULT_CENTER}
        zoom={DEFAULT_ZOOM}
        className="h-full w-full"
        scrollWheelZoom
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
        />
        <FitBounds points={points} />
        {mapped.map((deal) => (
          <CircleMarker
            key={deal.id}
            center={[deal.lat, deal.lng]}
            radius={8}
            pathOptions={{ color: "#fbbf24", fillColor: "#f59e0b", fillOpacity: 0.75, weight: 2 }}
          >
            <Popup>
              <div className="flex flex-col gap-1 min-w-[180px]">
                <strong className="font-display text-[15px]">
                  {deal.business_name || "Deal"}
                </strong>
                {(deal.price_deal || deal.discount_label) && (
                  <span className="font-mono text-[13px] text-brand">
                    {deal.price_deal || deal.discount_label}
                  </span>
                )}
                {deal.location && <span className="text-[12px] opacity-80">{deal.location}</span>}
                {deal.deal_description && (
                  <span className="text-[12px] opacity-80 line-clamp-3">{deal.deal_description}</span>
                )}
                {deal.source_url && (
                  <a
                    href={deal.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[12px] font-medium underline"
                  >
                    View deal
                  </a>
                )}
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
      <div className="absolute bottom-md left-md z-[1000] bg-surface/95 backdrop-blur p-sm rounded-xl border border-line shadow-lg max-w-[220px]">
        <h3 className="font-display text-[15px] font-semibold text-ink">
          {mapped.length} deal{mapped.length === 1 ? "" : "s"} on the map
        </h3>
        {deals.length > mapped.length && (
          <p className="text-[12px] text-ink-dim mt-1">
            {deals.length - mapped.length} more without a location
          </p>
        )}
      </div>
    </aside>
  );
}
