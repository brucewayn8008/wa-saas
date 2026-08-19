"use client";

import Link from "next/link";
import {
  AlertTriangle,
  CalendarClock,
  MessageSquare,
  Power,
  Target,
  Users,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { toast } from "sonner";
import { PageHeader } from "@/components/layout/page-header";
import { StatCard } from "@/components/dashboard/stat-card";
import { UsageMeter } from "@/components/billing/usage-meter";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { useDashboard, useToggleAgent } from "@/hooks/use-dashboard";

export default function DashboardPage() {
  const { data, isLoading, isError, refetch } = useDashboard();
  const toggleAgent = useToggleAgent();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <EmptyState
        icon={AlertTriangle}
        title="Couldn’t load dashboard"
        description="Check your connection and try again."
        actionLabel="Retry"
        onAction={() => refetch()}
      />
    );
  }

  const usagePct =
    data.usage.conversationsQuota > 0
      ? data.usage.conversationsUsed / data.usage.conversationsQuota
      : 0;
  const nearQuota = usagePct >= 0.8;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description={`${data.companyName} — agent overview and recent activity`}
        actions={
          <>
            <Button variant="secondary" asChild>
              <Link href="/settings">Configure agent</Link>
            </Button>
            <Button
              variant={data.agentEnabled ? "secondary" : "default"}
              onClick={() =>
                toggleAgent.mutate(!data.agentEnabled, {
                  onSuccess: () =>
                    toast.success(data.agentEnabled ? "Agent paused" : "Agent live"),
                })
              }
              disabled={toggleAgent.isPending}
            >
              <Power className="h-4 w-4" aria-hidden="true" />
              {data.agentEnabled ? "Pause agent" : "Go live"}
            </Button>
          </>
        }
      />

      {nearQuota ? (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-[var(--radius-md)] border border-[var(--warning)] bg-[var(--warning-subtle)] px-4 py-3 text-[var(--text-sm)] text-[var(--warning)]"
        >
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <p>
            You’re nearing your conversation quota (
            {data.usage.conversationsUsed}/{data.usage.conversationsQuota}).{" "}
            <Link href="/billing" className="font-[var(--font-semibold)] underline">
              Review billing
            </Link>
          </p>
        </div>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <Badge
          variant={
            data.waStatus === "CONNECTED"
              ? "success"
              : data.waStatus === "QR_PENDING"
                ? "warning"
                : "danger"
          }
        >
          WhatsApp: {data.waStatus.replaceAll("_", " ")}
        </Badge>
        <Badge variant={data.agentEnabled ? "brand" : "outline"}>
          Agent: {data.agentEnabled ? "Live" : "Paused"}
        </Badge>
      </div>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4" aria-label="Key metrics">
        <StatCard label="Active conversations" value={data.stats.activeConversations} icon={MessageSquare} />
        <StatCard label="Hot leads" value={data.stats.hotLeads} icon={Target} />
        <StatCard label="Meetings this week" value={data.stats.meetingsBookedWeek} icon={CalendarClock} />
        <StatCard label="Messages today" value={data.stats.messagesSentToday} icon={Users} />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <Card>
          <CardHeader>
            <CardTitle>Recent activity</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.activity.length === 0 ? (
              <EmptyState
                icon={MessageSquare}
                title="No activity yet"
                description="Connect WhatsApp and go live to see agent activity."
                actionLabel="Onboarding"
                onAction={() => (window.location.href = "/onboarding")}
              />
            ) : (
              data.activity.map((item) => (
                <div
                  key={item.id}
                  className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] p-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <Badge variant="outline" className="mb-1">
                        {item.eventType.replaceAll("_", " ")}
                      </Badge>
                      <p className="text-[var(--text-sm)] font-[var(--font-semibold)]">{item.title}</p>
                      <p className="text-[var(--text-xs)] text-[var(--fg-muted)]">{item.detail}</p>
                    </div>
                    <time className="shrink-0 text-[var(--text-xs)] text-[var(--fg-subtle)]">
                      {formatDistanceToNow(new Date(item.createdAt), { addSuffix: true })}
                    </time>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Usage</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <UsageMeter
                label="Conversations"
                used={data.usage.conversationsUsed}
                quota={data.usage.conversationsQuota}
              />
              <UsageMeter
                label="Media storage"
                used={data.usage.mediaStoredMb}
                quota={data.usage.mediaQuotaMb}
                unit=" MB"
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Needs attention</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {data.needsAttention.map((item) => (
                <Link
                  key={item.id}
                  href={item.href}
                  className="block rounded-[var(--radius-md)] border border-[var(--border)] px-3 py-2 text-[var(--text-sm)] font-[var(--font-medium)] text-[var(--fg)] transition-ui hover:bg-[var(--surface-2)]"
                >
                  {item.title}
                </Link>
              ))}
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  );
}
