"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { cn } from "@/lib/relay-landing/utils";

const nodes = [
  "DISCOVER",
  "IDENTIFY",
  "START CONVERSATION",
  "QUALIFY",
  "FOLLOW UP",
  "BOOK MEETING",
  "HAND OFF",
];

export function SalesLoop({ className }: { className?: string }) {
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mq.matches) return;

    gsap.registerPlugin(ScrollTrigger);
    const ctx = gsap.context(() => {
      const items = gsap.utils.toArray<HTMLElement>("[data-node]");
      const lines = gsap.utils.toArray<HTMLElement>("[data-line]");

      gsap.set(items, { opacity: 0.35 });
      gsap.set(lines, { scaleY: 0, transformOrigin: "top center" });

      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: root.current,
          start: "top 70%",
          once: true,
        },
      });

      items.forEach((item, i) => {
        tl.to(item, { opacity: 1, duration: 0.35, ease: "power2.out" }, i * 0.22);
        if (lines[i]) {
          tl.to(
            lines[i],
            { scaleY: 1, duration: 0.28, ease: "power2.inOut" },
            i * 0.22 + 0.12,
          );
        }
      });

      tl.to(
        "[data-active-pulse]",
        { opacity: 1, duration: 0.3 },
        "-=0.1",
      );
    }, root);

    return () => ctx.revert();
  }, []);

  return (
    <div
      ref={root}
      className={cn("border border-line bg-paper grid-bg", className)}
    >
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <p className="meta">FIG. 03 — AUTONOMOUS SALES LOOP</p>
        <p className="meta text-signal" data-active-pulse style={{ opacity: 0.4 }}>
          SYSTEM ACTIVE
        </p>
      </div>

      <div className="px-4 py-8 md:px-8">
        <ul className="mx-auto flex max-w-md flex-col">
          {nodes.map((node, i) => (
            <li key={node} className="flex flex-col items-stretch">
              <div
                data-node
                className={cn(
                  "relative flex items-center justify-between border border-ink bg-paper px-4 py-3",
                  i === nodes.length - 1 && "border-signal",
                )}
              >
                <div className="flex items-center gap-3">
                  <span
                    className={cn(
                      "h-2 w-2 animate-pulse-node",
                      i === nodes.length - 1 ? "bg-signal" : "bg-ink",
                    )}
                    aria-hidden
                  />
                  <span className="text-sm font-medium tracking-tight">
                    {node}
                  </span>
                </div>
                <span className="font-mono text-[10px] text-mute">
                  N{String(i + 1).padStart(2, "0")}
                </span>
              </div>
              {i < nodes.length - 1 && (
                <div className="relative mx-auto flex h-8 w-px items-stretch justify-center">
                  <span
                    data-line
                    className="block w-px bg-signal"
                    aria-hidden
                  />
                </div>
              )}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
