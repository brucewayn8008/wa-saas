import Link from "next/link";

const capabilities = [
  {
    n: "01",
    title: "Answers inbound WhatsApp 24/7",
    body: "Prospects get a natural reply with typing pauses and short bubbles — not a stiff bot wall of text.",
  },
  {
    n: "02",
    title: "Qualifies and remembers",
    body: "Budget, timeline, and service interest scored into HOT / WARM / COLD and kept in conversation memory.",
  },
  {
    n: "03",
    title: "Shares your brand media",
    body: "Portfolio shots and product videos from your library — never fake persona photos.",
  },
  {
    n: "04",
    title: "Books the meeting",
    body: "When the lead is ready, PrePop proposes your booking link and logs it in the CRM.",
  },
];

const steps = [
  {
    n: "01",
    title: "Connect WhatsApp",
    body: "Link your business number with Cloud API or a quick QR link. Your number stays yours.",
  },
  {
    n: "02",
    title: "Describe what you sell",
    body: "Brand voice, services, offer, booking link, and a mandatory AI disclosure line.",
  },
  {
    n: "03",
    title: "Go live",
    body: "Inbound chats get answered in seconds — qualified, remembered, and steered to a meeting.",
  },
];

const compliance = [
  "No cold DMs to strangers",
  "No scraping group members into blast lists",
  "Agent always discloses it is AI for your brand",
  "Group listening auto-replies to matched leads",
  "Opt-in templates only outside the 24h window",
  "Your brand media only — no fake personas",
];

const audiences = [
  "Freelancers & agencies getting leads on WhatsApp",
  "Local clinics, salons, tutors, and real estate teams",
  "Anyone running click-to-WhatsApp ads who needs the other end answered well",
];

