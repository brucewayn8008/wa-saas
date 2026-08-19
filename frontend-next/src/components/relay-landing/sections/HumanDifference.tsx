import { Reveal } from "@/components/relay-landing/ui/Reveal";
import { SectionLabel } from "@/components/relay-landing/ui/SectionLabel";

const traits = [
  "Understands conversation context",
  "Maintains continuity across replies",
  "Handles objections in-thread",
  "Adapts questions to the prospect",
  "Detects buying intent",
  "Knows when to follow up",
  "Adjusts behavior per conversation",
  "Escalates when a human should join",
];

export function HumanDifference() {
  return (
    <section className="border-b border-line">
      <div className="section-pad mx-auto grid max-w-[1440px] gap-12 py-20 lg:grid-cols-12 lg:py-28">
        <Reveal className="lg:col-span-7">
          <SectionLabel>05 / BEHAVIOR</SectionLabel>
          <h2 className="font-display headline-lg mt-5 max-w-[10ch]">
            NOT AN
            <br />
            AUTO-REPLY
            <br />
            BOT.
          </h2>
          <p className="mt-8 max-w-[34ch] text-[15px] leading-relaxed text-mute">
            Relay behaves like a disciplined salesperson: present, adaptive, and
            precise — then steps aside when the deal needs you.
          </p>
        </Reveal>

        <Reveal delay={0.08} className="lg:col-span-5">
          <ul className="border-t border-line">
            {traits.map((trait, i) => (
              <li
                key={trait}
                className="flex items-baseline justify-between gap-6 border-b border-line py-4"
              >
                <span className="text-sm md:text-base">{trait}</span>
                <span className="meta shrink-0 text-signal">
                  {String(i + 1).padStart(2, "0")}
                </span>
              </li>
            ))}
          </ul>
        </Reveal>
      </div>
    </section>
  );
}
