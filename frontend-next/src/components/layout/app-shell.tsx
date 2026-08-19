"use client";

import { MobileNav, Sidebar } from "@/components/layout/sidebar";
import { AUTH_BYPASS } from "@/lib/config";

type AppShellProps = {
  children: React.ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex min-h-screen bg-[var(--bg)]">
      <Sidebar />
      <div className="flex min-h-screen min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-[var(--border)] bg-[var(--surface)] px-4 py-3 lg:px-6">
          <div className="lg:hidden">
            <p className="text-[var(--text-sm)] font-[var(--font-bold)] text-[var(--fg)]">PrePop</p>
          </div>
          <div className="ml-auto flex items-center gap-3">
            {AUTH_BYPASS ? (
              <span className="rounded-[var(--radius-full)] bg-[var(--warning-subtle)] px-2.5 py-1 text-[var(--text-xs)] font-[var(--font-medium)] text-[var(--warning)]">
                Dev auth bypass
              </span>
            ) : null}
          </div>
        </header>
        <MobileNav />
        <main className="mx-auto w-full max-w-[1280px] flex-1 px-[var(--space-6)] py-[var(--space-6)]">
          {children}
        </main>
      </div>
    </div>
  );
}
