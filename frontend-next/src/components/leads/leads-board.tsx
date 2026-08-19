"use client";

import { useEffect, useRef } from "react";
import {
  parseAsInteger,
  parseAsString,
  parseAsStringEnum,
  useQueryStates,
} from "nuqs";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LeadsTable } from "@/components/leads/leads-table";
import { useLeads } from "@/hooks/use-leads";
import type { LeadIntent, LeadSource, LeadStatus } from "@/types";

const STATUS_VALUES = ["NEW", "IN_PROGRESS", "CONVERTED", "FAILED"] as const;
const INTENT_VALUES = ["HOT", "WARM", "COLD"] as const;
const SOURCE_VALUES = ["DIRECT", "GROUP", "AD", "WIDGET"] as const;

const SCORE_OPTIONS = [
  { label: "Any score", value: 0 },
  { label: "50+", value: 50 },
  { label: "75+", value: 75 },
];

const filterParsers = {
  status: parseAsStringEnum([...STATUS_VALUES]),
  intent: parseAsStringEnum([...INTENT_VALUES]),
  source: parseAsStringEnum([...SOURCE_VALUES]),
  minScore: parseAsInteger.withDefault(0),
  q: parseAsString.withDefault(""),
};

function ChipGroup<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T | null;
  options: Array<{ value: T | null; label: string }>;
  onChange: (next: T | null) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label={label}>
      {options.map((opt) => {
        const selected = value === opt.value;
        return (
          <button
            key={opt.label}
            type="button"
            aria-pressed={selected}
            onClick={() => onChange(opt.value)}
            className={`rounded-[var(--radius-full)] px-3 py-1.5 text-[var(--text-xs)] font-[var(--font-semibold)] transition-ui ${
              selected
                ? "bg-[var(--brand)] text-[var(--brand-fg)]"
                : "bg-[var(--surface-2)] text-[var(--fg-muted)] hover:text-[var(--fg)]"
            }`}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

export function LeadsBoard() {
  const [filters, setFilters] = useQueryStates(filterParsers, {
    history: "replace",
    shallow: false,
  });

  const listFilters = {
    status: (filters.status ?? "") as LeadStatus | "",
    intent: (filters.intent ?? "") as LeadIntent | "",
    source: (filters.source ?? "") as LeadSource | "",
    minScore: filters.minScore > 0 ? filters.minScore : null,
    search: filters.q || "",
  };

  const { data, isLoading, isError, isFetching, refetch } = useLeads(listFilters);
  const toastedError = useRef(false);

  useEffect(() => {
    if (isError && !toastedError.current) {
      toastedError.current = true;
      toast.error("Couldn’t load leads. Try again.");
    }
    if (!isError) toastedError.current = false;
  }, [isError]);

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
          <div className="w-full max-w-sm space-y-1.5">
            <Label htmlFor="leads-search">Search</Label>
            <Input
              id="leads-search"
              placeholder="Search leads…"
              value={filters.q}
              onChange={(e) => setFilters({ q: e.target.value || null })}
              aria-label="Search leads"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="leads-min-score">Min score</Label>
            <select
              id="leads-min-score"
              value={filters.minScore}
              onChange={(e) =>
                setFilters({ minScore: Number(e.target.value) || null })
              }
              className="h-10 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-3 text-[var(--text-sm)] text-[var(--fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand)]"
            >
              {SCORE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <ChipGroup
          label="Status filters"
          value={filters.status}
          options={[
            { value: null, label: "All status" },
            ...STATUS_VALUES.map((s) => ({
              value: s as LeadStatus,
              label: s.replaceAll("_", " "),
            })),
          ]}
          onChange={(status) => setFilters({ status })}
        />

        <ChipGroup
          label="Intent filters"
          value={filters.intent}
          options={[
            { value: null, label: "All intent" },
            ...INTENT_VALUES.map((s) => ({
              value: s as LeadIntent,
              label: s,
            })),
          ]}
          onChange={(intent) => setFilters({ intent })}
        />

        <ChipGroup
          label="Source filters"
          value={filters.source}
          options={[
            { value: null, label: "All sources" },
            ...SOURCE_VALUES.map((s) => ({
              value: s as LeadSource,
              label: s,
            })),
          ]}
          onChange={(source) => setFilters({ source })}
        />
      </div>

      <LeadsTable
        items={data?.items ?? []}
        isLoading={isLoading || (isFetching && !data)}
        isError={isError}
        onRetry={() => refetch()}
      />
    </div>
  );
}
