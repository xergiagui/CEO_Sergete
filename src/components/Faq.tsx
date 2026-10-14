import Reveal from "@/components/Reveal";

export const FAQS = [
  {
    q: "¿Qué es exactamente esto?",
    a: "Una selección de los 5 recursos de Luis Monge Malo para aprender a vender online. Cada uno resuelve un momento distinto: empezar de cero, entender el modelo, cerrar más ventas, rodearte de una comunidad ambiciosa con mentoría diaria o tener acompañamiento continuo.",
  },
  {
    q: "¿Necesito experiencia previa?",
    a: "No. La Escuela de Afiliados está pensada para empezar desde cero, sin producto propio ni inversión. El resto de recursos te sirven a medida que avanzas.",
  },
  {
    q: "¿Cuánto cuesta y qué recibo?",
    a: "Desde 49 €/mes (Escuela de Afiliados) hasta la Mentoría desde 200 €. Al pulsar un recurso te llevamos a su página oficial, donde ves el detalle completo y compras con total seguridad.",
  },
  {
    q: "¿Por qué me pedís el email?",
    a: "Solo para enviarte información útil relacionada con el recurso que te interesa y avisarte de ofertas. Sin spam y con baja en un clic cuando quieras.",
  },
  {
    q: "¿Quién es Luis Monge Malo?",
    a: "Uno de los mayores referentes en ventas y marketing de afiliación en español, con miles de alumnos. Los recursos de esta página son suyos; aquí solo te ayudamos a elegir el que mejor encaja contigo.",
  },
];

export default function Faq() {
  return (
    <section id="faq" className="mx-auto w-full max-w-3xl px-5 py-20 sm:py-24">
      <Reveal className="text-center">
        <span className="pill">Preguntas frecuentes</span>
        <h2 className="mt-5 font-display text-3xl sm:text-4xl tracking-tight">
          Lo que quieres saber antes de empezar
        </h2>
      </Reveal>

      <div className="mt-10 flex flex-col gap-3">
        {FAQS.map((f, i) => (
          <Reveal key={f.q} delay={i * 50}>
            <details className="card group px-5 py-4 [&_summary]:cursor-pointer">
              <summary className="flex list-none items-center justify-between gap-4 font-medium">
                {f.q}
                <span className="text-[var(--text-faint)] transition-transform duration-200 ease-out group-open:rotate-45">
                  +
                </span>
              </summary>
              <p className="mt-3 text-[15px] leading-relaxed text-[var(--text-muted)]">
                {f.a}
              </p>
            </details>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
