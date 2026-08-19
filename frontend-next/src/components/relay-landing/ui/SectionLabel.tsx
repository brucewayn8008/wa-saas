import { cn } from "@/lib/relay-landing/utils";

type SectionLabelProps = {
  children: React.ReactNode;
  className?: string;
  dark?: boolean;
};

export function SectionLabel({ children, className, dark }: SectionLabelProps) {
  return (
    <p
      className={cn(
        "meta flex items-center gap-3",
        dark && "text-white/45",
        className,
      )}
    >
      <span
        className={cn(
          "inline-block h-px w-6",
          dark ? "bg-signal" : "bg-signal",
        )}
        aria-hidden
      />
      {children}
    </p>
  );
}
