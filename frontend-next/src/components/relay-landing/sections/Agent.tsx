import { SalesLoop } from "@/components/relay-landing/diagrams/SalesLoop";
import { BookButton } from "@/components/relay-landing/ui/BookButton";
import { Reveal } from "@/components/relay-landing/ui/Reveal";
import { SectionLabel } from "@/components/relay-landing/ui/SectionLabel";

export function Agent() {
  return (
    <section id="product" className="relative border-b border-line">
      <div className="section-pad mx-auto grid max-w-[1440px] gap-12 py-20 lg:grid-cols-2 lg:gap-16 lg:py-28">
        <Reveal>
          <SectionLabel>02 / THE AGENT</SectionLabel>
          <h2 className="font-display headline-lg mt-5 max-w-[10ch]">
            ONE AGENT.
            <br />
            THE WHOLE
            <br />
            SALES LOOP.
          </h2>
          <p className="mt-8 max-w-[40ch] text-[15px] leading-relaxed text-mute">
            Relay runs the full cycle: discover prospects in WhatsApp
            communities, open personalized conversations, qualify intent, follow
            up on schedule, book meetings, and hand off when a human should
            take over.
          </p>
          <ul className="mt-8 space-y-3 border-t border-line pt-6">
            {[
              "Personalized cold opens — not blast templates",
              "Objection handling inside the thread",
              "Buying-intent detection before you join",
              "Escalation when the conversation matters",
            ].map((item) => (
              <li key={item} className="flex gap-3 text-sm">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 bg-signal" />
                {item}
              </li>
            ))}
          </ul>
          <div className="mt-10">
            <BookButton />
          </div>
        </Reveal>

        <Reveal delay={0.12}>
          <SalesLoop />
        </Reveal>
      </div>
    </section>
  );
}
