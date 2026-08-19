import { cn } from "@/lib/utils";

type ScoreBarProps = {
  score: number;
  className?: string;
  showLabel?: boolean;
};

function scoreColor(score: number) {
  if (score >= 75) return "bg-[var(--stage-hot)]";
  if (score >= 50) return "bg-[var(--stage-warm)]";
  return "bg-[var(--stage-cold)]";
}

export function ScoreBar({ score, className, showLabel = true }: ScoreBarProps) {
  const clamped = Math.max(0, Math.min(100, score));
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="h-1.5 w-16 overflow-hidden rounded-[var(--radius-full)] bg-[var(--surface-2)]">
        <div
          className={cn("h-full rounded-[var(--radius-full)]", scoreColor(clamped))}
          style={{ width: `${clamped}%` }}
          role="meter"
          aria-valuenow={clamped}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Lead score ${clamped}`}
        />
      </div>
      {showLabel ? (
        <span className="text-[var(--text-xs)] font-[var(--font-semibold)] text-[var(--fg-muted)]">
          {clamped}
        </span>
      ) : null}
    </div>
  );
}
