import { type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type EmptyStateProps = {
  icon: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
};

export function EmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-[var(--radius-lg)] border border-dashed border-[var(--border)] bg-[var(--surface)] px-6 py-12 text-center",
        className
      )}
    >
      <div className="mb-4 rounded-[var(--radius-md)] bg-[var(--brand-subtle)] p-3 text-[var(--brand)]">
        <Icon className="h-6 w-6" aria-hidden="true" />
      </div>
      <h3 className="text-[var(--text-lg)] font-[var(--font-semibold)] text-[var(--fg)]">{title}</h3>
      <p className="mt-1 max-w-sm text-[var(--text-sm)] text-[var(--fg-muted)]">{description}</p>
      {actionLabel && onAction ? (
        <Button className="mt-4" onClick={onAction}>
          {actionLabel}
        </Button>
      ) : null}
    </div>
  );
}
