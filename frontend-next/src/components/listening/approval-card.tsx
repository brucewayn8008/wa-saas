"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ListeningItem } from "@/types";
import { formatDistanceToNow } from "date-fns";

type ApprovalCardProps = {
  item: ListeningItem;
  onDismiss: (id: string) => void;
  dismissing?: boolean;
};

function statusBadge(item: ListeningItem) {
  if (item.status === "sent") {
    return <Badge variant="success">Auto-replied</Badge>;
  }
  if (item.status === "blocked") {
    return <Badge variant="warning">Blocked by policy</Badge>;
  }
  return <Badge variant="outline">Processing</Badge>;
}

export function ApprovalCard({ item, onDismiss, dismissing }: ApprovalCardProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <CardTitle className="text-[var(--text-base)]">{item.groupName}</CardTitle>
          {statusBadge(item)}
          <Badge variant="outline">{item.matchReason}</Badge>
        </div>
        <p className="text-[var(--text-xs)] text-[var(--fg-subtle)]">
          {formatDistanceToNow(new Date(item.createdAt), { addSuffix: true })}
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <p className="mb-1.5 text-[var(--text-sm)] font-[var(--font-medium)] text-[var(--fg-muted)]">
            Public group message
          </p>
          <blockquote className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-[var(--text-sm)] text-[var(--fg)]">
            “{item.originalMessage}”
          </blockquote>
        </div>
        <div>
          <p className="mb-1.5 text-[var(--text-sm)] font-[var(--font-medium)] text-[var(--fg-muted)]">
            AI reply sent to lead
          </p>
          <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-[var(--text-sm)] text-[var(--fg)]">
            {item.draftReply || (
              <span className="text-[var(--fg-subtle)]">Reply pending…</span>
            )}
          </div>
          {item.status === "blocked" && item.blockReason ? (
            <p className="mt-1.5 text-[var(--text-xs)] text-[var(--warning)]">
              Gate: {item.blockReason}
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="ghost"
            disabled={dismissing}
            onClick={() => onDismiss(item.id)}
          >
            Dismiss
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
