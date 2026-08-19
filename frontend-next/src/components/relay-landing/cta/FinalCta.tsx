import Link from "next/link";
import { BookButton } from "@/components/relay-landing/ui/BookButton";
import { Reveal } from "@/components/relay-landing/ui/Reveal";
import { SectionLabel } from "@/components/relay-landing/ui/SectionLabel";
import { SIGNUP_HREF } from "@/lib/relay-landing/utils";

export function FinalCta() {
  return (
    <section
      id="book"
      className="relative overflow-hidden border-b border-line bg-off grain"
    >
      <div className="pointer-events-none absolute inset-0 grid-bg opacity-60" />
      <div className="section-pad relative z-10 mx-auto max-w-[1440px] py-24 lg:py-36">
        <Reveal>
          <SectionLabel>10 / NEXT STEP</SectionLabel>
          <h2 className="font-display headline-xl mt-6 max-w-[12ch]">
            YOUR NEXT
            <br />
            CUSTOMER
            <br />
            COULD ALREADY
            <br />
            BE IN THE CHAT.
          </h2>
        </Reveal>

        <Reveal
          delay={0.1}
          className="mt-12 flex flex-col gap-8 border-t border-line pt-8 md:flex-row md:items-end md:justify-between"
        >
          <p className="max-w-[42ch] text-[16px] leading-relaxed text-mute">
            Start free and connect your WhatsApp number in minutes, or book a
            call to see how it fits your acquisition process.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              href={SIGNUP_HREF}
              className="inline-flex items-center justify-center h-14 px-8 text-sm font-medium tracking-[0.04em] uppercase bg-ink text-paper hover:bg-signal transition-colors duration-200"
            >
              START FREE →
            </Link>
            <BookButton size="lg" variant="outline" />
          </div>
        </Reveal>

        <p className="meta mt-16 text-mute">
          SELF-SERVE SIGNUP · BOOKING · CALENDAR HANDOFF
        </p>
      </div>
    </section>
  );
}
