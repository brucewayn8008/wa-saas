import { Reveal } from "@/components/relay-landing/ui/Reveal";
import { SectionLabel } from "@/components/relay-landing/ui/SectionLabel";

const steps = [
  {
    n: "01",
    title: "DISCOVER",
    body: "The agent scans relevant WhatsApp communities and identifies potential prospects based on your targeting criteria.",
    meta: "GROUPS · COMMUNITIES · SIGNALS",
  },
  {
    n: "02",
    title: "UNDERSTAND",
    body: "Available context is analyzed to determine whether the person appears relevant before any outreach begins.",
    meta: "CONTEXT FILTER · FIT SCORE",
  },
  {
    n: "03",
    title: "ENGAGE",
    body: "A personalized conversation starts — grounded in context — instead of generic spam.",
    meta: "PERSONALIZED OPEN",
  },
  {
    n: "04",
    title: "QUALIFY",
    body: "Relevant questions evaluate intent, budget signals, timing, and fit against your criteria.",
    meta: "INTENT · FIT · TIMING",
  },
  {
    n: "05",
    title: "FOLLOW UP",
    body: "Follow-ups fire automatically based on conversation state and timing — without manual reminders.",
    meta: "CADENCE ENGINE",
  },
  {
    n: "06",
    title: "BOOK",
    body: "Qualified prospects are moved toward a meeting on your calendar. Priority threads escalate to a human.",
    meta: "CALENDAR · HANDOFF",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="border-b border-line bg-paper">
      <div className="section-pad mx-auto max-w-[1440px] py-20 lg:py-28">
        <Reveal>
          <SectionLabel>03 / HOW IT WORKS</SectionLabel>
          <h2 className="font-display headline-lg mt-5 max-w-[16ch]">
            FROM SIGNAL
            <br />
            TO MEETING.
            <br />
            WITHOUT YOU
            <br />
            IN THE THREAD.
          </h2>
        </Reveal>

        <div className="mt-14 border-t border-line">
          {steps.map((step, i) => (
            <Reveal key={step.n} delay={i * 0.04}>
              <article
                className={`grid gap-6 border-b border-line py-10 md:grid-cols-12 md:items-end md:gap-8 ${
                  i % 2 === 1 ? "bg-off/50" : ""
                }`}
              >
                <div className="md:col-span-2">
                  <p className="font-display text-5xl tracking-tight text-signal md:text-6xl">
                    {step.n}
                  </p>
                </div>
                <div
                  className={
                    i % 2 === 0
                      ? "md:col-span-5"
                      : "md:col-span-5 md:col-start-4"
                  }
                >
                  <h3 className="font-display text-3xl tracking-tight md:text-4xl">
                    {step.title}
                  </h3>
                  <p className="mt-4 max-w-[40ch] text-[15px] leading-relaxed text-mute">
                    {step.body}
                  </p>
                </div>
                <div
                  className={
                    i % 2 === 0
                      ? "md:col-span-5 md:flex md:justify-end"
                      : "md:col-span-3 md:col-start-10"
                  }
                >
                  <div className="w-full border border-line bg-paper p-4 md:max-w-xs">
                    <div className="mb-6 h-16 border border-dashed border-line grid-bg" />
                    <p className="meta">{step.meta}</p>
                    <div className="mt-3 flex items-center gap-2">
                      <span className="h-1.5 w-1.5 bg-signal animate-pulse-node" />
                      <span className="meta text-ink">NODE ONLINE</span>
                    </div>
                  </div>
                </div>
              </article>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
