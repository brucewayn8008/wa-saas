import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApprovalCard } from "@/components/listening/approval-card";

const item = {
  id: "li1",
  groupName: "Indie Hackers Delhi",
  originalMessage: "Anyone know a good web developer?",
  matchReason: "keyword" as const,
  draftReply: "Happy to help with restaurant sites.",
  createdAt: new Date().toISOString(),
  status: "sent" as const,
};

describe("ApprovalCard", () => {
  it("shows auto-replied feed with dismiss only (no approve)", async () => {
    const onDismiss = vi.fn();
    const user = userEvent.setup();
    render(<ApprovalCard item={item} onDismiss={onDismiss} />);

    expect(screen.getByText("Auto-replied")).toBeInTheDocument();
    expect(screen.getByText("AI reply sent to lead")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Approve/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Send$/ })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(onDismiss).toHaveBeenCalledWith("li1");
  });
});
