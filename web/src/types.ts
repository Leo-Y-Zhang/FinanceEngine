export type SourceOrg = "GOVUK" | "HMRC" | "FCA" | "MoneyHelper" | "PensionWise";

export type Confidence = "established" | "depends" | "uncertain";

export interface Citation {
  org: SourceOrg;
  title: string;
  url: string;
  fetched_at: string;
  last_updated: string | null;
}

export interface Claim {
  text: string;
  citation: Citation;
  confidence: Confidence;
}

export type Verdict = "grounded" | "partial" | "unsupported";

export interface ClaimVerdict {
  verdict: Verdict;
  score: number;
  passage_id: string;
  span: [number, number] | null;
}

export interface TrustReport {
  verdicts: ClaimVerdict[];
  grounded: number;
  total: number;
  all_grounded: boolean;
}

export type FreshnessVerdict = "current" | "aging" | "stale";

export interface Freshness {
  verdict: FreshnessVerdict;
  snapshot_age_days: number;
  tax_year: string | null;
  tax_year_current: boolean | null;
}

export interface FreshnessReport {
  per_claim: Freshness[];
  overall: FreshnessVerdict;
  stale_count: number;
}

export interface RoutingLink {
  label: string;
  url: string;
}

export interface Routing {
  message: string;
  links: RoutingLink[];
}

export interface AnswerCard {
  kind: "answer";
  question: string;
  claims: Claim[];
  disclaimer: string;
  trust_report?: TrustReport | null;
  freshness?: FreshnessReport | null;
}

export type AbstainStage =
  | "no_source"
  | "weak_coverage"
  // Sources matched the words but none of them is ABOUT the subject raised.
  // Kept distinct from no_groundable_statement, where a source IS on topic and
  // merely holds no quotable sentence — conflating the two would give the user
  // a confidently wrong account of why FinanceEngine declined.
  | "off_topic"
  | "no_groundable_statement"
  | "empty_question";

export interface SignalCheck {
  name: string;
  value: number;
  threshold: number;
  passed: boolean;
}

export interface AbstentionReport {
  stage: AbstainStage;
  explanation: string;
  signals: SignalCheck[];
  uncovered_terms: string[];
}

export interface Abstention {
  kind: "abstain";
  question: string;
  reason: string;
  routing: Routing;
  disclaimer: string;
  report?: AbstentionReport | null;
}

export interface RoutingEvent {
  kind: "routing";
  question: string;
  reason: string;
  routing: Routing;
  matched: string[];
  disclaimer: string;
}

export type AskResponse = AnswerCard | Abstention | RoutingEvent;
