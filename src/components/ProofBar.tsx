const CLAIMS = [
  "Sin crear producto propio",
  "Basado en +7.000 conversaciones de venta reales",
  "Empiezas sin inversión",
  "Formación del nº1 en afiliación en español",
  "Comunidad de +1.000 miembros activos",
  "Método replicable y predecible",
];

export default function ProofBar() {
  return (
    <section aria-label="Motivos para confiar" className="border-y border-[var(--border)] py-5">
      <div className="marquee-mask overflow-hidden">
        <div className="marquee-track gap-3">
          {[...CLAIMS, ...CLAIMS].map((c, i) => (
            <span
              key={i}
              className="whitespace-nowrap rounded-full border border-[var(--border-strong)] bg-[var(--surface)]/50 px-4 py-2 text-sm text-[var(--text-muted)]"
            >
              {c}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
