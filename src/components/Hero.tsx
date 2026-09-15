import Reveal from "@/components/Reveal";
import { ArrowRight, Bolt } from "@/components/icons";

export default function Hero() {
  return (
    <section
      id="top"
      className="bg-aura relative overflow-hidden px-5 pt-16 pb-16 sm:pt-24 sm:pb-24"
    >
      <div className="mx-auto max-w-3xl text-center">
        <Reveal>
          <span className="pill">
            <Bolt width={13} height={13} style={{ color: "var(--gold)" }} />
            Recursos de Luis Monge Malo · nº1 en ventas y afiliación
          </span>
        </Reveal>

        <Reveal delay={80}>
          <h1 className="mt-6 font-display text-[2.6rem] leading-[1.03] tracking-tight sm:text-6xl md:text-[4.25rem]">
            El dinero no llega por suerte.
            <br className="hidden sm:block" /> Llega cuando aprendes a{" "}
            <span className="relative whitespace-nowrap hl">vender.</span>
          </h1>
        </Reveal>

        <Reveal delay={150}>
          <p className="mx-auto mt-6 max-w-xl text-lg text-[var(--text-muted)]">
            He reunido los <strong className="text-[var(--text)]">5 recursos</strong>{" "}
            con los que cualquiera puede empezar hoy: desde tu primer euro como
            afiliado hasta cerrar ventas de miles. Elige el tuyo en 30 segundos.
          </p>
        </Reveal>

        <Reveal delay={220}>
          <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <a href="#productos" className="btn-primary w-full sm:w-auto">
              Ver los 5 recursos
              <ArrowRight width={18} height={18} />
            </a>
            <a href="#faq" className="btn-ghost w-full sm:w-auto">
              ¿Cuál es para mí?
            </a>
          </div>
        </Reveal>

        <Reveal delay={300}>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-x-7 gap-y-3 text-sm text-[var(--text-muted)]">
            <span className="flex items-center gap-2">
              <span className="text-[var(--gold)]">★★★★★</span> Método probado
            </span>
            <span className="hidden h-4 w-px bg-[var(--border-strong)] sm:block" />
            <span>+1.000 alumnos en la comunidad</span>
            <span className="hidden h-4 w-px bg-[var(--border-strong)] sm:block" />
            <span>Sin experiencia previa</span>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
