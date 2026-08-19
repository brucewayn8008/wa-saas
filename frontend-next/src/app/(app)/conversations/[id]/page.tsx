"use client";

import { use } from "react";
import Link from "next/link";
import { ArrowLeft, MessageSquare } from "lucide-react";
import { toast } from "sonner";
import { ChatBubble } from "@/components/conversations/chat-bubble";
import { Composer } from "@/components/conversations/composer";
import { ThreadList } from "@/components/conversations/thread-list";
import { StageBadge } from "@/components/leads/stage-badge";
import { ScoreBar } from "@/components/leads/score-bar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { EmptyState } from "@/components/ui/empty-state";
import {
  useConversation,
  useConversations,
  useSendReply,
  useTakeover,
} from "@/hooks/use-conversations";

export default function ConversationDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const threads = useConversations();
  const { data, isLoading, isError, refetch } = useConversation(id);
  const sendReply = useSendReply(id);
  const takeover = useTakeover(id);

  return (
    <div className="space-y-4">
      <Button variant="ghost" size="sm" asChild className="lg:hidden">
        <Link href="/conversations">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back to inbox
        </Link>
      </Button>

      <Card className="overflow-hidden">
        <div className="grid min-h-[640px] lg:grid-cols-[360px_1fr]">
          <div className="hidden border-r border-[var(--border)] lg:block">
            {threads.data ? <ThreadList threads={threads.data} activeId={id} /> : null}
          </div>

          <div className="flex min-h-[640px] flex-col">
            {isLoading ? (
              <div className="space-y-3 p-4">
                <Skeleton className="h-12" />
                <Skeleton className="h-40" />
                <Skeleton className="h-40" />
              </div>
            ) : isError || !data ? (
              <div className="p-6">
                <EmptyState
                  icon={MessageSquare}
                  title="Conversation unavailable"
                  description="This thread could not be loaded."
                  actionLabel="Retry"
                  onAction={() => refetch()}
                />
              </div>
            ) : (
              <>
                <div className="border-b border-[var(--border)] px-4 py-3">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <h1 className="text-[var(--text-lg)] font-[var(--font-bold)]">
                          {data.contactName}
                        </h1>
                        <StageBadge stage={data.stage} />
                        {data.doNotContact ? <Badge variant="danger">DNC</Badge> : null}
                      </div>
                      <div className="mt-2">
                        <ScoreBar score={data.score} />
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <label
                        htmlFor="takeover"
                        className="text-[var(--text-sm)] font-[var(--font-medium)]"
                      >
                        Human takeover
                      </label>
                      <Switch
                        id="takeover"
                        checked={data.humanTakeover}
                        onCheckedChange={(checked) =>
                          takeover.mutate(checked, {
                            onSuccess: () =>
                              toast.message(
                                checked ? "Agent paused — you're replying" : "Agent resumed"
                              ),
                          })
                        }
                        aria-label="Toggle human takeover"
                      />
                    </div>
                  </div>
                  {data.humanTakeover ? (
                    <div
                      role="status"
                      className="mt-3 rounded-[var(--radius-md)] bg-[var(--warning-subtle)] px-3 py-2 text-[var(--text-sm)] text-[var(--warning)]"
                    >
                      Agent paused — you&apos;re replying.
                    </div>
                  ) : null}
                </div>

                <div className="flex-1 space-y-3 overflow-y-auto p-4" aria-live="polite">
                  {data.messages.map((message) => (
                    <ChatBubble key={message.id} message={message} />
                  ))}
                </div>

                <Composer
                  disabled={data.doNotContact}
                  disabledReason={
                    data.doNotContact
                      ? "This contact is on do-not-contact. Composer is disabled."
                      : undefined
                  }
                  within24hWindow={data.within24hWindow}
                  onSend={(text) =>
                    sendReply.mutate(text, {
                      onSuccess: () => toast.success("Message sent"),
                      onError: (e) => toast.error(e.message),
                    })
                  }
                />
              </>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}
