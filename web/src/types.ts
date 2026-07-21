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
}

export interface Abstention {
  kind: "abstain";
  question: string;
  reason: string;
  routing: Routing;
  disclaimer: string;
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
