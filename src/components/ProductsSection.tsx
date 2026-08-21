"use client";

import { useEffect, useRef, useState } from "react";
import type { Product } from "@/lib/products";
import { track } from "@/lib/analytics";
import LeadModal from "@/components/LeadModal";
import Reveal from "@/components/Reveal";
import { ArrowRight, Check } from "@/components/icons";

function ProductCard({
  product,
  onWant,
}: {
  product: Product;
  onWant: (p: Product) => void;
}) {
  const ref = useRef<HTMLElement | null>(null);

  // Registra que la tarjeta se ha visto (product_view), una vez.
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          track("product_view", product.id);
          io.disconnect();
        }
      },
      { threshold: 0.5 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [product.id]);

  return (
    <article
      ref={ref}
      className="card flex flex-col p-6 sm:p-7"
      style={{ ["--accent" as string]: product.accent }}
    >
      {/* Barra de acento superior */}
      <div
        className="absolute inset-x-6 top-0 h-px"
        style={{
          background: `linear-gradient(90deg, transparent, ${product.accent}, transparent)`,
        }}
      />

      <div className="flex items-center justify-between gap-3">
        <span
          className="pill"
          style={{
            color: product.accentInk,
            borderColor: `color-mix(in oklab, ${product.accent} 40%, var(--border-strong))`,
            background: `color-mix(in oklab, ${product.accent} 8%, transparent)`,
          }}
        >
          {product.kind}
        </span>
        {product.badge && (
          <span
            className="rounded-full px-2.5 py-1 text-[11px] font-semibold"
            style={{
              color: "#0b0f18",
              background: product.accent,
            }}
          >
            {product.badge}
          </span>
        )}
      </div>

      <h3 className="mt-5 font-display text-[1.6rem] leading-[1.15] tracking-tight">
        {product.hook}
      </h3>
      <p className="mt-2 text-[15px] text-[var(--text-muted)]">
        {product.subhook}
      </p>

      <ul className="mt-5 flex flex-col gap-2.5">
        {product.bullets.map((b) => (
          <li key={b} className="flex items-start gap-2.5 text-[14.5px]">
            <span
              className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full"
              style={{ background: `color-mix(in oklab, ${product.accent} 18%, transparent)` }}
            >
              <Check width={13} height={13} style={{ color: product.accent }} />
            </span>
            <span className="text-[var(--text)]/90">{b}</span>
          </li>
        ))}
      </ul>

      <div className="mt-6 flex items-end justify-between gap-4 border-t border-[var(--border)] pt-5">
        <div>
          <p className="text-xs uppercase tracking-wide text-[var(--text-faint)]">
            {product.name}
          </p>
          <p className="mt-0.5 text-lg font-semibold">{product.price}</p>
        </div>
        <button
          onClick={() => onWant(product)}
          className="btn-primary"
          style={{ ["--accent" as string]: product.accent }}
          aria-label={`Lo quiero: ${product.name}`}
        >
          Lo quiero
          <ArrowRight width={17} height={17} />
        </button>
      </div>
    </article>
  );
}

export default function ProductsSection({ products }: { products: Product[] }) {
  const [selected, setSelected] = useState<Product | null>(null);

  const want = (p: Product) => {
    track("cta_click", p.id);
    setSelected(p);
  };

  return (
    <section id="productos" className="relative mx-auto w-full max-w-6xl px-5 py-20 sm:py-28">
      <Reveal className="mx-auto max-w-2xl text-center">
        <span className="pill">Elige tu recurso</span>
        <h2 className="mt-5 font-display text-3xl sm:text-4xl md:text-5xl leading-[1.05] tracking-tight">
          4 formas de empezar a{" "}
          <span className="hl">ganar dinero</span> vendiendo
        </h2>
        <p className="mt-4 text-[var(--text-muted)]">
          Del primer euro como afiliado a cerrar ventas de miles. Elige por dónde
          entrar — pulsa, deja tu email y te llevamos al recurso.
        </p>
      </Reveal>

      <div className="mt-14 grid gap-5 md:grid-cols-2">
        {products.map((p, i) => (
          <Reveal key={p.id} delay={i * 70}>
            <ProductCard product={p} onWant={want} />
          </Reveal>
        ))}
      </div>

      {/* Mini-guía: ¿cuál es para ti? */}
      <Reveal className="mt-14">
        <div className="card overflow-hidden">
          <div className="border-b border-[var(--border)] px-6 py-4">
            <h3 className="font-display text-xl">¿No sabes por cuál empezar?</h3>
            <p className="text-sm text-[var(--text-muted)]">
              Encuentra tu punto de partida en 10 segundos.
            </p>
          </div>
          <ul className="divide-y divide-[var(--border)]">
            {products.map((p) => (
              <li key={p.id}>
                <button
                  onClick={() => want(p)}
                  className="group flex w-full items-center gap-4 px-6 py-4 text-left transition-colors hover:bg-[var(--surface-2)]"
                >
                  <span
                    className="h-2.5 w-2.5 shrink-0 rounded-full"
                    style={{ background: p.accent }}
                  />
                  <span className="flex-1 text-[15px] text-[var(--text)]/90">
                    {p.bestFor}
                  </span>
                  <span className="hidden text-sm font-medium text-[var(--text-muted)] sm:inline">
                    {p.name}
                  </span>
                  <ArrowRight
                    width={16}
                    height={16}
                    className="text-[var(--text-faint)] transition-transform duration-200 ease-out group-hover:translate-x-1"
                  />
                </button>
              </li>
            ))}
          </ul>
        </div>
      </Reveal>

      {selected && (
        <LeadModal product={selected} onClose={() => setSelected(null)} />
      )}
    </section>
  );
}
