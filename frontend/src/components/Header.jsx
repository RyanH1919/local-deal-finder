export default function Header() {
  return (
    <header className="glass-header fixed top-0 w-full z-50 px-margin-mobile md:px-margin-desktop py-sm flex flex-row items-center justify-between">
      <h1 className="font-headline-md text-headline-md font-bold text-primary tracking-tight">
        <span className="text-primary-container">L</span>ocal<span className="text-primary-container">D</span>eal<span className="text-primary-container">F</span>inder
      </h1>
    </header>
  );
}
