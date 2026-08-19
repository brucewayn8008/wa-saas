import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-[var(--radius-full)] px-2.5 py-0.5 text-[var(--text-xs)] font-[var(--font-medium)]",
  {
    variants: {
      variant: {
        default: "bg-[var(--surface-2)] text-[var(--fg)]",
        brand: "bg-[var(--brand-subtle)] text-[var(--brand)]",
        success: "bg-[var(--success-subtle)] text-[var(--success)]",
        warning: "bg-[var(--warning-subtle)] text-[var(--warning)]",
        danger: "bg-[var(--danger-subtle)] text-[var(--danger)]",
        info: "bg-[var(--info-subtle)] text-[var(--info)]",
        outline: "border border-[var(--border-strong)] text-[var(--fg-muted)]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}
