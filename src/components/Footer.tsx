export default function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="mt-auto border-t border-[var(--border)] px-5 py-10">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
        <div className="max-w-md">
          <div className="flex items-center gap-2.5">
            <span
              className="grid h-7 w-7 place-items-center rounded-md font-display text-[13px] font-semibold"
              style={{ background: "var(--gold)", color: "#1a1206" }}
            >
              M
            </span>
            <span className="text-sm font-semibold">Selección · Monje Malo</span>
          </div>
          <p className="mt-3 text-xs leading-relaxed text-[var(--text-faint)]">
            <strong className="text-[var(--text-muted)]">Aviso de afiliación:</strong>{" "}
            esta página recomienda productos de Luis Monje Malo. Al comprar a través
            de nuestros enlaces podemos recibir una comisión, sin coste adicional
            para ti. No representamos oficialmente a la marca.
          </p>
        </div>
        <div className="flex flex-col gap-2 text-sm text-[var(--text-muted)]">
          <a href="#productos" className="transition-colors hover:text-[var(--text)]">
            Recursos
          </a>
          <a href="#faq" className="transition-colors hover:text-[var(--text)]">
            Preguntas frecuentes
          </a>
          <a href="/privacidad" className="transition-colors hover:text-[var(--text)]">
            Privacidad
          </a>
        </div>
      </div>
      <p className="mx-auto mt-8 w-full max-w-6xl text-xs text-[var(--text-faint)]">
        © {year} · Hecho con criterio. Todos los productos pertenecen a sus
        respectivos autores.
      </p>
    </footer>
  );
}
