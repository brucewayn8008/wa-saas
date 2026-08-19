"use client";

import { use, useEffect, useRef } from "react";
import Link from "next/link";
import { ArrowLeft, Users } from "lucide-react";
import { toast } from "sonner";
import { ChatBubble } from "@/components/conversations/chat-bubble";
import { PageHeader } from "@/components/layout/page-header";
import { StageBadge } from "@/components/leads/stage-badge";
import { ScoreBar } from "@/components/leads/score-bar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { EmptyState } from "@/components/ui/empty-state";
import { useLead, usePatchLead } from "@/hooks/use-leads";
import type { LeadStatus } from "@/types";

const STATUS_OPTIONS: LeadStatus[] = ["NEW", "IN_PROGRESS", "CONVERTED", "FAILED"];

export default function LeadDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data, isLoading, isError, refetch } = useLead(id);
  const patch = usePatchLead(id);
  const toastedError = useRef(false);

  useEffect(() => {
    if (isError && !toastedError.current) {
      toastedError.current = true;
      toast.error("Couldn’t load this lead. Try again.");
    }
    if (!isError) toastedError.current = false;
  }, [isError]);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <EmptyState
        icon={Users}
        title="Lead not found"
        description="This lead may have been removed or is unavailable."
        actionLabel="Retry"
        onAction={() => refetch()}
      />
    );
  }

  const stage = data.intentLabel;

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" asChild>
        <Link href="/leads">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back to leads
        </Link>
      </Button>

      <PageHeader
        title={data.name}
        description={data.requirementSummary || data.serviceInterest}
        actions={
          <>
            {data.conversationId ? (
              <Button variant="secondary" asChild>
                <Link href={`/conversations/${data.conversationId}`}>Open full thread</Link>
              </Button>
            ) : null}
            <Button disabled>Propose meeting</Button>
          </>
        }
      />

      <div className="flex flex-wrap items-center gap-3">
        {stage ? <StageBadge stage={stage} /> : null}
        <ScoreBar score={data.score} />
        <Badge variant="outline">{data.status.replaceAll("_", " ")}</Badge>
        <Badge variant="outline">{data.source}</Badge>
        {data.consentLabel ? <Badge variant="brand">{data.consentLabel}</Badge> : null}
        {data.doNotContact ? <Badge variant="danger">DNC</Badge> : null}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Manual controls</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="space-y-1.5">
            <Label htmlFor="lead-status">Status override</Label>
            <select
              id="lead-status"
              value={data.status}
              disabled={patch.isPending}
              onChange={(e) => {
                const status = e.target.value as LeadStatus;
                patch.mutate(
                  { status },
                  {
                    onSuccess: () => toast.success("Status updated"),
                    onError: () => toast.error("Couldn’t update status. Changes were reverted."),
                  }
                );
              }}
              className="h-10 min-w-[180px] rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-3 text-[var(--text-sm)] text-[var(--fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand)] disabled:opacity-50"
            >
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s.replaceAll("_", " ")}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-3">
            <div>
              <Label htmlFor="lead-dnc">Do not contact</Label>
              <p className="text-[var(--text-xs)] text-[var(--fg-subtle)]">
                Blocks all outbound sends for this lead.
              </p>
            </div>
            <Switch
              id="lead-dnc"
              checked={data.doNotContact}
              disabled={patch.isPending}
              onCheckedChange={(checked) => {
                patch.mutate(
                  { doNotContact: checked },
                  {
                    onSuccess: () =>
                      toast.success(checked ? "Marked do-not-contact" : "DNC cleared"),
                    onError: () =>
                      toast.error("Couldn’t update DNC. Changes were reverted."),
                  }
                );
              }}
              aria-label="Do not contact"
            />
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[1fr_1.2fr]">
        <Card>
          <CardHeader>
            <CardTitle>Memory facts</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.memoryFacts.length === 0 ? (
              <p className="text-[var(--text-sm)] text-[var(--fg-muted)]">No facts extracted yet.</p>
            ) : (
              data.memoryFacts.map((fact) => (
                <div
                  key={fact.id}
                  className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] p-3"
                >
                  <div className="mb-1 flex items-center gap-2">
                    <Badge variant="outline">{fact.category}</Badge>
                    <Badge variant={fact.source === "stated" ? "success" : "info"}>
                      {fact.source}
                    </Badge>
                  </div>
                  <p className="text-[var(--text-sm)] text-[var(--fg)]">{fact.fact}</p>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Lead summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-[var(--text-sm)] text-[var(--fg-muted)]">
            {data.phoneMasked ? (
              <p>
                <span className="font-[var(--font-semibold)] text-[var(--fg)]">Phone:</span>{" "}
                {data.phoneMasked}
              </p>
            ) : null}
            <p>
              <span className="font-[var(--font-semibold)] text-[var(--fg)]">Service:</span>{" "}
              {data.serviceInterest}
            </p>
            <p>
              <span className="font-[var(--font-semibold)] text-[var(--fg)]">Meeting:</span>{" "}
              {data.meetingStatus.replaceAll("_", " ").toLowerCase()}
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Conversation</CardTitle>
        </CardHeader>
        <CardContent>
          {data.messages.length === 0 ? (
            <p className="text-[var(--text-sm)] text-[var(--fg-muted)]">
              No messages in this thread yet.
            </p>
          ) : (
            <div className="flex max-h-[480px] flex-col gap-3 overflow-y-auto">
              {data.messages.map((message) => (
                <ChatBubble key={message.id} message={message} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
