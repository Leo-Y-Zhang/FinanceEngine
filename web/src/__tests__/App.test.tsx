import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import type { AskResponse } from "../types";

const ANSWER: AskResponse = {
  kind: "answer",
  question: "How does a Lifetime ISA work?",
  claims: [
    {
      text: "You can put in up to £4,000 each year until you are 50.",
      citation: {
        org: "GOVUK",
        title: "Lifetime ISA",
        url: "https://www.gov.uk/lifetime-isa",
        fetched_at: "2026-07-21",
        last_updated: "2026-04-06",
      },
      confidence: "established",
    },
    {
      text: "If you withdraw for other reasons you pay a 25% charge.",
      citation: {
        org: "GOVUK",
        title: "Lifetime ISA",
        url: "https://www.gov.uk/lifetime-isa",
        fetched_at: "2026-07-21",
        last_updated: null,
      },
      confidence: "depends",
    },
  ],
  disclaimer: "Pistis provides information and guidance, not regulated financial advice.",
};

const ROUTING: AskResponse = {
  kind: "routing",
  question: "Which ISA should I open?",
  reason: "This looks like a request for a personal recommendation.",
  matched: ["should-i"],
  routing: {
    message: "Guidance cannot tell you what is right for you.",
    links: [
      { label: "MoneyHelper", url: "https://www.moneyhelper.org.uk/en" },
      { label: "FCA Register", url: "https://register.fca.org.uk/" },
    ],
  },
  disclaimer: "Guidance, not advice.",
};

const ABSTAIN: AskResponse = {
  kind: "abstain",
  question: "How do I renew my passport?",
  reason: "The sources Pistis trusts do not cover this well enough to answer reliably.",
  routing: {
    message: "Here is where to go next.",
    links: [{ label: "MoneyHelper", url: "https://www.moneyhelper.org.uk/en" }],
  },
  disclaimer: "Guidance, not advice.",
};

function mockAsk(response: AskResponse) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({
      ok: true,
      json: async () => response,
    })),
  );
}

async function askQuestion(text: string) {
  const user = userEvent.setup();
  await user.type(screen.getByRole("textbox"), text);
  await user.click(screen.getByRole("button", { name: /ask/i }));
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App", () => {
  it("renders the persistent guidance-not-advice banner before any question", () => {
    render(<App />);
    expect(
      screen.getByText(/not regulated financial advice/i),
    ).toBeInTheDocument();
  });

  it("renders an answer as a cited claim ledger", async () => {
    mockAsk(ANSWER);
    render(<App />);
    await askQuestion("How does a Lifetime ISA work?");
    await waitFor(() =>
      expect(screen.getByRole("list")).toBeInTheDocument(),
    );
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    const links = screen.getAllByRole("link", { name: "Lifetime ISA" });
    expect(links[0]).toHaveAttribute("href", "https://www.gov.uk/lifetime-isa");
    expect(screen.getAllByText(/checked 2026-07-21/)).toHaveLength(2);
    expect(screen.getByText("Established")).toBeInTheDocument();
    expect(
      screen.getByText("Depends on your situation"),
    ).toBeInTheDocument();
  });

  it("renders a routing event as a refusal with adviser links", async () => {
    mockAsk(ROUTING);
    render(<App />);
    await askQuestion("Which ISA should I open?");
    await waitFor(() =>
      expect(
        screen.getByText(/needs an adviser/i),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByRole("link", { name: /FCA Register/ }),
    ).toBeInTheDocument();
  });

  it("renders an abstention honestly", async () => {
    mockAsk(ABSTAIN);
    render(<App />);
    await askQuestion("How do I renew my passport?");
    await waitFor(() =>
      expect(screen.getByText(/cannot verify/i)).toBeInTheDocument(),
    );
    expect(
      screen.getByText(/do not cover this well enough/i),
    ).toBeInTheDocument();
  });

  it("shows a recoverable error when the engine is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, status: 503 })));
    render(<App />);
    await askQuestion("What is an ISA?");
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/HTTP 503/),
    );
  });

  it("has no axe accessibility violations in idle and answer states", async () => {
    mockAsk(ANSWER);
    const { container } = render(<App />);
    expect(await axe(container)).toHaveNoViolations();
    await askQuestion("How does a Lifetime ISA work?");
    await waitFor(() =>
      expect(screen.getByRole("list")).toBeInTheDocument(),
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
