import type { ReactNode } from "react";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";

export const SITE_LINK = "https://the-landing-ten.vercel.app/";
const LINK =
  "font-medium text-[var(--azure)] underline underline-offset-2 rounded-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--azure)]";

export function LegalShell({ title, children }: { title: string; children: ReactNode }) {
  return (
    <>
      <Nav />
      <main className="mx-auto w-full max-w-2xl flex-1 px-5 py-16">
        <h1 className="font-display text-4xl tracking-tight">{title}</h1>
        <div className="mt-8 flex flex-col gap-4 text-[15px] leading-relaxed text-[var(--text-muted)]">
          {children}
        </div>
      </main>
      <Footer />
    </>
  );
}

export function Site() {
  return (
    <a href={SITE_LINK} className={`${LINK} break-words`}>
      {SITE_LINK}
    </a>
  );
}

export function A({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a href={href} className={LINK}>
      {children}
    </a>
  );
}

export function H2({ id, children }: { id?: string; children: ReactNode }) {
  return (
    <h2 id={id} className="mt-4 scroll-mt-24 font-display text-xl text-[var(--text)]">
      {children}
    </h2>
  );
}

export function H3({ id, children }: { id?: string; children: ReactNode }) {
  return (
    <h3 id={id} className="mt-2 scroll-mt-24 font-display text-lg text-[var(--text)]">
      {children}
    </h3>
  );
}

export function UL({ children }: { children: ReactNode }) {
  return <ul className="list-disc space-y-2 pl-6">{children}</ul>;
}

export function OL({ children }: { children: ReactNode }) {
  return <ol className="list-decimal space-y-2 pl-6">{children}</ol>;
}

export function Strong({ children }: { children: ReactNode }) {
  return <strong className="font-semibold text-[var(--text)]">{children}</strong>;
}

export function Identificativos() {
  return (
    <>
      <p>El responsable y titular de este sitio web es:</p>
      <UL>
        <li>
          <Strong>Nombre:</Strong> Sergio Aguilar Mañas
        </li>
        <li>
          <Strong>Domicilio Social:</Strong> Calle Madrid 129, 4ºA Getafe (Madrid)
        </li>
        <li>
          <Strong>Actividad de la página web</Strong>: divulgación de contenido
          informativo relativo a las opiniones y reviews sobre cursos online y
          recomendación de productos mediante marketing de afiliación.
        </li>
        <li>
          <Strong>Correo electrónico</Strong>:{" "}
          <A href="mailto:xergiagui.ventas@gmail.com">xergiagui.ventas@gmail.com</A>
        </li>
      </UL>
    </>
  );
}
