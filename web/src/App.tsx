import { FormEvent, useState } from "react";
import { ask } from "./api";
import { AnswerLedger } from "./components/AnswerLedger";
import { RefusalCard } from "./components/RefusalCard";
import type { AskResponse } from "./types";

const DISCLAIMER =
  "Pistis provides information and guidance, not regulated financial advice " +
  "or a personal recommendation. It does not consider your individual " +
  "circumstances. For advice tailored to you, speak to an FCA-authorised adviser.";

type Status =
  | { state: "idle" }
  | { state: "loading" }
  | { state: "error"; message: string }
  | { state: "done"; response: AskResponse };

export default function App() {
  const [question, setQuestion] = useState("");
  const [status, setStatus] = useState<Status>({ state: "idle" });

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
        <h1 className="wordmark">Pistis</h1>
        <p className="register-line">
          UK money questions · answered only when provable · GOV.UK / HMRC /
          FCA sources
        </p>
      </header>

      <p className="disclaimer-banner">
        {status.state === "done" ? status.response.disclaimer : DISCLAIMER}
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
    </main>
  );
}
