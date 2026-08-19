import { format } from "date-fns";
import { Badge } from "@/components/ui/badge";
import type { ChatMessage } from "@/types";
import { cn } from "@/lib/utils";

export function ChatBubble({ message }: { message: ChatMessage }) {
  const isOutbound = message.role === "agent" || message.role === "human";
  const isAi = message.role === "agent";

  return (
    <div className={cn("flex w-full", isOutbound ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[var(--bubble-max-w)] rounded-[var(--bubble-radius)] px-3.5 py-2.5",
          isOutbound
            ? "bg-[var(--bubble-out-bg)] text-[var(--bubble-out-fg)]"
            : "bg-[var(--bubble-in-bg)] text-[var(--bubble-in-fg)]"
        )}
      >
        {isAi ? (
          <Badge variant="brand" className="mb-1.5">
            AI
          </Badge>
        ) : null}
        {message.role === "human" ? (
          <Badge variant="outline" className="mb-1.5">
            You
          </Badge>
        ) : null}
        <p className="whitespace-pre-wrap text-[var(--text-sm)] leading-relaxed">{message.text}</p>
        <div className="mt-1.5 flex items-center justify-end gap-2 text-[var(--text-xs)] text-[var(--fg-subtle)]">
          <time dateTime={message.timestamp}>
            {format(new Date(message.timestamp), "HH:mm")}
          </time>
          {message.status ? <span className="capitalize">{message.status}</span> : null}
        </div>
      </div>
    </div>
  );
}
