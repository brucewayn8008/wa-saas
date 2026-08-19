"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";
import { BookButton } from "@/components/relay-landing/ui/BookButton";
import { cn, LOGIN_HREF, SIGNUP_HREF } from "@/lib/relay-landing/utils";

const links = [
  { href: "#product", label: "PRODUCT" },
  { href: "#how-it-works", label: "HOW IT WORKS" },
  { href: "#use-cases", label: "USE CASES" },
  { href: "#results", label: "RESULTS" },
];

export function SiteNav() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <header
      className={cn(
        "sticky top-0 z-50 border-b border-line bg-paper/92 backdrop-blur-sm transition-shadow",
        scrolled && "shadow-[0_1px_0_0_var(--line)]",
      )}
    >
      <nav
        className="section-pad mx-auto flex h-14 max-w-[1440px] items-center justify-between gap-4"
        aria-label="Primary"
      >
        <Link
          href="/"
          className="relative z-10 flex items-center gap-2 font-display text-[15px] tracking-[-0.03em]"
        >
          <span className="inline-block h-2 w-2 bg-signal" aria-hidden />
          RELAY
        </Link>

        <ul className="absolute left-1/2 hidden -translate-x-1/2 items-center gap-7 md:flex">
          {links.map((link) => (
            <li key={link.href}>
              <Link
                href={link.href}
                className="meta-ink text-[10px] tracking-[0.12em] text-mute transition-colors hover:text-ink"
              >
                {link.label}
              </Link>
            </li>
          ))}
        </ul>

        <div className="relative z-10 flex items-center gap-3">
          <Link
            href={LOGIN_HREF}
            className="hidden sm:inline-flex items-center h-9 px-4 text-[11px] font-medium tracking-[0.04em] uppercase text-mute transition-colors hover:text-ink"
          >
            LOG IN
          </Link>
          <BookButton size="sm" className="hidden sm:inline-flex" label="START FREE →" href={SIGNUP_HREF} />
          <BookButton size="sm" className="sm:hidden px-3" label="START →" href={SIGNUP_HREF} />
          <button
            type="button"
            className="inline-flex h-9 w-9 items-center justify-center border border-line md:hidden"
            aria-expanded={open}
            aria-controls="mobile-menu"
            aria-label={open ? "Close menu" : "Open menu"}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? <X size={16} /> : <Menu size={16} />}
          </button>
        </div>
      </nav>

      <div
        id="mobile-menu"
        className={cn(
          "border-t border-line bg-paper md:hidden",
          open ? "block" : "hidden",
        )}
      >
        <ul className="section-pad flex flex-col py-4">
          {links.map((link) => (
            <li key={link.href} className="border-b border-line">
              <Link
                href={link.href}
                className="flex h-12 items-center meta-ink tracking-[0.12em]"
                onClick={() => setOpen(false)}
              >
                {link.label}
              </Link>
            </li>
          ))}
          <li className="border-b border-line">
            <Link
              href={LOGIN_HREF}
              className="flex h-12 items-center meta-ink tracking-[0.12em]"
              onClick={() => setOpen(false)}
            >
              LOG IN
            </Link>
          </li>
          <li className="pt-4">
            <BookButton size="md" label="START FREE →" href={SIGNUP_HREF} className="w-full" />
          </li>
        </ul>
      </div>
    </header>
  );
}
