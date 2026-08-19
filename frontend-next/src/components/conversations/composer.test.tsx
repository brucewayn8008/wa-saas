import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Composer } from "@/components/conversations/composer";

describe("Composer", () => {
  it("disables with DNC explanation", () => {
    render(
      <Composer
        disabled
        disabledReason="This contact is on do-not-contact. Composer is disabled."
        onSend={vi.fn()}
      />
    );
    expect(
      screen.getByText("This contact is on do-not-contact. Composer is disabled.")
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Message composer")).toBeDisabled();
  });

  it("shows 24h window hint", () => {
    render(<Composer within24hWindow onSend={vi.fn()} />);
    expect(screen.getByText("Within customer service window")).toBeInTheDocument();
  });
});
