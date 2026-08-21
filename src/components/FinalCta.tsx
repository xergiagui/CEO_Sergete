import Reveal from "@/components/Reveal";
import { ArrowRight } from "@/components/icons";

export default function FinalCta() {
  return (
    <section className="px-5 pb-24">
      <Reveal>
        <div className="bg-aura relative mx-auto max-w-4xl overflow-hidden rounded-3xl border border-[var(--border-strong)] px-6 py-14 text-center sm:px-12 sm:py-20">
          <h2 className="mx-auto max-w-2xl font-display text-3xl sm:text-4xl md:text-5xl leading-[1.05] tracking-tight">
            Dentro de un año desearás haber empezado{" "}
            <span className="text-[var(--gold)]">hoy</span>.
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-[var(--text-muted)]">
            Elige tu recurso, deja tu email y da el primer paso. Se tarda menos en
            empezar que en seguir dudando.
          </p>
          <div className="mt-8">
            <a href="#productos" className="btn-primary">
              Elegir mi recurso
              <ArrowRight width={18} height={18} />
            </a>
          </div>
        </div>
      </Reveal>
    </section>
  );
}
