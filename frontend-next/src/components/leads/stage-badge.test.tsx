import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StageBadge } from "@/components/leads/stage-badge";

describe("StageBadge", () => {
  it("shows stage label for accessibility", () => {
    render(<StageBadge stage="HOT" />);
    expect(screen.getByLabelText("Stage: HOT")).toHaveTextContent("HOT");
  });
});
