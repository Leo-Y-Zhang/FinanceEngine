import type { Abstention, AbstentionReport, RoutingEvent } from "../types";

function RefusalDiagnostics({ report }: { report: AbstentionReport }) {
  return (
    <div className="refusal-diagnostics">
      {report.uncovered_terms.length > 0 && (
        <div className="uncovered-block">
          <p className="uncovered-label">No trusted source covers</p>
          <ul
            className="uncovered-terms"
            aria-label="Concepts no trusted source covers"
          >
            {report.uncovered_terms.map((term) => (
              <li key={term} className="uncovered-chip">
                {term}
              </li>
            ))}
          </ul>
        </div>
      )}
      {report.signals.length > 0 && (
        <ul className="signal-meters" aria-label="How the answerability checks scored">
          {report.signals.map((signal) => (
            <li
              key={signal.name}
              className="signal-meter"
              data-passed={signal.passed}
            >
              <span className="signal-name">{signal.name}</span>
              <span className="signal-value">
                {signal.value} / {signal.threshold} needed{" "}
                {signal.passed ? "✓" : "✗"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function RefusalCard({
  response,
}: {
  response: Abstention | RoutingEvent;
}) {
  const stamp =
    response.kind === "abstain"
      ? "Not answered — cannot verify"
      : "Not answered — needs an adviser";
  // The refusal proves itself: when the engine attaches a report, its
  // explanation is the specific reason (which concepts it could not verify),
  // superseding the generic one-liner.
  const report = response.kind === "abstain" ? response.report : null;
  const reason = report?.explanation || response.reason;
  return (
    <section className="refusal-card result-enter" aria-label={stamp}>
      <p className="refusal-stamp">{stamp}</p>
      <h2 className="question-echo">{response.question}</h2>
      <p className="refusal-reason">{reason}</p>
      {report && <RefusalDiagnostics report={report} />}
      <p className="routing-message">{response.routing.message}</p>
      <ul className="routing-list">
        {response.routing.links.map((link) => (
          <li key={link.url}>
            <a href={link.url} target="_blank" rel="noopener noreferrer">
              {link.label}
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}
