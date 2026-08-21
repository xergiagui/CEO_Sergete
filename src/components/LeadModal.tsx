"use client";

import { useEffect, useRef, useState } from "react";
import type { Product } from "@/lib/products";
import { getAttribution, getSessionId, track } from "@/lib/analytics";
import { ArrowRight, Check, Close, Lock } from "@/components/icons";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function LeadModal({
  product,
  onClose,
}: {
  product: Product;
  onClose: () => void;
}) {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "error" | "done">(
    "idle"
  );
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!EMAIL_RE.test(email.trim())) {
      setError("Escribe un email válido.");
      setStatus("error");
      return;
    }
    setStatus("loading");
    setError("");

    const attr = getAttribution();
    const payload = {
      email: email.trim(),
      product_id: product.id,
      session_id: getSessionId(),
      path: window.location.pathname,
      ...attr,
    };

    try {
      const res = await fetch("/api/lead", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        throw new Error(data.error || "error");
      }
      setStatus("done");
      track("affiliate_redirect", product.id);
      // Pequeña pausa para que el usuario vea la confirmación.
      const dest = data.redirect || product.href;
      setTimeout(() => {
        window.location.href = dest;
      }, 650);
    } catch {
      setStatus("error");
      setError("Algo falló. Inténtalo de nuevo.");
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 backdrop-in"
      style={{ background: "rgba(4,6,12,0.72)", backdropFilter: "blur(6px)" }}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="lead-title"
    >
      <div
        className="modal-in w-full max-w-md card p-7"
        style={{ ["--accent" as string]: product.accent }}
      >
        <div className="flex items-start justify-between gap-4">
          <span
            className="pill"
            style={{
              color: product.accent,
              borderColor: `color-mix(in oklab, ${product.accent} 45%, var(--border-strong))`,
            }}
          >
            {product.kind} · {product.price}
          </span>
          <button
            onClick={onClose}
            aria-label="Cerrar"
            className="text-[var(--text-faint)] hover:text-[var(--text)] transition-colors"
          >
            <Close width={20} height={20} />
          </button>
        </div>

        {status === "done" ? (
          <div className="py-6 text-center">
            <div
              className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full"
              style={{ background: `color-mix(in oklab, ${product.accent} 22%, transparent)` }}
            >
              <Check width={26} height={26} style={{ color: product.accent }} />
            </div>
            <p className="font-display text-2xl">¡Hecho!</p>
            <p className="mt-1 text-[var(--text-muted)]">
              Te llevamos a {product.name}…
            </p>
          </div>
        ) : (
          <>
            <h2 id="lead-title" className="mt-4 font-display text-2xl leading-tight">
              A un paso de {product.name}
            </h2>
            <p className="mt-2 text-[15px] text-[var(--text-muted)]">
              Déjanos tu email y te llevamos directo al recurso.
            </p>

            <form onSubmit={submit} className="mt-5">
              <label htmlFor="email" className="sr-only">
                Tu email
              </label>
              <input
                ref={inputRef}
                id="email"
                type="email"
                inputMode="email"
                autoComplete="email"
                placeholder="tu@email.com"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (status === "error") setStatus("idle");
                }}
                className="w-full rounded-xl border bg-[var(--bg-2)] px-4 py-3 text-[var(--text)] placeholder:text-[var(--text-faint)] outline-none transition-colors focus:border-[color-mix(in_oklab,var(--accent)_60%,var(--border-strong))]"
                style={{ borderColor: "var(--border-strong)" }}
                aria-invalid={status === "error"}
              />
              {status === "error" && (
                <p className="mt-2 text-sm text-[var(--rose)]">{error}</p>
              )}

              <button
                type="submit"
                disabled={status === "loading"}
                className="btn-primary mt-4 w-full disabled:opacity-70"
              >
                {status === "loading" ? (
                  "Un momento…"
                ) : (
                  <>
                    Ir al recurso
                    <ArrowRight width={18} height={18} />
                  </>
                )}
              </button>
            </form>

            <p className="mt-4 flex items-center justify-center gap-1.5 text-xs text-[var(--text-faint)]">
              <Lock width={13} height={13} />
              Sin spam. Solo información útil. Puedes darte de baja cuando quieras.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
