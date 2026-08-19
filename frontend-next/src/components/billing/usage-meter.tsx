import { cn } from "@/lib/utils";

type UsageMeterProps = {
  label: string;
  used: number;
  quota: number;
  unit?: string;
};

export function UsageMeter({ label, used, quota, unit = "" }: UsageMeterProps) {
  const pct = quota > 0 ? Math.min(100, Math.round((used / quota) * 100)) : 0;
  const nearLimit = pct >= 80;

  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between text-[var(--text-sm)]">
        <span className="font-[var(--font-medium)] text-[var(--fg)]">{label}</span>
        <span className={cn("text-[var(--fg-muted)]", nearLimit && "text-[var(--warning)]")}>
          {used}
          {unit} / {quota}
          {unit}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-[var(--radius-full)] bg-[var(--surface-2)]">
        <div
          className={cn(
            "h-full rounded-[var(--radius-full)] transition-ui",
            nearLimit ? "bg-[var(--warning)]" : "bg-[var(--brand)]"
          )}
          style={{ width: `${pct}%` }}
          role="progressbar"
          aria-valuenow={used}
          aria-valuemin={0}
          aria-valuemax={quota}
          aria-label={`${label}: ${used} of ${quota}`}
        />
      </div>
    </div>
  );
}
