import { cn } from "@/lib/utils";

type PageHeaderProps = {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  className?: string;
};

export function PageHeader({ title, description, actions, className }: PageHeaderProps) {
  return (
    <div
      className={cn(
        "mb-[var(--space-6)] flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between",
        className
      )}
    >
      <div>
        <h1 className="text-[var(--text-xl)] font-[var(--font-bold)] tracking-tight text-[var(--fg)]">
          {title}
        </h1>
        {description ? (
          <p className="mt-1 text-[var(--text-sm)] text-[var(--fg-muted)]">{description}</p>
        ) : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}