export function LandingPage() {
  return (
    <div className="lp-root min-h-screen overflow-x-hidden">

      {/* ── Nav ── */}
      <header className="sticky top-0 z-50 border-b border-[var(--lp-line)] bg-[var(--lp-paper)]/92 backdrop-blur-sm">
        <nav className="lp-pad mx-auto flex h-14 max-w-[1440px] items-center justify-between gap-4">
          <Link href="/" className="flex items-center gap-2 lp-display text-[15px] tracking-[-0.03em]">
            <span className="inline-block h-2 w-2 bg-[var(--lp-signal)]" aria-hidden />
            PREPOP
          </Link>

          <ul className="absolute left-1/2 hidden -translate-x-1/2 items-center gap-7 md:flex">
            {[
              { href: "#product", label: "PRODUCT" },
              { href: "#how-it-works", label: "HOW IT WORKS" },
              { href: "#who", label: "WHO IT'S FOR" },
            ].map((l) => (
              <li key={l.href}>
                <Link href={l.href} className="lp-meta text-[10px] tracking-[0.12em] text-[var(--lp-mute)] transition-colors hover:text-[var(--lp-ink)]">
                  {l.label}
                </Link>
              </li>
            ))}
          </ul>

          <div className="flex items-center gap-3">
            <Link href="/login" className="hidden sm:inline-flex items-center h-9 px-4 lp-meta text-[11px] text-[var(--lp-mute)] transition-colors hover:text-[var(--lp-ink)]">
              LOG IN
            </Link>
            <Link
              href="/signup"
              className="inline-flex items-center justify-center h-9 px-5 lp-meta text-[11px] bg-[var(--lp-signal)] text-white hover:bg-[var(--lp-signal-deep)] transition-colors"
            >
              START FREE →
            </Link>
          </div>
        </nav>
      </header>

      {/* ── Hero ── */}
      <section className="relative overflow-hidden border-b border-[var(--lp-line)]">
        <div className="pointer-events-none absolute inset-0 lp-grid-bg opacity-70" />
        <div className="lp-pad relative mx-auto grid max-w-[1440px] gap-10 pb-16 pt-10 lg:grid-cols-[1.05fr_0.95fr] lg:gap-8 lg:pb-24 lg:pt-16">

          {/* Left: copy */}
          <div className="relative z-10 flex flex-col">
            <p className="lp-meta text-[10px] tracking-[0.12em]">
              WHATSAPP / AUTONOMOUS SALES INFRASTRUCTURE
            </p>

            <h1 className="lp-display lp-headline-xl mt-6 max-w-[12ch] text-[var(--lp-ink)]">
              TURN WHATSAPP
              <br />INTO YOUR
              <br />AUTONOMOUS
              <br />SALES TEAM.
            </h1>

            <div className="mt-8 grid max-w-xl gap-6 border-t border-[var(--lp-line)] pt-6 lg:mt-auto">
              <p className="text-[15px] leading-relaxed text-[var(--lp-mute)] lg:max-w-[36ch]">
                Find prospects, start conversations, qualify leads, handle objections, and follow up
                automatically — with a sales agent that talks to customers like a real salesperson.
              </p>
              <div className="flex flex-wrap gap-3">
                <Link
                  href="/signup"
                  className="inline-flex items-center justify-center h-14 px-8 text-sm font-medium tracking-[0.04em] uppercase bg-[var(--lp-signal)] text-white hover:bg-[var(--lp-signal-deep)] transition-colors duration-200"
                >
                  START FREE →
                </Link>
                <Link
                  href="/dashboard"
                  className="inline-flex items-center justify-center h-14 px-8 text-sm font-medium tracking-[0.04em] uppercase border border-[var(--lp-ink)] bg-transparent text-[var(--lp-ink)] hover:bg-[var(--lp-ink)] hover:text-[var(--lp-paper)] transition-colors duration-200"
                >
                  VIEW DEMO
                </Link>
              </div>
            </div>

            <p className="lp-meta mt-8 text-[var(--lp-mute)]">
              NOT A CHATBOT · AN AUTONOMOUS SALES EMPLOYEE
            </p>
          </div>

          {/* Right: chat preview */}
          <div className="relative z-10">
            <div className="relative overflow-hidden border border-[var(--lp-line-dark)] bg-[#0f1a14] mt-2 lg:mt-10">
              {/* Console header */}
              <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
                <div>
                  <p className="lp-meta-signal text-[10px] tracking-[0.12em]">LIVE ON WHATSAPP</p>
                  <p className="mt-1 text-sm font-medium text-white/90">Northline Studio</p>
                </div>
                <span className="flex items-center gap-2 border border-white/10 px-2.5 py-1">
                  <span className="lp-pulse-dot lp-blink h-1.5 w-1.5 rounded-full bg-[var(--lp-signal)]" />
                  <span className="lp-meta text-[10px] text-white/70">AGENT LIVE</span>
                </span>
              </div>

              {/* Chat bubbles */}
              <div className="space-y-3 px-4 py-5">
                <div className="lp-chat lp-chat-1 max-w-[85%] border border-white/10 px-3.5 py-2.5 text-sm leading-relaxed text-white/80">
                  Hi, I need a website for my restaurant in Mumbai. Timeline is about 4 weeks.
                </div>
                <div className="lp-chat lp-chat-2 ml-auto max-w-[88%] bg-[var(--lp-signal)] px-3.5 py-2.5 text-sm leading-relaxed text-white">
                  <span className="lp-meta mb-1.5 inline-block bg-white/20 px-2 py-0.5 text-[9px]">AI</span>
                  <p>Hi — I&apos;m PrePop AI for Northline Studio. Happy to help. Rough budget range, and do you need online ordering too?</p>
                </div>
                <div className="lp-chat lp-chat-3 max-w-[80%] border border-white/10 px-3.5 py-2.5 text-sm leading-relaxed text-white/80">
                  Around ₹80k. Portfolio examples would help.
                </div>
                <div className="lp-chat lp-chat-4 ml-auto max-w-[88%] bg-[var(--lp-signal)] px-3.5 py-2.5 text-sm leading-relaxed text-white">
                  <span className="lp-meta mb-1.5 inline-block bg-white/20 px-2 py-0.5 text-[9px]">AI</span>
                  <p>Sending two recent restaurant builds. Want a 20-min discovery call this week?</p>
                </div>
              </div>
            </div>

            <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
              <p className="lp-meta">CORE LOOP · DISCOVER → QUALIFY → BOOK</p>
              <p className="lp-meta-signal">OPERATING ON WHATSAPP</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Problem ── */}
      <section className="border-b border-[var(--lp-line)] bg-white">
        <div className="lp-pad mx-auto max-w-[1440px] py-20 sm:py-28">
          <p className="lp-meta text-[10px] tracking-[0.12em]">THE PROBLEM</p>
          <h2 className="lp-display lp-headline-lg mt-6 max-w-[16ch] text-[var(--lp-ink)]">
            Leads message you on WhatsApp. Then they wait. Then they leave.
          </h2>
          <p className="mt-8 max-w-2xl text-[15px] leading-relaxed text-[var(--lp-mute)]">
            Freelancers and small businesses lose deals because they can&apos;t reply at 11pm,
            mid-meeting, or across time zones. Hiring a sales rep is expensive. Generic chatbots
            feel robotic and don&apos;t convert.
          </p>
        </div>
      </section>

      {/* ── Capabilities ── */}
      <section id="product" className="border-b border-[var(--lp-line)] bg-[var(--lp-off)] scroll-mt-14">
        <div className="lp-pad mx-auto max-w-[1440px] py-20 sm:py-28">
          <p className="lp-meta text-[10px] tracking-[0.12em]">WHAT PREPOP DOES</p>
          <h2 className="lp-display lp-headline-md mt-6 max-w-[20ch] text-[var(--lp-ink)]">
            A disclosed AI sales agent on your WhatsApp number.
          </h2>
          <ul className="mt-16 grid gap-0 border-t border-[var(--lp-line)] sm:grid-cols-2">
            {capabilities.map((item) => (
              <li key={item.n} className="border-b border-r border-[var(--lp-line)] p-8 last:border-r-0 sm:[&:nth-child(2n)]:border-r-0">
                <span className="lp-meta text-[10px] text-[var(--lp-signal)]">{item.n}</span>
                <h3 className="mt-3 text-[15px] font-semibold tracking-[-0.02em] text-[var(--lp-ink)]">{item.title}</h3>
                <p className="mt-3 text-[14px] leading-relaxed text-[var(--lp-mute)]">{item.body}</p>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* ── How it works ── */}
      <section id="how-it-works" className="border-b border-[var(--lp-line)] bg-white scroll-mt-14">
        <div className="lp-pad mx-auto max-w-[1440px] py-20 sm:py-28">
          <p className="lp-meta text-[10px] tracking-[0.12em]">HOW IT WORKS</p>
          <h2 className="lp-display lp-headline-md mt-6 max-w-[16ch] text-[var(--lp-ink)]">
            Live in under fifteen minutes.
          </h2>
          <ol className="mt-16 grid border-t border-[var(--lp-line)] lg:grid-cols-3">
            {steps.map((step) => (
              <li key={step.n} className="border-b border-r border-[var(--lp-line)] p-8 lg:border-b-0 last:border-r-0">
                <span className="lp-display text-5xl font-semibold text-[var(--lp-signal)] opacity-30">{step.n}</span>
                <h3 className="mt-4 text-[15px] font-semibold tracking-[-0.02em] text-[var(--lp-ink)]">{step.title}</h3>
                <p className="mt-3 text-[14px] leading-relaxed text-[var(--lp-mute)]">{step.body}</p>
              </li>
            ))}
          </ol>
          <div className="mt-10">
            <Link
              href="/onboarding"
              className="lp-meta inline-flex items-center gap-2 text-[11px] text-[var(--lp-signal)] hover:text-[var(--lp-signal-deep)] transition-colors"
            >
              BEGIN ONBOARDING →
            </Link>
          </div>
        </div>
      </section>

      {/* ── Compliance — dark section ── */}
      <section className="relative overflow-hidden border-b border-[var(--lp-line-dark)] bg-[var(--lp-ink)]">
        <div className="pointer-events-none absolute inset-0 lp-grid-bg-dark opacity-100" />
        <div className="lp-pad relative mx-auto max-w-[1440px] py-20 sm:py-28">
          <p className="lp-meta-signal text-[10px] tracking-[0.12em]">BUILT TO STAY COMPLIANT</p>
          <h2 className="lp-display lp-headline-md mt-6 max-w-[18ch] text-white">
            Sales automation — never spam tooling.
          </h2>
          <ul className="mt-14 grid gap-0 border-t border-white/10 sm:grid-cols-2">
            {compliance.map((line) => (
              <li key={line} className="flex items-start gap-4 border-b border-white/10 py-5 pr-8">
                <span className="mt-1 h-1.5 w-1.5 shrink-0 bg-[var(--lp-signal)]" aria-hidden />
                <span className="text-[14px] leading-relaxed text-white/70">{line}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* ── Who it's for ── */}
      <section id="who" className="border-b border-[var(--lp-line)] bg-[var(--lp-off)] scroll-mt-14">
        <div className="lp-pad mx-auto max-w-[1440px] py-20 sm:py-28">
          <p className="lp-meta text-[10px] tracking-[0.12em]">WHO IT&apos;S FOR</p>
          <h2 className="lp-display lp-headline-md mt-6 max-w-[20ch] text-[var(--lp-ink)]">
            If WhatsApp is your sales inbox, PrePop is your closer.
          </h2>
          <ul className="mt-14 border-t border-[var(--lp-line)]">
            {audiences.map((line) => (
              <li key={line} className="flex items-center justify-between border-b border-[var(--lp-line)] py-6">
                <span className="text-[15px] leading-relaxed text-[var(--lp-mute)]">{line}</span>
                <span className="lp-meta ml-8 shrink-0 text-[10px] text-[var(--lp-signal)]">→</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* ── Final CTA — dark ── */}
      <section className="relative overflow-hidden border-b border-[var(--lp-line-dark)] bg-[var(--lp-ink)]">
        <div className="pointer-events-none absolute inset-0 lp-grid-bg-dark opacity-100" />
        <div className="lp-pad relative mx-auto flex max-w-[1440px] flex-col gap-10 py-24 lg:flex-row lg:items-end lg:justify-between lg:py-32">
          <div>
            <h2 className="lp-display lp-headline-lg max-w-[14ch] text-white">
              STOP LOSING WHATSAPP LEADS OVERNIGHT.
            </h2>
            <p className="mt-6 max-w-md text-[15px] leading-relaxed text-white/50">
              Create your workspace, connect WhatsApp, and put a disclosed sales agent on duty.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/signup"
              className="inline-flex items-center justify-center h-14 px-8 text-sm font-medium tracking-[0.04em] uppercase bg-[var(--lp-signal)] text-white hover:bg-[var(--lp-signal-deep)] transition-colors duration-200"
            >
              CREATE YOUR WORKSPACE →
            </Link>
            <Link
              href="/dashboard"
              className="inline-flex items-center justify-center h-14 px-8 text-sm font-medium tracking-[0.04em] uppercase border border-white/20 text-white/70 hover:border-white hover:text-white transition-colors duration-200"
            >
              VIEW DASHBOARD
            </Link>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-[var(--lp-line)] bg-[var(--lp-paper)]">
        <div className="lp-pad mx-auto flex max-w-[1440px] flex-col gap-4 py-8 sm:flex-row sm:items-center sm:justify-between">
          <Link href="/" className="flex items-center gap-2 lp-display text-[15px] tracking-[-0.03em] text-[var(--lp-ink)]">
            <span className="inline-block h-2 w-2 bg-[var(--lp-signal)]" aria-hidden />
            PREPOP
          </Link>
          <p className="lp-meta text-[10px] text-[var(--lp-mute)]">
            DISCLOSED AI SALES AGENT FOR WHATSAPP · COMPLIANT BY DESIGN
          </p>
        </div>
      </footer>

    </div>
  );
}
