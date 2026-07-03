export default function Header() {
  return (
    <header className="fixed top-0 w-full z-50 h-[56px] px-margin-mobile md:px-margin-desktop flex items-center bg-bg/85 backdrop-blur-md border-b border-line">
      <div className="flex items-center gap-sm">
        <span className="grid place-items-center w-8 h-8 rounded-lg bg-brand/15 text-brand">
          <span aria-hidden="true" className="material-symbols-outlined text-[20px]">near_me</span>
        </span>
        <h1 className="font-display text-[18px] font-bold tracking-tight text-ink">
          Local<span className="text-brand">Deal</span>Finder
        </h1>
      </div>
    </header>
  );
}
