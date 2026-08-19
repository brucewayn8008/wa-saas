import Link from "next/link";
import { cn, BOOK_HREF } from "@/lib/relay-landing/utils";

type BookButtonProps = {
  className?: string;
  label?: string;
  href?: string;
  variant?: "solid" | "ghost" | "outline";
  size?: "sm" | "md" | "lg";
};

export function BookButton({
  className,
  label = "BOOK A CALL →",
  href,
  variant = "solid",
  size = "md",
}: BookButtonProps) {
  return (
    <Link
      href={href ?? BOOK_HREF}
      className={cn(
        "inline-flex items-center justify-center font-medium tracking-[0.04em] uppercase transition-colors duration-200",
        size === "sm" && "h-9 px-4 text-[11px]",
        size === "md" && "h-11 px-5 text-xs",
        size === "lg" && "h-14 px-8 text-sm",
        variant === "solid" &&
          "bg-signal text-white hover:bg-signal-deep focus-visible:bg-signal-deep",
        variant === "ghost" &&
          "bg-transparent text-ink hover:text-signal border-b border-transparent hover:border-signal rounded-none px-0",
        variant === "outline" &&
          "border border-ink bg-transparent text-ink hover:bg-ink hover:text-paper",
        className,
      )}
    >
      {label}
    </Link>
  );
}
