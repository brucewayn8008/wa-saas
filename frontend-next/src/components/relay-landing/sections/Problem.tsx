import { Reveal } from "@/components/relay-landing/ui/Reveal";
import { SectionLabel } from "@/components/relay-landing/ui/SectionLabel";

const manualFlow = [
  "LEADS",
  "MANUAL DISCOVERY",
  "MANUAL OUTREACH",
  "MANUAL FOLLOW-UP",
  "LOST OPPORTUNITIES",
];

export function Problem() {
  return (
    <section className="relative border-b border-line bg-off">
      <div className="section-pad mx-auto grid max-w-[1440px] gap-12 py-20 lg:grid-cols-[1.2fr_0.8fr] lg:gap-16 lg:py-28">
        <Reveal>
          <SectionLabel>01 / THE PROBLEM</SectionLabel>
          <h2 className="font-display headline-lg mt-5 max-w-[14ch]">
            YOUR LEADS ARE
            <br />
            ALREADY TALKING.
            <br />
            YOU&apos;RE JUST NOT
            <br />
            THERE.
          </h2>
          <p className="mt-8 max-w-[42ch] text-[15px] leading-relaxed text-mute">
            Prospects already exist inside WhatsApp groups, communities,
            referrals, and business networks. The bottleneck isn&apos;t demand —
            it&apos;s the manual work of finding them, starting conversations,
            qualifying, following up, and booking meetings.
          </p>
        </Reveal>

        <Reveal delay={0.1} className="flex flex-col justify-end">
          <div className="border border-line bg-paper">
            <div className="border-b border-line px-4 py-3">
              <p className="meta">FIG. 02 — MANUAL PIPELINE FAILURE</p>
            </div>
            <ol className="divide-y divide-line">
              {manualFlow.map((step, i) => (
                <li
                  key={step}
                  className="flex items-center justify-between gap-4 px-4 py-4"
                >
                  <div className="flex items-center gap-4">
                    <span className="font-mono text-[11px] text-mute">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <span
                      className={
                        i === manualFlow.length - 1
                          ? "text-sm font-medium text-signal"
                          : "text-sm font-medium text-ink"
                      }
                    >
                      {step}
                    </span>
                  </div>
                  {i < manualFlow.length - 1 && (
                    <span className="font-mono text-signal" aria-hidden>
                      ↓
                    </span>
                  )}
                </li>
              ))}
            </ol>
          </div>
          <p className="meta mt-4">
            AUTONOMOUS SYSTEM REPLACES THE MANUAL CHAIN
          </p>
        </Reveal>
      </div>
    </section>
  );
}
