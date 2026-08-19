"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { cn } from "@/lib/relay-landing/utils";

const stages = [
  { id: "01", title: "WHATSAPP GROUPS", sub: "Source surface" },
  { id: "02", title: "LEAD DISCOVERY", sub: "Signal extraction" },
  { id: "03", title: "LEAD ENRICHMENT", sub: "Context attach" },
  { id: "04", title: "CONTEXT ENGINE", sub: "Relevance model" },
  { id: "05", title: "PERSONALIZED OUTREACH", sub: "Open generation" },
  { id: "06", title: "CONVERSATION ENGINE", sub: "Dialogue control" },
  { id: "07", title: "INTENT DETECTION", sub: "Purchase signals" },
  { id: "08", title: "FOLLOW-UP ENGINE", sub: "Cadence control" },
  { id: "09", title: "MEETING BOOKING", sub: "Calendar commit" },
];

export function InfrastructureMap({ className }: { className?: string }) {
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    gsap.registerPlugin(ScrollTrigger);
    const ctx = gsap.context(() => {
      gsap.from("[data-stage]", {
        opacity: 0,
        y: 14,
        stagger: 0.05,
        duration: 0.4,
        ease: "power2.out",
        scrollTrigger: {
          trigger: root.current,
          start: "top 75%",
          once: true,
        },
      });
      gsap.from("[data-flow]", {
        strokeDashoffset: 240,
        duration: 1.2,
        ease: "power2.inOut",
        scrollTrigger: {
          trigger: root.current,
          start: "top 75%",
          once: true,
        },
      });
    }, root);
    return () => ctx.revert();
  }, []);

  return (
    <div
      ref={root}
      className={cn(
        "border border-line bg-paper grid-bg overflow-hidden",
        className,
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-3">
        <p className="meta">FIG. 04 — INTELLIGENCE INFRASTRUCTURE</p>
        <p className="meta">STAGES 01–09 · RED PATH = ACTIVE FLOW</p>
      </div>

      <div className="relative p-4 md:p-8">
        <svg
          className="pointer-events-none absolute inset-x-8 top-1/2 hidden h-24 -translate-y-1/2 lg:block"
          viewBox="0 0 1000 100"
          fill="none"
          aria-hidden
        >
          <path
            data-flow
            d="M20 50 H980"
            stroke="#00C2D7"
            strokeWidth="1.5"
            strokeDasharray="240"
            strokeDashoffset="0"
            opacity="0.55"
          />
        </svg>

        <div className="relative grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {stages.map((stage, i) => (
            <div key={stage.id} data-stage>
              <div className="flex h-full min-h-[128px] flex-col justify-between border border-ink/90 bg-paper p-4">
                <div className="flex items-start justify-between gap-3">
                  <span className="font-mono text-[11px] text-signal">
                    {stage.id}
                  </span>
                  <span className="relative flex h-2 w-2">
                    <span className="absolute inset-0 animate-pulse-node bg-signal" />
                    <span className="relative h-2 w-2 bg-signal" />
                  </span>
                </div>
                <div>
                  <p className="text-sm font-medium tracking-tight">
                    {stage.title}
                  </p>
                  <p className="meta mt-2">{stage.sub}</p>
                  {i < stages.length - 1 && (
                    <p className="meta mt-3 text-signal">↓ NEXT</p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-6 flex flex-col gap-2 border border-line bg-off p-4 md:flex-row md:items-center md:justify-between">
          <p className="meta-ink">
            INPUT: COMMUNITIES → OUTPUT: BOOKED MEETINGS
          </p>
          <p className="meta text-signal">HUMAN ESCALATION NODE AVAILABLE</p>
        </div>
      </div>
    </div>
  );
}
