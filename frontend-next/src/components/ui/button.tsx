import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-[var(--radius-md)] text-[var(--text-sm)] font-[var(--font-semibold)] transition-ui focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand)] focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "bg-[var(--brand)] text-[var(--brand-fg)] hover:bg-[var(--brand-hover)] shadow-[var(--shadow-sm)]",
        secondary:
          "border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--fg)] hover:bg-[var(--surface-2)]",
        ghost: "text-[var(--fg-muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]",
        danger:
          "bg-[var(--danger)] text-white hover:opacity-90 shadow-[var(--shadow-sm)]",
        outline:
          "border border-[var(--border-strong)] bg-transparent text-[var(--fg)] hover:bg-[var(--surface-2)]",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-8 px-3 text-[var(--text-xs)]",
        lg: "h-11 px-6",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
