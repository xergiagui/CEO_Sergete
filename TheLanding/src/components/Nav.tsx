import Link from "next/link";

export default function Nav() {
  return (
    <header className="sticky top-0 z-40 border-b border-[var(--border)]/70 bg-[color-mix(in_oklab,var(--bg)_78%,transparent)] backdrop-blur-md">
      <nav className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-5">
        <Link href="/#top" className="flex items-center gap-2.5" aria-label="Inicio">
          <span
            className="grid h-8 w-8 place-items-center rounded-lg font-display text-[15px] font-semibold"
            style={{ background: "var(--gold)", color: "#1a1206" }}
          >
            M
          </span>
          <span className="text-[15px] font-semibold tracking-tight">
            Selección <span className="text-[var(--text-faint)]">· Monge Malo</span>
          </span>
        </Link>
        <Link href="/#productos" className="btn-ghost !py-2 !px-4 text-sm">
          Ver recursos
        </Link>
      </nav>
    </header>
  );
}
