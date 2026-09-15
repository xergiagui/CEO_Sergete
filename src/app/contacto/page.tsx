import type { Metadata } from "next";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import ContactForm from "@/components/ContactForm";

export const metadata: Metadata = {
  title: "Contacto",
  description: "¿Tienes una duda? Escríbenos y te respondemos.",
  alternates: { canonical: "/contacto" },
};

export default function Contacto() {
  return (
    <>
      <Nav />
      <main className="mx-auto w-full max-w-2xl flex-1 px-5 py-16">
        <h1 className="font-display text-4xl tracking-tight">Contacto</h1>
        <p className="mt-3 text-[var(--text-muted)]">
          ¿Una duda sobre alguno de los recursos o sobre tus datos? Escríbenos y te
          respondemos al email que nos dejes.
        </p>
        <div className="mt-8">
          <ContactForm />
        </div>
      </main>
      <Footer />
    </>
  );
}
