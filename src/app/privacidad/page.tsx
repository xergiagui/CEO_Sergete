import type { Metadata } from "next";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: "Privacidad",
  description:
    "Cómo tratamos tus datos en esta página: qué recogemos, para qué y tus derechos.",
  robots: { index: false, follow: true },
};

export default function Privacidad() {
  return (
    <>
      <Nav />
      <main className="mx-auto w-full max-w-2xl flex-1 px-5 py-16">
        <h1 className="font-display text-4xl tracking-tight">Política de privacidad</h1>
        <p className="mt-3 text-sm text-[var(--text-faint)]">
          Última actualización: {new Date().getFullYear()}
        </p>

        <div className="mt-8 flex flex-col gap-6 text-[15px] leading-relaxed text-[var(--text-muted)]">
          <section>
            <h2 className="mb-2 font-display text-xl text-[var(--text)]">
              Qué datos recogemos
            </h2>
            <p>
              Cuando pulsas “Lo quiero” y dejas tu correo, guardamos: tu email, el
              recurso que te interesa y la fecha y hora. Además, de forma anónima,
              medimos visitas y clics (sin cookies de terceros ni datos personales
              identificables más allá del email que nos facilitas).
            </p>
          </section>

          <section>
            <h2 className="mb-2 font-display text-xl text-[var(--text)]">
              Para qué los usamos
            </h2>
            <p>
              Para enviarte información útil sobre el recurso que te interesa y
              posibles ofertas, y para entender qué contenidos funcionan mejor. No
              vendemos ni cedemos tu email a terceros.
            </p>
          </section>

          <section>
            <h2 className="mb-2 font-display text-xl text-[var(--text)]">
              Dónde se almacenan
            </h2>
            <p>
              Los datos se guardan de forma segura en Supabase. El acceso está
              restringido y protegido.
            </p>
          </section>

          <section>
            <h2 className="mb-2 font-display text-xl text-[var(--text)]">Tus derechos</h2>
            <p>
              Puedes solicitar en cualquier momento acceder, rectificar o eliminar
              tus datos, así como darte de baja de las comunicaciones. Escríbenos y
              lo resolvemos.
            </p>
          </section>

          <section>
            <h2 className="mb-2 font-display text-xl text-[var(--text)]">
              Enlaces de afiliado
            </h2>
            <p>
              Esta página recomienda productos de Luis Monje Malo mediante enlaces de
              afiliado. Si compras a través de ellos podemos recibir una comisión sin
              coste adicional para ti.
            </p>
          </section>
        </div>
      </main>
      <Footer />
    </>
  );
}
