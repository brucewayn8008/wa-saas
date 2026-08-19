"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/relay-landing/utils";

const thread = [
  {
    role: "agent" as const,
    text: "Saw your note in the operators group about scaling outbound — curious if you're still hiring SDRs or looking at automation?",
    tag: "PERSONALIZATION ACTIVE",
  },
  {
    role: "prospect" as const,
    text: "Both, honestly. Hiring is slow and our follow-up is inconsistent.",
    tag: "HIGH INTENT",
  },
  {
    role: "agent" as const,
    text: "Makes sense. Where do most conversations stall — first reply, or after they go quiet?",
    tag: null,
  },
  {
    role: "prospect" as const,
    text: "After they go quiet. We don't have capacity to chase every thread.",
    tag: "OBJECTION DETECTED",
  },
  {
    role: "agent" as const,
    text: "That's exactly the loop we run. I can show you a 15-min walkthrough of how meetings get booked without your team living in WhatsApp. Tuesday 11:00?",
    tag: "MEETING QUALIFIED",
  },
];

export function ConversationConsole() {
  const [count, setCount] = useState(1);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mq.matches) {
      const t = window.setTimeout(() => setCount(thread.length), 0);
      return () => clearTimeout(t);
    }
    let i = 1;
    const id = window.setInterval(() => {
      i = i >= thread.length ? 1 : i + 1;
      setCount(i);
    }, 2200);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="relative border border-line-dark bg-ink-soft">
      <div className="flex items-center justify-between border-b border-line-dark px-4 py-3">
        <p className="meta text-white/40">INTEL CONSOLE · THREAD 07</p>
        <p className="meta text-signal">FOLLOW-UP IN 18H</p>
      </div>

      <div className="grid lg:grid-cols-[1fr_200px]">
        <div className="space-y-4 border-b border-line-dark p-5 lg:border-b-0 lg:border-r">
          {thread.map((m, idx) => {
            const show = idx < count;
            return (
              <div
                key={idx}
                className={cn(
                  "transition-all duration-500",
                  m.role === "agent" ? "ml-0 mr-8" : "ml-8 mr-0",
                  show ? "opacity-100" : "opacity-0",
                )}
              >
                <div className="mb-1 flex items-center justify-between gap-3">
                  <p className="meta text-white/35">
                    {m.role === "agent" ? "RELAY AGENT" : "PROSPECT"}
                  </p>
                  {m.tag && show && (
                    <p className="meta text-signal">{m.tag} ↑</p>
                  )}
                </div>
                <div
                  className={cn(
                    "border px-3 py-2.5 text-[13px] leading-relaxed text-white/90",
                    m.role === "agent"
                      ? "border-white/15 bg-white/5"
                      : "border-line-dark bg-ink",
                  )}
                >
                  {m.text}
                </div>
              </div>
            );
          })}
        </div>

        <aside className="space-y-3 p-4">
          {[
            "HIGH INTENT",
            "OBJECTION DETECTED",
            "PERSONALIZATION ACTIVE",
            "FOLLOW-UP IN 18H",
            "MEETING QUALIFIED",
          ].map((label, i) => (
            <div
              key={label}
              className={cn(
                "border px-3 py-2 font-mono text-[10px] tracking-[0.08em]",
                i < count
                  ? "border-signal text-signal"
                  : "border-line-dark text-white/25",
              )}
            >
              {label}
            </div>
          ))}
        </aside>
      </div>
    </div>
  );
}
