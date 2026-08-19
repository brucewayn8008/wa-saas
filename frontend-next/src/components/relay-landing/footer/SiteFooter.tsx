import Link from "next/link";

const links = [
  { href: "#product", label: "PRODUCT" },
  { href: "#how-it-works", label: "HOW IT WORKS" },
  { href: "#use-cases", label: "USE CASES" },
  { href: "#book", label: "CONTACT" },
  { href: "#", label: "PRIVACY" },
  { href: "#", label: "TERMS" },
];

export function SiteFooter() {
  return (
    <footer className="border-t border-line bg-paper">
      <div className="section-pad mx-auto flex max-w-[1440px] flex-col gap-10 py-12 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="flex items-center gap-2 font-display text-sm tracking-tight">
            <span className="inline-block h-2 w-2 bg-signal" aria-hidden />
            RELAY
          </p>
          <p className="meta mt-4 max-w-[28ch]">
            AUTONOMOUS SALES INFRASTRUCTURE / 2026
          </p>
        </div>

        <nav aria-label="Footer">
          <ul className="flex flex-wrap gap-x-6 gap-y-3">
            {links.map((link) => (
              <li key={link.label}>
                <Link
                  href={link.href}
                  className="meta-ink text-[10px] tracking-[0.12em] text-mute transition-colors hover:text-ink"
                >
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </footer>
  );
}
