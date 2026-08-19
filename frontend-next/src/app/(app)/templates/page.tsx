"use client";

import { FileText } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { useTemplates } from "@/hooks/use-settings";
import type { TemplateStatus } from "@/types";

function statusVariant(status: TemplateStatus) {
  if (status === "approved") return "success" as const;
  if (status === "pending") return "warning" as const;
  return "danger" as const;
}

export default function TemplatesPage() {
  const { data, isLoading, isError, refetch } = useTemplates();

  return (
    <div className="space-y-4">
      <PageHeader
        title="Templates"
        description="WhatsApp-approved templates for opt-in re-engagement only. Never used for cold outreach."
        actions={<Button>Create template</Button>}
      />

      <div
        role="note"
        className="rounded-[var(--radius-md)] border border-[var(--info)] bg-[var(--info-subtle)] px-4 py-3 text-[var(--text-sm)] text-[var(--info)]"
      >
        Template sends only go to contacts with recorded opt-in, pass the compliance gate, and
        respect rate limits / 24h window rules.
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-3 p-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-16" />
              ))}
            </div>
          ) : isError ? (
            <div className="p-4">
              <EmptyState
                icon={FileText}
                title="Couldn’t load templates"
                description="Try again shortly."
                actionLabel="Retry"
                onAction={() => refetch()}
              />
            </div>
          ) : !data?.length ? (
            <div className="p-4">
              <EmptyState
                icon={FileText}
                title="No templates yet"
                description="Create an approved WhatsApp template for opted-in re-engagement."
                actionLabel="Create template"
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-[var(--text-sm)]">
                <thead className="border-b border-[var(--border)] bg-[var(--surface-2)] text-[var(--fg-muted)]">
                  <tr>
                    <th className="px-4 py-3 font-[var(--font-semibold)]">Name</th>
                    <th className="px-4 py-3 font-[var(--font-semibold)]">Language</th>
                    <th className="px-4 py-3 font-[var(--font-semibold)]">Status</th>
                    <th className="px-4 py-3 font-[var(--font-semibold)]">Body</th>
                    <th className="px-4 py-3 font-[var(--font-semibold)]">Last used</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((tpl) => (
                    <tr key={tpl.id} className="border-b border-[var(--border)]">
                      <td className="px-4 py-3 font-[var(--font-semibold)]">{tpl.name}</td>
                      <td className="px-4 py-3 text-[var(--fg-muted)]">{tpl.language}</td>
                      <td className="px-4 py-3">
                        <Badge variant={statusVariant(tpl.status)}>{tpl.status}</Badge>
                      </td>
                      <td className="max-w-xs truncate px-4 py-3 text-[var(--fg-muted)]">
                        {tpl.body}
                      </td>
                      <td className="px-4 py-3 text-[var(--fg-subtle)]">
                        {tpl.lastUsedAt
                          ? formatDistanceToNow(new Date(tpl.lastUsedAt), { addSuffix: true })
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
