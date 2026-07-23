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
  disclaimer: "SERVER DISCLAIMER SENTINEL — guidance, not advice.",
  trust_report: {
    verdicts: [
      { verdict: "grounded", score: 1.0, passage_id: "lifetime-isa#3", span: [0, 52] },
      { verdict: "grounded", score: 1.0, passage_id: "lifetime-isa#5", span: null },
    ],
    grounded: 2,
    total: 2,
    all_grounded: true,
  },
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
  window.location.hash = "";
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
    // the API's disclaimer is the source of truth once a response arrives
    expect(
      screen.getByText(/SERVER DISCLAIMER SENTINEL/),
    ).toBeInTheDocument();
  });

  it("surfaces the trust report and per-claim grounding verdicts", async () => {
    mockAsk(ANSWER);
    render(<App />);
    await askQuestion("How does a Lifetime ISA work?");
    await waitFor(() => expect(screen.getByRole("list")).toBeInTheDocument());
    expect(
      screen.getByText(/2 of 2 statements grounded in their cited source/i),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Grounded in source")).toHaveLength(2);
  });

  it("announces the loading state and stays axe-clean while checking", async () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));
    const { container } = render(<App />);
    await askQuestion("What is an ISA?");
    expect(
      screen.getByRole("status", { name: /checking sources/i }),
    ).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
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

  it("links to a reachable privacy notice from the disclaimer banner", () => {
    render(<App />);
    const link = screen.getByRole("link", {
      name: /privacy notice/i,
    });
    expect(link).toHaveAttribute("href", "#/privacy");
  });

  it("navigates to the privacy notice page and back via the hash route", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("link", { name: /privacy notice/i }));
    expect(
      screen.getByRole("heading", { name: /privacy notice/i }),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/30 days/).length).toBeGreaterThan(0);
    // no longer showing the ask form while on the privacy page
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: /back to pistis/i }));
    expect(screen.getByRole("textbox")).toBeInTheDocument();
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
