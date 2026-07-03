export default function MapPanel({ dealCount }) {
  return (
    <aside className="hidden lg:block w-full lg:w-1/2 h-full map-container relative">
      <div className="absolute inset-0 bg-surface-container-lowest/50 backdrop-blur-[2px]"></div>
      <div className="absolute bottom-md left-md bg-surface-container p-sm rounded-lg border border-outline-variant shadow-lg max-w-[200px]">
        <h3 className="font-headline-md text-[16px] font-bold text-on-surface">
          {dealCount} deal{dealCount === 1 ? "" : "s"} near you
        </h3>
        <p className="font-body-md text-[12px] text-on-surface-variant mt-1">Map view coming soon</p>
      </div>
    </aside>
  );
}
