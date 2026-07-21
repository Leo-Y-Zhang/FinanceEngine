import type { Abstention, RoutingEvent } from "../types";

export function RefusalCard({
  response,
}: {
  response: Abstention | RoutingEvent;
}) {
  const stamp =
    response.kind === "abstain"
      ? "Not answered — cannot verify"
      : "Not answered — needs an adviser";
  return (
    <section className="refusal-card result-enter" aria-label={stamp}>
      <p className="refusal-stamp">{stamp}</p>
      <h2 className="question-echo">{response.question}</h2>
      <p className="refusal-reason">{response.reason}</p>
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
