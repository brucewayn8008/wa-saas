import { InfrastructureMap } from "@/components/relay-landing/diagrams/InfrastructureMap";
import { Reveal } from "@/components/relay-landing/ui/Reveal";
import { SectionLabel } from "@/components/relay-landing/ui/SectionLabel";

export function Infrastructure() {
  return (
    <section className="border-b border-line bg-off">
      <div className="section-pad mx-auto max-w-[1440px] py-20 lg:py-28">
        <Reveal className="max-w-3xl">
          <SectionLabel>06 / INFRASTRUCTURE</SectionLabel>
          <h2 className="font-display headline-lg mt-5">
            SALES AS
            <br />
            A SYSTEM —
            <br />
            NOT A QUEUE
            <br />
            OF CHATS.
          </h2>
          <p className="mt-8 max-w-[46ch] text-[15px] leading-relaxed text-mute">
            Every stage is explicit, observable, and connected. From WhatsApp
            groups to a booked meeting, Relay treats outreach like
            infrastructure — not a pile of unread threads.
          </p>
        </Reveal>

        <Reveal delay={0.1} className="mt-12">
          <InfrastructureMap />
        </Reveal>
      </div>
    </section>
  );
}
