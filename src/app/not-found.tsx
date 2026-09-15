import type { Metadata } from "next";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import { ArrowRight } from "@/components/icons";

export const metadata: Metadata = {
  title: "Página no encontrada",
  description: "La página que buscas no existe o se ha movido.",
};

export default function NotFound() {
  return (
    <>
      <Nav />
      <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col items-center justify-center px-5 py-24 text-center">
        <span
          className="font-display text-[clamp(4rem,18vw,8rem)] font-semibold leading-none tracking-tight"
          style={{ color: "var(--gold-ink)" }}
          aria-hidden="true"
        >
          404
        </span>
        <h1 className="mt-4 font-display text-3xl tracking-tight sm:text-4xl">
          Esta página se ha perdido
        </h1>
        <p className="mx-auto mt-3 max-w-md text-[15px] leading-relaxed text-[var(--text-muted)]">
          El enlace que seguiste no existe o el recurso se ha movido. Vuelve al
          inicio y elige tu recurso en 30 segundos.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <a href="/" className="btn-primary">
            Volver al inicio
            <ArrowRight width={18} height={18} />
          </a>
          <a href="/#productos" className="btn-ghost">
            Ver los recursos
          </a>
        </div>
      </main>
      <Footer />
    </>
  );
}
