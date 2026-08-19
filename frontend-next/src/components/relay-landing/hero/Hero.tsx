import Image from "next/image";
import Link from "next/link";
import { BookButton } from "@/components/relay-landing/ui/BookButton";
import { SectionLabel } from "@/components/relay-landing/ui/SectionLabel";
import { SalesConsole } from "@/components/relay-landing/conversations/SalesConsole";
import { SIGNUP_HREF } from "@/lib/relay-landing/utils";

export function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-line">
      <div className="pointer-events-none absolute inset-0 grid-bg opacity-70" />
      <div className="section-pad relative mx-auto grid max-w-[1440px] gap-10 pb-16 pt-10 lg:grid-cols-[1.05fr_0.95fr] lg:gap-8 lg:pb-24 lg:pt-16">
        <div className="relative z-10 flex flex-col">
          <SectionLabel>WHATSAPP / AUTONOMOUS SALES INFRASTRUCTURE</SectionLabel>

          <h1 className="font-display headline-xl mt-6 max-w-[12ch] text-ink">
            TURN WHATSAPP
            <br />
            INTO YOUR
            <br />
            AUTONOMOUS
            <br />
            SALES TEAM.
          </h1>

          <div className="mt-8 grid max-w-xl gap-6 border-t border-line pt-6 lg:mt-auto">
            <p className="text-[15px] leading-relaxed text-mute lg:max-w-[36ch]">
              Find prospects, start conversations, qualify leads, handle
              objections, and follow up automatically — with a sales agent that
              talks to customers like a real salesperson.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link
                href={SIGNUP_HREF}
                className="inline-flex items-center justify-center h-14 px-8 text-sm font-medium tracking-[0.04em] uppercase bg-signal text-white hover:bg-signal-deep transition-colors duration-200"
              >
                START FREE →
              </Link>
              <BookButton size="lg" variant="outline" className="w-full sm:w-auto" />
            </div>
          </div>

          <p className="meta mt-8 text-mute">
            NOT A CHATBOT · AN AUTONOMOUS SALES EMPLOYEE
          </p>
        </div>

        <div className="relative z-10">
          <div className="absolute -right-2 -top-6 hidden w-28 lg:block xl:-right-6 xl:w-36">
            <div className="relative aspect-[3/4] overflow-hidden border border-line">
              <Image
                src="/images/editorial-signal.webp"
                alt=""
                fill
                className="object-cover"
                sizes="144px"
                priority
              />
            </div>
            <p className="meta mt-2">FIG. 01 — SIGNAL MAP</p>
          </div>

          <SalesConsole className="relative z-10 mt-2 lg:mt-10" />

          <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
            <p className="meta">CORE LOOP · DISCOVER → BOOK</p>
            <p className="meta text-signal">OPERATING ON WHATSAPP</p>
          </div>
        </div>
      </div>
    </section>
  );
}
