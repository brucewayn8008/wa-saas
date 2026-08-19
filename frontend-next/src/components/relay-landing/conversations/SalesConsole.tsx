"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/relay-landing/utils";

type Msg = {
  id: string;
  role: "prospect" | "agent";
  text: string;
  delay: number;
};

const messages: Msg[] = [
  {
    id: "1",
    role: "prospect",
    text: "Hey, I'm interested. How does this work?",
    delay: 400,
  },
  {
    id: "2",
    role: "agent",
    text: "Absolutely. Before I send details — are you handling outreach manually, or do you already have a sales process in place?",
    delay: 1600,
  },
  {
    id: "3",
    role: "prospect",
    text: "Mostly manual. We lose track after the first reply.",
    delay: 3200,
  },
  {
    id: "4",
    role: "agent",
    text: "That's the bottleneck we remove. I can qualify inbound interest and book a call with your team — does Thursday 14:00 work?",
    delay: 4800,
  },
];

const signals = [
  { label: "INTENT DETECTED", activeAt: 500 },
  { label: "QUALIFICATION ACTIVE", activeAt: 1700 },
  { label: "HIGH PURCHASE SIGNAL", activeAt: 3400 },
  { label: "MEETING READY", activeAt: 5000 },
];

export function SalesConsole({ className }: { className?: string }) {
  const [visible, setVisible] = useState<string[]>([]);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mq.matches) {
      const t = window.setTimeout(() => {
        setVisible(messages.map((m) => m.id));
        setTick(9999);
      }, 0);
      return () => clearTimeout(t);
    }

    let cancelled = false;
    let msgTimers: number[] = [];
    let interval = 0;
    let cycleTimer = 0;

    const run = () => {
      if (cancelled) return;
      setVisible([]);
      setTick(0);
      msgTimers.forEach(clearTimeout);
      clearInterval(interval);

      msgTimers = messages.map((m) =>
        window.setTimeout(() => {
          if (!cancelled) {
            setVisible((v) => (v.includes(m.id) ? v : [...v, m.id]));
          }
        }, m.delay),
      );

      const started = performance.now();
      interval = window.setInterval(() => {
        if (!cancelled) setTick(performance.now() - started);
      }, 100);

      cycleTimer = window.setTimeout(run, 10000);
    };

    run();
    return () => {
      cancelled = true;
      msgTimers.forEach(clearTimeout);
      clearInterval(interval);
      clearTimeout(cycleTimer);
    };
  }, []);

  return (
    <div
      className={cn(
        "relative border border-line bg-paper",
        className,
      )}
    >
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <div className="flex items-center gap-3">
          <span className="meta">SYS / SALES OS</span>
          <span className="meta text-signal animate-blink">● LIVE</span>
        </div>
        <span className="meta">WA · SESSION 04</span>
      </div>

      <div className="grid lg:grid-cols-[1fr_148px]">
        <div className="min-h-[360px] space-y-3 border-b border-line p-4 lg:border-b-0 lg:border-r">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <p className="meta-ink">PROSPECT · INBOUND</p>
              <p className="mt-1 text-sm text-mute">Group · Real Estate Buyers</p>
            </div>
            <span className="shrink-0 border border-line px-2 py-1 meta text-signal">
              SCORE 86
            </span>
          </div>

          {messages.map((m) => {
            const show = visible.includes(m.id);
            return (
              <div
                key={m.id}
                className={cn(
                  "max-w-[94%] transition-all duration-500",
                  m.role === "agent" ? "ml-auto" : "mr-auto",
                  show
                    ? "translate-y-0 opacity-100"
                    : "pointer-events-none translate-y-2 opacity-0",
                )}
              >
                <p className="meta mb-1">
                  {m.role === "prospect" ? "PROSPECT" : "RELAY AGENT"}
                </p>
                <div
                  className={cn(
                    "border px-3 py-2.5 text-[13px] leading-relaxed",
                    m.role === "agent"
                      ? "border-signal/35 bg-off"
                      : "border-line bg-paper",
                  )}
                >
                  {m.text}
                </div>
              </div>
            );
          })}
        </div>

        <aside className="flex flex-row gap-2 overflow-x-auto p-3 lg:flex-col lg:gap-3 lg:overflow-visible">
          {signals.map((s) => {
            const on = tick >= s.activeAt;
            return (
              <div
                key={s.label}
                className={cn(
                  "min-w-[122px] border px-2 py-2 transition-colors duration-300",
                  on
                    ? "border-signal bg-signal text-white"
                    : "border-line bg-paper text-mute",
                )}
              >
                <p className="font-mono text-[9px] tracking-[0.08em] leading-tight">
                  {s.label}
                </p>
              </div>
            );
          })}
          <div className="hidden border border-line px-2 py-2 lg:block">
            <p className="meta mb-1">FOLLOW-UP</p>
            <p className="font-mono text-xs text-ink">T+18H</p>
          </div>
        </aside>
      </div>

      <div className="flex items-center justify-between border-t border-line px-4 py-2">
        <span className="meta">CONTEXT ENGINE · ACTIVE</span>
        <span className="meta text-signal">BOOKING PATH OPEN</span>
      </div>
    </div>
  );
}
