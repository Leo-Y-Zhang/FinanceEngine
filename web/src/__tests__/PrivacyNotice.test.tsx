import { render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it } from "vitest";
import { PrivacyNotice } from "../components/PrivacyNotice";

describe("PrivacyNotice", () => {
  it("states what is logged, why, the retention period, and how to exercise rights", () => {
    render(<PrivacyNotice />);
    expect(screen.getByText(/ask.jsonl/)).toBeInTheDocument();
    expect(screen.getByText(/exact text of your question/i)).toBeInTheDocument();
    expect(screen.getByText(/advice-boundary classifier/i)).toBeInTheDocument();
    expect(screen.getAllByText(/legitimate interests/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/30 days/).length).toBeGreaterThan(0);
    expect(screen.getByText(/right to erasure/i)).toBeInTheDocument();
    expect(screen.getByText(/site operator/i)).toBeInTheDocument();
  });

  it("links back to the main app", () => {
    render(<PrivacyNotice />);
    expect(screen.getByRole("link", { name: /back to financeengine/i })).toHaveAttribute(
      "href",
      "#/",
    );
  });

  it("has no axe accessibility violations", async () => {
    const { container } = render(<PrivacyNotice />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
