"use client";

import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { StageBadge } from "@/components/leads/stage-badge";
import type { ConversationSummary } from "@/types";
import { cn } from "@/lib/utils";

type ThreadListProps = {
  threads: ConversationSummary[];
  activeId?: string;
};

export function ThreadList({ threads, activeId }: ThreadListProps) {
  return (
    <ul className="divide-y divide-[var(--border)]" role="list" aria-label="Conversation threads">
      {threads.map((thread) => {
        const active = thread.id === activeId;
        return (
          <li key={thread.id}>
            <Link
              href={`/conversations/${thread.id}`}
              className={cn(
                "block px-4 py-3 transition-ui hover:bg-[var(--surface-2)] focus-visible:bg-[var(--surface-2)]",
                active && "bg-[var(--brand-subtle)]"
              )}
              aria-current={active ? "page" : undefined}
            >
              <div className="flex items-start justify-between gap-2">
                <p className="font-[var(--font-semibold)] text-[var(--fg)]">{thread.contactName}</p>
                <time className="shrink-0 text-[var(--text-xs)] text-[var(--fg-subtle)]">
                  {formatDistanceToNow(new Date(thread.updatedAt), { addSuffix: true })}
                </time>
              </div>
              <p className="mt-1 line-clamp-1 text-[var(--text-sm)] text-[var(--fg-muted)]">
                {thread.lastMessage}
              </p>
              <div className="mt-2 flex items-center gap-2">
                <StageBadge stage={thread.stage} />
                {thread.unread > 0 ? (
                  <span className="rounded-[var(--radius-full)] bg-[var(--brand)] px-2 py-0.5 text-[10px] font-[var(--font-bold)] text-[var(--brand-fg)]">
                    {thread.unread}
                  </span>
                ) : null}
                {thread.humanTakeover ? (
                  <span className="text-[var(--text-xs)] text-[var(--warning)]">Takeover</span>
                ) : null}
              </div>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
