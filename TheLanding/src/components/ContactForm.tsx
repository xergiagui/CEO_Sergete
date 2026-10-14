"use client";

import { useState } from "react";
import { getSessionId } from "@/lib/analytics";
import { ArrowRight, Check } from "@/components/icons";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function ContactForm() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "error" | "done">("idle");
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!EMAIL_RE.test(email.trim())) {
      setError("Escribe un email válido para poder responderte.");
      setStatus("error");
      return;
    }
    if (message.trim().length < 5) {
      setError("Cuéntanos un poco más en el mensaje.");
      setStatus("error");
      return;
    }
    setStatus("loading");
    setError("");
    try {
      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim(),
          message: message.trim(),
          session_id: getSessionId(),
        }),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || "error");
      setStatus("done");
    } catch {
      setStatus("error");
      setError("No se pudo enviar. Inténtalo de nuevo en un momento.");
    }
  }

  if (status === "done") {
    return (
      <div className="card p-7 text-center">
        <div
          className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full"
          style={{ background: "color-mix(in oklab, var(--emerald) 16%, transparent)" }}
        >
          <Check width={26} height={26} style={{ color: "var(--emerald)" }} />
        </div>
        <p className="font-display text-2xl">¡Mensaje enviado!</p>
        <p className="mt-1 text-[var(--text-muted)]">
          Te responderemos al email que nos has dejado lo antes posible.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="card p-6 sm:p-7">
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="c-name" className="mb-1.5 block text-sm font-medium">
            Nombre <span className="text-[var(--text-faint)]">(opcional)</span>
          </label>
          <input
            id="c-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Tu nombre"
            className="w-full rounded-xl border border-[var(--border-strong)] bg-[var(--bg-2)] px-4 py-3 outline-none transition-colors focus:border-[var(--gold)]"
          />
        </div>
        <div>
          <label htmlFor="c-email" className="mb-1.5 block text-sm font-medium">
            Email
          </label>
          <input
            id="c-email"
            type="email"
            inputMode="email"
            autoComplete="email"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              if (status === "error") setStatus("idle");
            }}
            placeholder="tu@email.com"
            className="w-full rounded-xl border border-[var(--border-strong)] bg-[var(--bg-2)] px-4 py-3 outline-none transition-colors focus:border-[var(--gold)]"
          />
        </div>
      </div>

      <div className="mt-4">
        <label htmlFor="c-msg" className="mb-1.5 block text-sm font-medium">
          Mensaje
        </label>
        <textarea
          id="c-msg"
          rows={5}
          value={message}
          onChange={(e) => {
            setMessage(e.target.value);
            if (status === "error") setStatus("idle");
          }}
          placeholder="¿En qué podemos ayudarte?"
          className="w-full resize-y rounded-xl border border-[var(--border-strong)] bg-[var(--bg-2)] px-4 py-3 outline-none transition-colors focus:border-[var(--gold)]"
        />
      </div>

      {status === "error" && (
        <p className="mt-3 text-sm text-[var(--rose)]">{error}</p>
      )}

      <button
        type="submit"
        disabled={status === "loading"}
        className="btn-primary mt-5 w-full disabled:opacity-70 sm:w-auto"
      >
        {status === "loading" ? (
          "Enviando…"
        ) : (
          <>
            Enviar mensaje
            <ArrowRight width={18} height={18} />
          </>
        )}
      </button>

      <p className="mt-4 text-xs text-[var(--text-faint)]">
        Al continuar aceptas la{" "}
        <a
          href="/privacidad"
          className="underline underline-offset-2 transition-colors hover:text-[var(--text)]"
        >
          política de privacidad
        </a>
        .
      </p>
    </form>
  );
}
