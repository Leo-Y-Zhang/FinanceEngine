import type { AnswerCard, Claim } from "../types";

const CONFIDENCE_LABEL: Record<Claim["confidence"], string> = {
  established: "Established",
  depends: "Depends on your situation",
  uncertain: "Uncertain",
};

const ORG_LABEL: Record<Claim["citation"]["org"], string> = {
  GOVUK: "GOV.UK",
  HMRC: "HMRC",
  FCA: "FCA",
  MoneyHelper: "MoneyHelper",
  PensionWise: "Pension Wise",
};

function Receipt({ claim }: { claim: Claim }) {
  const { citation } = claim;
  return (
    <p className="receipt">
      <span className="org-badge">{ORG_LABEL[citation.org]}</span>
      <a href={citation.url} target="_blank" rel="noopener noreferrer">
        {citation.title}
      </a>
      {citation.last_updated && <span>updated {citation.last_updated}</span>}
      <span>checked {citation.fetched_at}</span>
      <span
        className="confidence-chip"
        data-confidence={claim.confidence}
      >
        {CONFIDENCE_LABEL[claim.confidence]}
      </span>
    </p>
  );
}

export function AnswerLedger({ card }: { card: AnswerCard }) {
  return (
    <section className="result-enter" aria-label="Answer">
      <p className="result-kind">
        Answer · every statement below is cited to its source
      </p>
      <h2 className="question-echo">{card.question}</h2>
      <ul className="ledger">
        {card.claims.map((claim) => (
          <li
            className="ledger-row"
            data-confidence={claim.confidence}
            key={claim.text}
          >
            <p className="claim-text">{claim.text}</p>
            <Receipt claim={claim} />
          </li>
        ))}
      </ul>
    </section>
  );
}
