"use client";

import { MessageSquare } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { ThreadList } from "@/components/conversations/thread-list";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { useConversations } from "@/hooks/use-conversations";

export default function ConversationsPage() {
  const { data, isLoading, isError, refetch } = useConversations();

  return (
    <div className="space-y-4">
      <PageHeader
        title="Conversations"
        description="Live WhatsApp inbox — reply manually or let the disclosed AI agent handle it."
      />

      <Card className="overflow-hidden">
        <div className="grid min-h-[560px] lg:grid-cols-[360px_1fr]">
          <div className="border-r border-[var(--border)]">
            {isLoading ? (
              <div className="space-y-3 p-4">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-20" />
                ))}
              </div>
            ) : isError ? (
              <div className="p-4">
                <EmptyState
                  icon={MessageSquare}
                  title="Couldn’t load threads"
                  description="Try again in a moment."
                  actionLabel="Retry"
                  onAction={() => refetch()}
                />
              </div>
            ) : !data?.length ? (
              <div className="p-4">
                <EmptyState
                  icon={MessageSquare}
                  title="No conversations yet"
                  description="Connect WhatsApp to start receiving inbound chats."
                  actionLabel="Connect WhatsApp"
                  onAction={() => (window.location.href = "/onboarding")}
                />
              </div>
            ) : (
              <ThreadList threads={data} />
            )}
          </div>
          <div className="hidden items-center justify-center p-8 text-center lg:flex">
            <div>
              <MessageSquare className="mx-auto mb-3 h-10 w-10 text-[var(--fg-subtle)]" aria-hidden="true" />
              <p className="font-[var(--font-semibold)] text-[var(--fg)]">Select a conversation</p>
              <p className="mt-1 text-[var(--text-sm)] text-[var(--fg-muted)]">
                Choose a thread from the list to view messages and take over from the AI.
              </p>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
