"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  MessageSquare,
  Users,
  Ear,
  FileText,
  ImageIcon,
  Settings,
  CreditCard,
  Rocket,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { AUTH_BYPASS } from "@/lib/config";
import { ClerkOrgControls } from "@/components/layout/clerk-org-controls";

const navItems = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Conversations", href: "/conversations", icon: MessageSquare },
  { name: "Leads", href: "/leads", icon: Users },
  { name: "Listening", href: "/listening", icon: Ear },
  { name: "Templates", href: "/templates", icon: FileText },
  { name: "Media", href: "/media", icon: ImageIcon },
  { name: "Settings", href: "/settings", icon: Settings },
  { name: "Billing", href: "/billing", icon: CreditCard },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      aria-label="Main navigation"
      className="hidden w-64 shrink-0 flex-col border-r border-[var(--border)] bg-[var(--surface)] lg:flex"
    >
      <div className="flex items-center gap-3 border-b border-[var(--border)] px-5 py-5">
        <div className="rounded-[var(--radius-md)] bg-[var(--brand)] p-2 text-[var(--brand-fg)]">
          <Rocket className="h-4 w-4" aria-hidden="true" />
        </div>
        <div>
          <p className="text-[var(--text-base)] font-[var(--font-bold)] text-[var(--fg)] leading-none tracking-[-0.03em]">
            PrePop
          </p>
          <p className="mt-1 text-[10px] font-[var(--font-semibold)] uppercase tracking-[0.1em] text-[var(--brand)]">
            Sales Agent
          </p>
        </div>
      </div>

      <div className="border-b border-[var(--border)] px-4 py-3">
        {AUTH_BYPASS ? (
          <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2">
            <p className="text-[10px] font-[var(--font-semibold)] uppercase tracking-wider text-[var(--fg-subtle)]">
              Organization
            </p>
            <p className="text-[var(--text-sm)] font-[var(--font-semibold)] text-[var(--fg)]">
              Northline Studio
            </p>
          </div>
        ) : (
          <div className="min-h-10">
            <ClerkOrgControls />
          </div>
        )}
      </div>

      <nav className="flex-1 space-y-1 p-3" aria-label="Sidebar">
        {navItems.map((item) => {
          const active =
            item.href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname === item.href || pathname.startsWith(`${item.href}/`);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex items-center gap-3 rounded-[var(--radius-md)] px-3 py-2.5 text-[var(--text-sm)] font-[var(--font-semibold)] transition-ui",
                active
                  ? "bg-[var(--brand)] text-[var(--brand-fg)]"
                  : "text-[var(--fg-muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span className="lg:inline">{item.name}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

export function MobileNav() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Mobile navigation"
      className="flex gap-1 overflow-x-auto border-b border-[var(--border)] bg-[var(--surface)] px-2 py-2 lg:hidden"
    >
      {navItems.map((item) => {
        const active =
          item.href === "/dashboard"
            ? pathname === "/dashboard"
            : pathname === item.href || pathname.startsWith(`${item.href}/`);
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-label={item.name}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex shrink-0 items-center gap-2 rounded-[var(--radius-md)] px-3 py-2 text-[var(--text-xs)] font-[var(--font-semibold)]",
              active
                ? "bg-[var(--brand)] text-[var(--brand-fg)]"
                : "text-[var(--fg-muted)] hover:bg-[var(--surface-2)]"
            )}
          >
            <Icon className="h-4 w-4" aria-hidden="true" />
            {item.name}
          </Link>
        );
      })}
    </nav>
  );
}
