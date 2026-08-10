import { FormEvent, useEffect, useState } from "react";
import { ask } from "./api";
import { AnswerLedger } from "./components/AnswerLedger";
import { PrivacyNotice } from "./components/PrivacyNotice";
import { RefusalCard } from "./components/RefusalCard";
import type { AskResponse } from "./types";

const DISCLAIMER =
  "FinanceEngine provides information and guidance, not regulated financial advice " +
  "or a personal recommendation. It does not consider your individual " +
  "circumstances. For advice tailored to you, speak to an FCA-authorised adviser.";

type Status =
  | { state: "idle" }
  | { state: "loading" }
  | { state: "error"; message: string }
  | { state: "done"; response: AskResponse };

// Minimal hash-based routing — no router dependency needed for one extra
// page. "#/privacy" is a real, bookmarkable, back-button-friendly route
// (see PrivacyNotice.tsx), not a modal or hidden panel.
function useHashRoute(): string {
  const [hash, setHash] = useState(() => window.location.hash);
  useEffect(() => {
    const onHashChange = () => setHash(window.location.hash);
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);
  return hash;
}

export default function App() {
  const route = useHashRoute();
  const [question, setQuestion] = useState("");
  const [status, setStatus] = useState<Status>({ state: "idle" });

  useEffect(() => {
    document.title =
      route === "#/privacy"
        ? "Privacy notice — FinanceEngine"
        : "FinanceEngine — UK money questions, answered only when provable";
  }, [route]);

  if (route === "#/privacy") {
    return <PrivacyNotice />;
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || status.state === "loading") return;
    setStatus({ state: "loading" });
    try {
      setStatus({ state: "done", response: await ask(trimmed) });
    } catch (error) {
      setStatus({
        state: "error",
        message:
          error instanceof Error ? error.message : "Something went wrong.",
      });
    }
  }

  return (
    <main className="shell">
      <header className="masthead">
        <h1 className="wordmark">FinanceEngine</h1>
        <p className="register-line">
          UK money questions · answered only when provable · GOV.UK / HMRC /
          FCA sources
        </p>
      </header>

      <p className="disclaimer-banner">
        {status.state === "done" ? status.response.disclaimer : DISCLAIMER}{" "}
        <a className="privacy-link" href="#/privacy">
          How we handle your questions (privacy notice)
        </a>
      </p>

      <form className="ask-form" onSubmit={onSubmit}>
        <label htmlFor="question" className="sr-only" hidden>
          Your question
        </label>
        <input
          id="question"
          className="ask-input"
          type="text"
          placeholder="e.g. How does a Lifetime ISA work?"
          value={question}
          maxLength={500}
          onChange={(event) => setQuestion(event.target.value)}
          aria-label="Your question about UK personal finance"
        />
        <button
          className="ask-button"
          type="submit"
          aria-disabled={status.state === "loading" || !question.trim()}
        >
          {status.state === "loading" ? "Checking…" : "Ask"}
        </button>
      </form>

      <div aria-live="polite">
        {status.state === "loading" && (
          <div className="skeleton" role="status" aria-label="Checking sources">
            <div className="skeleton-row" />
            <div className="skeleton-row" />
            <div className="skeleton-row" />
          </div>
        )}
        {status.state === "error" && (
          <p className="error-note" role="alert">
            {status.message} Check the engine is running, then try again.
          </p>
        )}
        {status.state === "done" &&
          (status.response.kind === "answer" ? (
            <AnswerLedger card={status.response} />
          ) : (
            <RefusalCard response={status.response} />
          ))}
      </div>

      <footer className="site-footer">
        <p>
          Contains public sector information licensed under the{" "}
          <a
            className="footer-link"
            href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"
            target="_blank"
            rel="noopener noreferrer"
          >
            Open Government Licence v3.0
          </a>
          . Source material from GOV.UK, HMRC and the FCA remains the copyright
          of its respective publishers and is quoted with attribution.
        </p>
      </footer>
    </main>
  );
}
