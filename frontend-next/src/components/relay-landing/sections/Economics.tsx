import { Reveal } from "@/components/relay-landing/ui/Reveal";
import { SectionLabel } from "@/components/relay-landing/ui/SectionLabel";

const manual = [
  "LIMITED HOURS",
  "LIMITED OUTREACH",
  "MANUAL FOLLOW-UP",
  "HUMAN BOTTLENECK",
];

const auto = [
  "24/7 CONVERSATIONS",
  "CONTINUOUS FOLLOW-UP",
  "SCALABLE OUTREACH",
  "CONSISTENT PROCESS",
];

export function Economics() {
  return (
    <section className="border-b border-line bg-ink text-paper">
      <div className="section-pad mx-auto max-w-[1440px] py-20 lg:py-28">
        <Reveal>
          <SectionLabel dark>08 / ECONOMICS</SectionLabel>
          <h2 className="font-display headline-lg mt-5 max-w-[14ch]">
            MANUAL SALES
            <br />
            HAS A CEILING.
            <br />
            AUTONOMY
            <br />
            REMOVES IT.
          </h2>
        </Reveal>

        <div className="mt-14 grid gap-0 border border-line-dark lg:grid-cols-2">
          <Reveal className="border-b border-line-dark p-8 lg:border-b-0 lg:border-r">
            <p className="meta text-white/40">MANUAL SALES</p>
            <p className="font-display mt-4 text-4xl tracking-tight text-white/35 md:text-5xl">
              FINITE
            </p>
            <ul className="mt-10 space-y-0 border-t border-line-dark">
              {manual.map((item) => (
                <li
                  key={item}
                  className="border-b border-line-dark py-4 font-display text-xl tracking-tight text-white/50 md:text-2xl"
                >
                  {item}
                </li>
              ))}
            </ul>
          </Reveal>

          <Reveal delay={0.08} className="bg-ink-soft p-8">
            <p className="meta text-signal">AUTONOMOUS SALES</p>
            <p className="font-display mt-4 text-4xl tracking-tight text-paper md:text-5xl">
              CONTINUOUS
            </p>
            <ul className="mt-10 space-y-0 border-t border-line-dark">
              {auto.map((item) => (
                <li
                  key={item}
                  className="border-b border-line-dark py-4 font-display text-xl tracking-tight text-paper md:text-2xl"
                >
                  {item}
                </li>
              ))}
            </ul>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
