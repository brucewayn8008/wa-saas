import { Reveal } from "@/components/relay-landing/ui/Reveal";
import { SectionLabel } from "@/components/relay-landing/ui/SectionLabel";

const metrics = [
  { value: "+XXX%", label: "QUALIFIED LEADS", note: "Replace with measured lift" },
  { value: "XX%", label: "RESPONSE RATE", note: "Replace with measured rate" },
  {
    value: "XXX",
    label: "CONVERSATIONS / MONTH",
    note: "Replace with volume",
  },
  { value: "XX", label: "MEETINGS BOOKED", note: "Replace with booked count" },
];

export function Results() {
  return (
    <section id="results" className="border-b border-line">
      <div className="section-pad mx-auto max-w-[1440px] py-20 lg:py-28">
        <Reveal className="grid gap-8 lg:grid-cols-12">
          <div className="lg:col-span-7">
            <SectionLabel>09 / RESULTS</SectionLabel>
            <h2 className="font-display headline-lg mt-5 max-w-[14ch]">
              PROOF BELONGS
              <br />
              IN THE
              <br />
              NUMBERS.
            </h2>
          </div>
          <p className="max-w-[36ch] self-end text-[15px] leading-relaxed text-mute lg:col-span-5">
            Metrics below are structured placeholders. Insert verified customer
            data before launch — no invented statistics.
          </p>
        </Reveal>

        <div className="mt-14 grid border-l border-t border-line sm:grid-cols-2">
          {metrics.map((m, i) => (
            <Reveal key={m.label} delay={i * 0.05}>
              <div className="flex min-h-[200px] flex-col justify-between border-b border-r border-line p-6 md:p-8">
                <p className="meta">{m.note}</p>
                <div>
                  <p className="font-display text-6xl tracking-tight text-signal md:text-7xl">
                    {m.value}
                  </p>
                  <p className="meta-ink mt-4">{m.label}</p>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
