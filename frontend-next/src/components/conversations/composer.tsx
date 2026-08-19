"use client";

import { useState } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

type ComposerProps = {
  disabled?: boolean;
  disabledReason?: string;
  within24hWindow?: boolean;
  onSend: (text: string) => void;
};

export function Composer({
  disabled,
  disabledReason,
  within24hWindow = true,
  onSend,
}: ComposerProps) {
  const [text, setText] = useState("");

  const submit = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
  };

  return (
    <div className="border-t border-[var(--border)] bg-[var(--surface)] p-4">
      {!within24hWindow ? (
        <p className="mb-2 text-[var(--text-xs)] text-[var(--warning)]">
          Outside 24h customer-service window — a template may be required.
        </p>
      ) : (
        <p className="mb-2 text-[var(--text-xs)] text-[var(--fg-subtle)]">
          Within customer service window
        </p>
      )}
      {disabled && disabledReason ? (
        <p className="mb-2 rounded-[var(--radius-md)] bg-[var(--danger-subtle)] px-3 py-2 text-[var(--text-sm)] text-[var(--danger)]">
          {disabledReason}
        </p>
      ) : null}
      <div className="flex gap-2">
        <Textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={disabled ? "Composer disabled" : "Type a reply…"}
          disabled={disabled}
          aria-label="Message composer"
          className="min-h-[72px] resize-none"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
        />
        <Button
          onClick={submit}
          disabled={disabled || !text.trim()}
          aria-label="Send message"
          className="self-end"
        >
          <Send className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}
