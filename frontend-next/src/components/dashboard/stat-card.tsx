import { type LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

type StatCardProps = {
  label: string;
  value: string | number;
  icon: LucideIcon;
};

export function StatCard({ label, value, icon: Icon }: StatCardProps) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between p-5">
        <div>
          <p className="text-[var(--text-xs)] font-[var(--font-bold)] uppercase tracking-wider text-[var(--fg-subtle)]">
            {label}
          </p>
          <p className="mt-2 text-[var(--text-2xl)] font-[var(--font-bold)] text-[var(--fg)]">
            {value}
          </p>
        </div>
        <div className="rounded-[var(--radius-md)] border border-[var(--brand-subtle)] bg-[var(--brand-subtle)] p-3 text-[var(--brand)]">
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
      </CardContent>
    </Card>
  );
}
