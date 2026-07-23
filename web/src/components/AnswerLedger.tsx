import type { AnswerCard, Claim, ClaimVerdict, Freshness } from "../types";

function freshnessLabel(f: Freshness): string {
  if (f.tax_year && f.tax_year_current === false) {
    return `${f.tax_year} tax year — check current figure`;
  }
  return "Source may be dated";
}

const CONFIDENCE_LABEL: Record<Claim["confidence"], string> = {
  established: "Established",
  depends: "Depends on your situation",
  uncertain: "Uncertain",
};

const VERDICT_LABEL: Record<ClaimVerdict["verdict"], string> = {
  grounded: "Grounded in source",
  partial: "Partial support",
  unsupported: "Unsupported",
};

const ORG_LABEL: Record<Claim["citation"]["org"], string> = {
  GOVUK: "GOV.UK",
  HMRC: "HMRC",
  FCA: "FCA",
  MoneyHelper: "MoneyHelper",
  PensionWise: "Pension Wise",
};

function Receipt({
  claim,
  verdict,
  freshness,
}: {
  claim: Claim;
  verdict?: ClaimVerdict;
  freshness?: Freshness;
}) {
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
      {verdict && (
        <span
          className="grounding-chip"
          data-verdict={verdict.verdict}
          title={`Faithfulness ${Math.round(verdict.score * 100)}% against source passage ${verdict.passage_id}`}
        >
          {VERDICT_LABEL[verdict.verdict]}
        </span>
      )}
      {freshness && freshness.verdict !== "current" && (
        <span className="freshness-chip" data-freshness={freshness.verdict}>
          {freshnessLabel(freshness)}
        </span>
      )}
    </p>
  );
}

export function AnswerLedger({ card }: { card: AnswerCard }) {
  const report = card.trust_report;
  const fresh = card.freshness;
  return (
    <section className="result-enter" aria-label="Answer">
      <p className="result-kind">
        Answer · every statement below is cited to its source
      </p>
      <h2 className="question-echo">{card.question}</h2>
      {report && (
        <p className="trust-summary" data-all-grounded={report.all_grounded}>
          {report.grounded} of {report.total}{" "}
          {report.total === 1 ? "statement" : "statements"} grounded in their
          cited source
        </p>
      )}
      {fresh && fresh.overall === "stale" && (
        <p className="freshness-caveat" role="note">
          Some statements reference a past tax year or an aged source — check the
          current figure before relying on it.
        </p>
      )}
      <ul className="ledger">
        {card.claims.map((claim, i) => (
          <li
            className="ledger-row"
            data-confidence={claim.confidence}
            key={claim.text}
          >
            <p className="claim-text">{claim.text}</p>
            <Receipt
              claim={claim}
              verdict={report?.verdicts[i]}
              freshness={fresh?.per_claim[i]}
            />
          </li>
        ))}
      </ul>
    </section>
  );
}
