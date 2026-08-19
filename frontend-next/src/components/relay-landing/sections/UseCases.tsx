import { Reveal } from "@/components/relay-landing/ui/Reveal";
import { SectionLabel } from "@/components/relay-landing/ui/SectionLabel";

const cases = [
  {
    n: "01",
    title: "AGENCIES",
    body: "Generate qualified conversations for clients without expanding headcount.",
  },
  {
    n: "02",
    title: "REAL ESTATE",
    body: "Identify and qualify buyers and sellers already active in WhatsApp networks.",
  },
  {
    n: "03",
    title: "RECRUITING",
    body: "Find candidates and begin conversations before competitors do.",
  },
  {
    n: "04",
    title: "COACHING",
    body: "Turn inbound interest into booked discovery calls on autopilot.",
  },
  {
    n: "05",
    title: "B2B SERVICES",
    body: "Keep a continuous pipeline of qualified sales conversations warm.",
  },
  {
    n: "06",
    title: "LEAD GENERATION",
    body: "Scale outreach volume without scaling manual follow-up labor.",
  },
];

export function UseCases() {
  return (
    <section id="use-cases" className="border-b border-line">
      <div className="section-pad mx-auto max-w-[1440px] py-20 lg:py-28">
        <Reveal className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div>
            <SectionLabel>07 / USE CASES</SectionLabel>
            <h2 className="font-display headline-lg mt-5 max-w-[12ch]">
              BUILT FOR
              <br />
              TEAMS THAT
              <br />
              LIVE IN
              <br />
              WHATSAPP.
            </h2>
          </div>
          <p className="max-w-[32ch] text-[15px] leading-relaxed text-mute md:pb-2">
            Same infrastructure. Different targeting criteria. One conversion
            path: booked conversations with the right people.
          </p>
        </Reveal>

        <div className="mt-14 grid border-l border-t border-line sm:grid-cols-2 lg:grid-cols-3">
          {cases.map((c, i) => (
            <Reveal key={c.n} delay={i * 0.04}>
              <article className="group flex h-full min-h-[220px] flex-col justify-between border-b border-r border-line bg-paper p-6 transition-colors hover:bg-off">
                <div className="flex items-start justify-between gap-4">
                  <span className="font-mono text-xs text-signal">{c.n}</span>
                  <span className="h-px w-10 bg-line transition-all group-hover:w-16 group-hover:bg-signal" />
                </div>
                <div>
                  <h3 className="font-display text-2xl tracking-tight md:text-3xl">
                    {c.title}
                  </h3>
                  <p className="mt-4 max-w-[28ch] text-sm leading-relaxed text-mute">
                    {c.body}
                  </p>
                </div>
              </article>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
