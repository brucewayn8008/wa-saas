"use client";

import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/relay-landing/utils";

type RevealProps = {
  children: React.ReactNode;
  className?: string;
  delay?: number;
  y?: number;
  as?: "div" | "section" | "article" | "header" | "li";
};

export function Reveal({
  children,
  className,
  delay = 0,
  y = 28,
  as = "div",
}: RevealProps) {
  const reduce = useReducedMotion();
  const Comp = motion[as];

  return (
    <Comp
      className={cn(className)}
      initial={reduce ? false : { opacity: 0, y }}
      whileInView={reduce ? undefined : { opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-10% 0px -8% 0px" }}
      transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1], delay }}
    >
      {children}
    </Comp>
  );
}
