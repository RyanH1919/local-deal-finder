import { useState } from "react";
import { parseProducts } from "../utils/deals";

const CATEGORY_META = {
  food: { icon: "restaurant", label: "Food" },
  grocery: { icon: "shopping_basket", label: "Grocery" },
  electronics: { icon: "devices", label: "Electronics" },
  services: { icon: "medical_services", label: "Services" },
  clothing: { icon: "checkroom", label: "Clothing" },
  software: { icon: "apps", label: "Software" },
  other: { icon: "sell", label: "Other" },
};

function formatPrice(value) {
  const num = Number(value);
  return Number.isFinite(num) ? `$${num.toFixed(2)}` : String(value);
}

function UrgencyChip({ urgency }) {
  if (urgency === "limited_time") {
    return (
      <span className="inline-flex items-center gap-xs shrink-0 rounded-full bg-warn/10 border border-warn/25 text-warn text-[11px] font-medium px-sm py-[2px]">
        <span aria-hidden="true" className="material-symbols-outlined text-[13px]">timer</span>
        Ending soon
      </span>
    );
  }
  if (urgency === "ongoing") {
    return (
      <span className="inline-flex items-center gap-xs shrink-0 rounded-full bg-good/10 border border-good/20 text-good text-[11px] font-medium px-sm py-[2px]">
        <span aria-hidden="true" className="material-symbols-outlined text-[13px]">event_repeat</span>
        Ongoing
      </span>
    );
  }
  return null;
}

function PeerNote({ text }) {
  const below = text.includes("below");
  const above = text.includes("above");
  return (
    <span className={`inline-flex items-center gap-xs text-[12px] ${below ? "text-good" : above ? "text-warn" : "text-ink-dim"}`}>
      <span aria-hidden="true" className="material-symbols-outlined text-[14px]">
        {below ? "trending_down" : above ? "trending_up" : "trending_flat"}
      </span>
      {text}
    </span>
  );
}

function ProductList({ products }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-xs">
      <button
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="flex items-center gap-xs text-[12px] font-medium text-ink-dim hover:text-ink transition-colors"
      >
        <span aria-hidden="true" className="material-symbols-outlined text-[16px]">
          {open ? "expand_less" : "expand_more"}
        </span>
        {products.length} priced item{products.length === 1 ? "" : "s"}
      </button>
      {open && (
        <ul className="mt-xs flex flex-col gap-xs list-none p-0 m-0 border-l border-line-2 pl-sm">
          {products.map((p, i) => (
            <li key={i} className="flex flex-col">
              <div className="flex justify-between items-baseline gap-sm">
                <span className="text-sm text-ink">{p.name}</span>
                <span className="font-mono text-[13px] text-brand whitespace-nowrap">
                  {p.price}
                  {p.price_original && (
                    <span className="line-through opacity-60 font-body text-[12px] ml-1 text-ink-dim">
                      {p.price_original}
                    </span>
                  )}
                </span>
              </div>
              {(p.discount || p.vs_peers) && (
                <span className="text-[11px] text-ink-faint">
                  {[p.discount, p.vs_peers].filter(Boolean).join(" · ")}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function DealCard({ deal, onDismiss }) {
  const category = CATEGORY_META[deal.category] || CATEGORY_META.other;
  const title = deal.business_name || category.label + " Deal";
  const hasPrice = deal.price_deal != null;
  const products = parseProducts(deal.products);

  return (
    <article className="w-full rounded-xl border border-line bg-surface p-md flex flex-col gap-xs transition-all duration-200 hover:border-line-2 hover:-translate-y-0.5">
      {/* Meta row: category / scope + urgency */}
      <div className="flex items-center justify-between gap-sm">
        <span className="inline-flex items-center gap-xs font-mono text-[11px] uppercase tracking-[0.12em] text-ink-faint">
          <span aria-hidden="true" className="material-symbols-outlined text-[14px]">{category.icon}</span>
          {category.label}
          {deal.scope && <span>· {deal.scope}</span>}
        </span>
        <UrgencyChip urgency={deal.urgency} />
      </div>

      {/* Title */}
      <h2 className="font-display text-[18px] font-semibold text-ink leading-snug truncate" title={title}>
        {title}
      </h2>

      {/* Price line */}
      {hasPrice ? (
        <div className="flex items-baseline gap-sm flex-wrap">
          <span className="font-mono text-[20px] font-semibold text-brand">{formatPrice(deal.price_deal)}</span>
          {deal.price_original != null && (
            <span className="line-through text-ink-faint text-sm">{formatPrice(deal.price_original)}</span>
          )}
          {deal.discount_label && (
            <span className="rounded-full bg-brand/10 border border-brand/25 text-brand text-[11px] font-medium px-sm py-[2px]">
              {deal.discount_label}
            </span>
          )}
        </div>
      ) : (
        deal.discount_label && (
          <span className="font-display text-[16px] font-semibold text-brand">{deal.discount_label}</span>
        )
      )}

      {/* Description */}
      {deal.deal_description && (
        <p className="text-sm text-ink-dim leading-relaxed line-clamp-2">{deal.deal_description}</p>
      )}

      {/* Priced items */}
      {products.length > 0 && <ProductList products={products} />}

      {/* Footer */}
      <div className="mt-auto pt-sm border-t border-line flex justify-between items-center gap-sm">
        <div className="min-w-0">{deal.vs_peers && <PeerNote text={deal.vs_peers} />}</div>
        <div className="flex gap-xs shrink-0">
          <button
            onClick={() => onDismiss(deal.id)}
            aria-label={`Dismiss deal from ${title}`}
            className="grid place-items-center w-8 h-8 rounded-lg text-ink-faint hover:text-ink hover:bg-surface-3 transition-colors"
          >
            <span aria-hidden="true" className="material-symbols-outlined text-[18px]">close</span>
          </button>
          {deal.source_url && (
            <a
              href={deal.source_url}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`View deal from ${title} (opens in new tab)`}
              className="inline-flex items-center gap-xs h-8 px-sm rounded-lg bg-brand text-on-brand hover:bg-brand-hi text-[13px] font-semibold transition-colors"
            >
              View deal
              <span aria-hidden="true" className="material-symbols-outlined text-[15px]">arrow_outward</span>
            </a>
          )}
        </div>
      </div>
    </article>
  );
}
