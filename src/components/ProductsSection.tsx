"use client";

import { useEffect, useRef, useState } from "react";
import type { Product } from "@/lib/products";
import { track } from "@/lib/analytics";
import LeadModal from "@/components/LeadModal";
import Reveal from "@/components/Reveal";
import { ArrowRight, Check, Bolt } from "@/components/icons";

// Registra que una tarjeta se ha visto (product_view), una sola vez.
function useProductView(id: string) {
  const ref = useRef<HTMLElement | null>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          track("product_view", id);
          io.disconnect();
        }
      },
      { threshold: 0.4 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [id]);
  return ref;
}

// Tarjeta destacada (buque insignia) — ocupa el ancho completo, encima del
// grid. Layout horizontal en desktop, apilado en móvil. Mismo sistema de
// diseño (.card, .pill, .btn-primary, font-display) y misma lógica de tracking.
function FeaturedProductCard({
  product,
  onWant,
}: {
  product: Product;
  onWant: (p: Product) => void;
}) {
  const ref = useProductView(product.id);

  return (
    <article
      ref={ref}
      className="card overflow-hidden p-7 sm:p-9 lg:p-10"
      style={{
        ["--accent" as string]: product.accent,
        borderColor: `color-mix(in oklab, ${product.accent} 45%, var(--border-strong))`,
        background: `
          radial-gradient(120% 140% at 100% 0%, color-mix(in oklab, ${product.accent} 12%, transparent), transparent 60%),
          linear-gradient(180deg, var(--surface) 0%, var(--bg-2) 140%)`,
      }}
    >
      {/* Barra de acento superior más marcada */}
      <div
        className="absolute inset-x-0 top-0 h-[3px]"
        style={{
          background: `linear-gradient(90deg, transparent, ${product.accent}, transparent)`,
        }}
      />

      <div className="flex flex-col gap-8 lg:flex-row lg:items-center lg:gap-10">
        {/* Izquierda: texto + bullets */}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-3">
            <span
              className="pill"
              style={{
                color: product.accentInk,
                borderColor: `color-mix(in oklab, ${product.accent} 45%, var(--border-strong))`,
                background: `color-mix(in oklab, ${product.accent} 10%, transparent)`,
              }}
            >
              <Bolt width={13} height={13} style={{ color: product.accent }} />
              {product.kind}
            </span>
            {product.badge && (
              <span
                className="inline-flex items-center rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-wide"
                style={{ color: "#fff", background: product.accent }}
              >
                {product.badge}
              </span>
            )}
          </div>

          <h3 className="mt-5 font-display text-[2rem] leading-[1.1] tracking-tight sm:text-[2.5rem]">
            {product.hook}
          </h3>
          <p className="mt-3 max-w-2xl text-[16px] text-[var(--text-muted)]">
            {product.subhook}
          </p>

          <ul className="mt-6 grid gap-2.5 sm:grid-cols-2">
            {product.bullets.map((b) => (
              <li key={b} className="flex items-start gap-2.5 text-[14.5px]">
                <span
                  className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full"
                  style={{ background: `color-mix(in oklab, ${product.accent} 20%, transparent)` }}
                >
                  <Check width={13} height={13} style={{ color: product.accent }} />
                </span>
                <span className="text-[var(--text)]/90">{b}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Derecha: precio + CTA grande */}
        <div className="flex shrink-0 flex-col gap-4 lg:w-64 lg:items-stretch lg:border-l lg:border-[var(--border)] lg:pl-10">
          <div>
            <p className="text-xs uppercase tracking-wide text-[var(--text-faint)]">
              {product.name}
            </p>
            <p className="mt-1 text-2xl font-semibold leading-tight">
              {product.price}
            </p>
          </div>
          <button
            onClick={() => onWant(product)}
            className="btn-primary w-full !py-4 text-base"
            style={{ ["--accent" as string]: product.accent, color: "#fff" }}
            aria-label={`Lo quiero: ${product.name}`}
          >
            Lo quiero
            <ArrowRight width={18} height={18} />
          </button>
        </div>
      </div>
    </article>
  );
}

function ProductCard({
  product,
  onWant,
}: {
  product: Product;
  onWant: (p: Product) => void;
}) {
  const ref = useProductView(product.id);

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

  const featured = products.find((p) => p.id === "grupo-alfa");
  const rest = products.filter((p) => p.id !== "grupo-alfa");

  return (
    <section id="productos" className="relative mx-auto w-full max-w-6xl px-5 py-20 sm:py-28">
      <Reveal className="mx-auto max-w-2xl text-center">
        <span className="pill">Elige tu recurso</span>
        <h2 className="mt-5 font-display text-3xl sm:text-4xl md:text-5xl leading-[1.05] tracking-tight">
          5 formas de empezar a{" "}
          <span className="hl">aprender a vender</span> online
        </h2>
        <p className="mt-4 text-[var(--text-muted)]">
          De dar tus primeros pasos como afiliado a cerrar ventas con método. Elige por dónde
          entrar — pulsa, deja tu email y te llevamos al recurso.
        </p>
      </Reveal>

      {/* Buque insignia: tarjeta destacada a lo ancho, encima de la parrilla */}
      {featured && (
        <Reveal className="mt-14">
          <FeaturedProductCard product={featured} onWant={want} />
        </Reveal>
      )}

      <div className="mt-5 grid gap-5 md:grid-cols-2">
        {rest.map((p, i) => (
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
