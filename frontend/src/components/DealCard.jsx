const CATEGORY_META = {
  food: { icon: "restaurant", label: "Food" },
  grocery: { icon: "shopping_basket", label: "Grocery" },
  electronics: { icon: "devices", label: "Electronics" },
  services: { icon: "medical_services", label: "Services" },
  clothing: { icon: "checkroom", label: "Clothing" },
  software: { icon: "apps", label: "Software" },
  other: { icon: "sell", label: "Other" },
};

const URGENCY_LABELS = {
  limited_time: "Ending Soon",
  ongoing: "Ongoing",
};

function formatPrice(value) {
  const num = Number(value);
  return Number.isFinite(num) ? `$${num.toFixed(2)}` : String(value);
}

export default function DealCard({ deal, onDismiss }) {
  const category = CATEGORY_META[deal.category] || CATEGORY_META.other;
  const title = deal.business_name || category.label + " Deal";
  const hasPrice = deal.price_deal != null;
  const urgencyLabel = URGENCY_LABELS[deal.urgency];

  return (
    <article className="w-full rounded-lg p-md card-shadow flex flex-col gap-xs relative overflow-hidden group">
      <div className="absolute top-0 right-0 w-32 h-32 bg-primary opacity-5 rounded-full blur-2xl group-hover:opacity-10 transition-opacity"></div>

      {/* Header: title, price, category */}
      <div className="flex flex-col gap-xs z-10 relative">
        <h2 className="font-headline-md text-headline-md font-bold text-on-surface truncate">{title}</h2>
        {hasPrice && (
          <div className="bg-primary-container text-on-primary-container font-data-point text-xs px-2 py-0.5 rounded-md shadow-sm border border-primary flex items-baseline gap-xs w-fit mt-xs">
            {formatPrice(deal.price_deal)}
            {deal.price_original != null && (
              <span className="line-through text-on-primary-container opacity-60 font-body-md text-sm">
                {formatPrice(deal.price_original)}
              </span>
            )}
          </div>
        )}
        {!hasPrice && deal.discount_label && (
          <div className="bg-secondary-container text-on-secondary-container font-data-point text-xs px-2 py-0.5 rounded-md shadow-sm border border-secondary flex items-baseline w-fit mt-xs">
            {deal.discount_label}
          </div>
        )}
        <span className="font-label-caps text-label-caps text-tertiary uppercase tracking-widest flex items-center gap-xs">
          <span aria-hidden="true" className="material-symbols-outlined text-[14px]">{category.icon}</span> {category.label}
        </span>
      </div>

      {/* Description */}
      {deal.deal_description && (
        <p className="font-body-md text-body-md text-on-surface-variant line-clamp-2 z-10 relative mt-xs">
          {deal.deal_description}
        </p>
      )}

      {/* Badges */}
      <div className="flex flex-wrap gap-base mt-sm z-10 relative">
        {deal.scope && (
          <span className="inline-flex items-center gap-xs bg-surface-container-highest text-on-surface font-label-caps text-[10px] px-2 py-1 rounded-sm border border-outline-variant">
            <span aria-hidden="true" className="material-symbols-outlined text-[12px]">
              {deal.scope === "online" ? "language" : "storefront"}
            </span>
            {deal.scope.toUpperCase()}
          </span>
        )}
        {urgencyLabel === "Ending Soon" && (
          <span className="inline-flex items-center gap-xs bg-error-container/20 text-error font-label-caps text-[10px] px-2 py-1 rounded-sm border border-error/30">
            <span aria-hidden="true" className="material-symbols-outlined text-[12px]">timer</span> ENDING SOON
          </span>
        )}
        {urgencyLabel === "Ongoing" && (
          <span className="inline-flex items-center gap-xs bg-tertiary/10 text-tertiary font-label-caps text-[10px] px-2 py-1 rounded-sm border border-tertiary/30">
            <span aria-hidden="true" className="material-symbols-outlined text-[12px]">event</span> ONGOING
          </span>
        )}
        {hasPrice && deal.discount_label && (
          <span className="inline-flex items-center gap-xs bg-primary/10 text-primary font-label-caps text-[10px] px-2 py-1 rounded-sm border border-primary/30">
            {deal.discount_label.toUpperCase()}
          </span>
        )}
      </div>

      {/* Footer: peer comparison + actions */}
      <div className="mt-auto flex justify-between items-center border-t border-surface-container-highest pt-sm z-10 relative">
        <div className="flex flex-col">
          {deal.vs_peers && (
            <span className="font-body-md text-[12px] text-outline flex items-center gap-xs">
              <span aria-hidden="true" className="material-symbols-outlined text-[14px]">trending_down</span> {deal.vs_peers}
            </span>
          )}
        </div>
        <div className="flex gap-xs">
          <button
            onClick={() => onDismiss(deal.id)}
            aria-label={`Dismiss deal from ${title}`}
            className="bg-surface-container border border-outline-variant text-on-surface hover:bg-surface-container-high font-body-md text-sm px-sm py-xs rounded-full transition-colors flex items-center justify-center"
          >
            <span aria-hidden="true" className="material-symbols-outlined text-[18px]">close</span>
          </button>
          {deal.source_url && (
            <a
              href={deal.source_url}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`View deal from ${title} (opens in new tab)`}
              className="bg-primary text-on-primary hover:bg-primary-fixed-dim font-label-caps text-label-caps px-sm py-xs rounded-full transition-colors flex items-center gap-xs"
            >
              VIEW <span aria-hidden="true" className="material-symbols-outlined text-[16px]">arrow_forward</span>
            </a>
          )}
        </div>
      </div>
    </article>
  );
}
