import { Badge } from "@/components/ui/badge";
import type { LeadStage } from "@/types";
import { cn } from "@/lib/utils";

const stageStyles: Record<LeadStage, string> = {
  NEW: "bg-[var(--surface-2)] text-[var(--stage-new)]",
  HOT: "bg-[var(--danger-subtle)] text-[var(--stage-hot)]",
  WARM: "bg-[var(--warning-subtle)] text-[var(--stage-warm)]",
  COLD: "bg-[var(--info-subtle)] text-[var(--stage-cold)]",
  CONVERTED: "bg-[var(--success-subtle)] text-[var(--stage-converted)]",
  FAILED: "bg-[var(--danger-subtle)] text-[var(--danger)]",
};

export function StageBadge({ stage, className }: { stage: LeadStage; className?: string }) {
  return (
    <Badge
      className={cn(stageStyles[stage], className)}
      aria-label={`Stage: ${stage}`}
    >
      {stage}
    </Badge>
  );
}
