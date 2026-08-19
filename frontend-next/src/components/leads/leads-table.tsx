"use client";

import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { Users } from "lucide-react";
import { StageBadge } from "@/components/leads/stage-badge";
import { ScoreBar } from "@/components/leads/score-bar";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import type { Lead } from "@/types";

type LeadsTableProps = {
  items: Lead[];
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
};

export function LeadsTable({ items, isLoading, isError, onRetry }: LeadsTableProps) {
  return (
    <Card>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="space-y-3 p-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-14" />
            ))}
          </div>
        ) : isError ? (
          <div className="p-4">
            <EmptyState
              icon={Users}
              title="Couldn’t load leads"
              description="Try again shortly."
              actionLabel="Retry"
              onAction={onRetry}
            />
          </div>
        ) : items.length === 0 ? (
          <div className="p-4">
            <EmptyState
              icon={Users}
              title="No leads match"
              description="Adjust filters or wait for inbound WhatsApp conversations."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[800px] text-left text-[var(--text-sm)]">
              <thead className="border-b border-[var(--border)] bg-[var(--surface-2)] text-[var(--fg-muted)]">
                <tr>
                  <th className="px-4 py-3 font-[var(--font-semibold)]">Name</th>
                  <th className="px-4 py-3 font-[var(--font-semibold)]">Intent</th>
                  <th className="px-4 py-3 font-[var(--font-semibold)]">Status</th>
                  <th className="px-4 py-3 font-[var(--font-semibold)]">Score</th>
                  <th className="px-4 py-3 font-[var(--font-semibold)]">Service</th>
                  <th className="px-4 py-3 font-[var(--font-semibold)]">Source</th>
                  <th className="px-4 py-3 font-[var(--font-semibold)]">Last inbound</th>
                  <th className="px-4 py-3 font-[var(--font-semibold)]">Meeting</th>
                </tr>
              </thead>
              <tbody>
                {items.map((lead) => (
                    <tr
                      key={lead.id}
                      className="border-b border-[var(--border)] transition-ui hover:bg-[var(--surface-2)]"
                    >
                      <td className="px-4 py-3">
                        <Link
                          href={`/leads/${lead.id}`}
                          className="font-[var(--font-semibold)] text-[var(--fg)] hover:text-[var(--brand)]"
                        >
                          {lead.name}
                        </Link>
                        {lead.phoneMasked ? (
                          <p className="text-[var(--text-xs)] text-[var(--fg-subtle)]">
                            {lead.phoneMasked}
                          </p>
                        ) : null}
                        {lead.doNotContact ? (
                          <Badge variant="danger" className="mt-1">
                            DNC
                          </Badge>
                        ) : null}
                      </td>
                      <td className="px-4 py-3">
                        {lead.intentLabel ? (
                          <StageBadge stage={lead.intentLabel} />
                        ) : (
                          <span className="text-[var(--fg-subtle)]">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant="outline">{lead.status.replaceAll("_", " ")}</Badge>
                      </td>
                      <td className="px-4 py-3">
                        <ScoreBar score={lead.score} />
                      </td>
                      <td className="px-4 py-3 text-[var(--fg-muted)]">
                        {lead.serviceInterest}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant="outline">{lead.source}</Badge>
                      </td>
                      <td className="px-4 py-3 text-[var(--fg-subtle)]">
                        {lead.lastInboundAt
                          ? formatDistanceToNow(new Date(lead.lastInboundAt), {
                              addSuffix: true,
                            })
                          : "—"}
                      </td>
                      <td className="px-4 py-3 capitalize text-[var(--fg-muted)]">
                        {lead.meetingStatus.replaceAll("_", " ").toLowerCase()}
                      </td>
                    </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
