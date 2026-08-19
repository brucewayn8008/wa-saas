import { ConversationConsole } from "@/components/relay-landing/conversations/ConversationConsole";
import { Reveal } from "@/components/relay-landing/ui/Reveal";
import { SectionLabel } from "@/components/relay-landing/ui/SectionLabel";

export function RealConversation() {
  return (
    <section className="relative border-b border-line bg-ink text-paper grain-dark">
      <div className="section-pad relative z-10 mx-auto max-w-[1440px] py-20 lg:py-28">
        <div className="grid gap-12 lg:grid-cols-[1fr_1.1fr] lg:gap-16">
          <Reveal>
            <SectionLabel dark>04 / CONVERSATION ENGINE</SectionLabel>
            <h2 className="font-display headline-lg mt-5 max-w-[12ch] text-paper">
              IT DOESN&apos;T SEND
              <br />
              MESSAGES.
              <br />
              IT HOLDS
              <br />
              CONVERSATIONS.
            </h2>
            <p className="mt-8 max-w-[36ch] text-[15px] leading-relaxed text-white/55">
              Personalized opens. Natural replies. Qualification. Objection
              handling. Follow-up. Intent recognition. Meeting booking — inside
              the same thread your buyers already use.
            </p>
          </Reveal>

          <Reveal delay={0.1}>
            <ConversationConsole />
          </Reveal>
        </div>
      </div>
    </section>
  );
}
