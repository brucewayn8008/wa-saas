import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ScoreBar } from "@/components/leads/score-bar";

describe("ScoreBar", () => {
  it("renders score label and meter value", () => {
    render(<ScoreBar score={87} />);
    expect(screen.getByText("87")).toBeInTheDocument();
    expect(screen.getByRole("meter")).toHaveAttribute("aria-valuenow", "87");
  });

  it("clamps score to 0–100", () => {
    render(<ScoreBar score={150} />);
    expect(screen.getByRole("meter")).toHaveAttribute("aria-valuenow", "100");
  });
});
