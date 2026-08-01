"""Core domain models.

The response union (AnswerCard | Abstention | RoutingEvent) is the product's
whole vocabulary: an answer earns its place claim-by-claim, and the two
non-answer shapes are first-class outcomes, not error states.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

DISCLAIMER = (
    "Pistis provides information and guidance, not regulated financial advice "
    "or a personal recommendation. It does not consider your individual "
    "circumstances. For advice tailored to you, speak to an FCA-authorised "
    "adviser."
)


class SourceOrg(str, Enum):
    GOVUK = "GOVUK"
    HMRC = "HMRC"
    FCA = "FCA"
    MONEYHELPER = "MoneyHelper"
    PENSIONWISE = "PensionWise"


Confidence = Literal["established", "depends", "uncertain"]


@dataclass(frozen=True)
class ManifestEntry:
    id: str
    domain: str
    title: str
    org: SourceOrg
    kind: Literal["govuk", "html"]
    locator: str
    why: str
    licence: str = "OGL v3.0"

    def __post_init__(self) -> None:
        if self.kind == "govuk" and not self.locator.startswith("/"):
            raise ValueError(
                f"{self.id}: govuk locator must be a content path starting with '/'"
            )
        if self.kind == "html" and not self.locator.startswith("https://"):
            raise ValueError(f"{self.id}: html locator must be an https URL")

    @property
    def url(self) -> str:
        return f"https://www.gov.uk{self.locator}" if self.kind == "govuk" else self.locator


@dataclass(frozen=True)
class Passage:
    id: str
    doc_id: str
    text: str
    doc_title: str
    org: SourceOrg
    url: str
    fetched_at: str  # ISO date the snapshot captured the source
    last_updated: str | None = None  # source-declared update date, if any
    # True when this chunk sits inside a worked example. Computed by the chunker,
    # not by the gate, because it is a property of the DOCUMENT REGION and the
    # gate only ever sees one chunk at a time: an example introduced in one chunk
    # runs its arithmetic into the next, which carries no marker of its own and
    # was therefore emitted as an established fact.
    in_example: bool = False


@dataclass(frozen=True)
class Citation:
    org: SourceOrg
    title: str
    url: str
    fetched_at: str
    last_updated: str | None = None

    @classmethod
    def from_passage(cls, p: Passage) -> Citation:
        return cls(
            org=p.org,
            title=p.doc_title,
            url=p.url,
            fetched_at=p.fetched_at,
            last_updated=p.last_updated,
        )


@dataclass(frozen=True)
class Claim:
    text: str
    citation: Citation
    confidence: Confidence


Verdict = Literal["grounded", "partial", "unsupported"]


@dataclass(frozen=True)
class ClaimVerdict:
    """Whether a claim's text is supported by the source passage it was drawn
    from, and where. The evidence behind the product's core promise."""

    verdict: Verdict
    score: float  # 0..1 grounding strength
    passage_id: str
    span: tuple[int, int] | None = None  # (start, end) char offsets in the source passage


@dataclass(frozen=True)
class TrustReport:
    """Per-answer faithfulness summary over its claims, in claim order."""

    verdicts: tuple[ClaimVerdict, ...]
    grounded: int
    total: int
    all_grounded: bool

    @classmethod
    def from_verdicts(
        cls, verdicts: tuple[ClaimVerdict, ...] | list[ClaimVerdict]
    ) -> TrustReport:
        vs = tuple(verdicts)
        grounded = sum(1 for v in vs if v.verdict == "grounded")
        total = len(vs)
        return cls(
            verdicts=vs,
            grounded=grounded,
            total=total,
            all_grounded=total > 0 and grounded == total,
        )


FreshnessVerdict = Literal["current", "aging", "stale"]

_FRESHNESS_ORDER = {"current": 0, "aging": 1, "stale": 2}


@dataclass(frozen=True)
class Freshness:
    """Whether a claim is still current: a claim that names a PAST UK tax year,
    or comes from an aged snapshot, is flagged rather than presented as fresh.
    Complements grounding — faithful to the source, but is the source current?"""

    verdict: FreshnessVerdict
    snapshot_age_days: int
    tax_year: str | None = None  # e.g. "2026-27" if the claim names one
    tax_year_current: bool | None = None  # is that tax year the current one?


@dataclass(frozen=True)
class FreshnessReport:
    """Per-answer freshness summary over its claims, in claim order."""

    per_claim: tuple[Freshness, ...]
    overall: FreshnessVerdict
    stale_count: int

    @classmethod
    def from_items(
        cls, items: tuple[Freshness, ...] | list[Freshness]
    ) -> FreshnessReport:
        items = tuple(items)
        overall: FreshnessVerdict = "current"
        for f in items:
            if _FRESHNESS_ORDER[f.verdict] > _FRESHNESS_ORDER[overall]:
                overall = f.verdict
        stale = sum(1 for f in items if f.verdict == "stale")
        return cls(per_claim=items, overall=overall, stale_count=stale)


@dataclass(frozen=True)
class RoutingLink:
    label: str
    url: str


@dataclass(frozen=True)
class Routing:
    message: str
    links: tuple[RoutingLink, ...]


@dataclass(frozen=True)
class AnswerCard:
    question: str
    claims: tuple[Claim, ...]
    disclaimer: str = DISCLAIMER
    kind: Literal["answer"] = "answer"
    trust_report: TrustReport | None = None
    freshness: FreshnessReport | None = None

    def __post_init__(self) -> None:
        # Structural invariant of the entire product: no uncited claims.
        if not self.claims:
            raise ValueError("AnswerCard requires at least one claim")
        for c in self.claims:
            if not c.citation.url or not c.citation.fetched_at:
                raise ValueError("every claim must carry a dated, linked citation")
        # Faithfulness invariant: an attached trust report must cover every
        # claim and show each grounded in its source. An ungrounded claim in a
        # shipped answer is a construction-time error (defence behind the gate).
        if self.trust_report is not None:
            if self.trust_report.total != len(self.claims):
                raise ValueError("trust_report must cover every claim")
            if not self.trust_report.all_grounded:
                raise ValueError(
                    "every claim in a shipped answer must be grounded in its cited source"
                )


AbstainStage = Literal[
    "no_source",
    "weak_coverage",
    # Sources matched the words strongly, but none of them is ABOUT the subject
    # raised — distinct from no_groundable_statement, where a source IS on topic
    # and merely has no quotable sentence. Conflating the two would give the user
    # a confidently wrong account of why Pistis declined.
    "off_topic",
    "no_groundable_statement",
    "empty_question",
]


@dataclass(frozen=True)
class SignalCheck:
    """One answerability signal measured against its threshold, so a refusal
    can show exactly which check fell short and by how much."""

    name: str
    value: float
    threshold: float
    passed: bool


@dataclass(frozen=True)
class AbstentionReport:
    """Why Pistis declined to answer — the refusal proving itself, symmetric
    with the TrustReport that proves an answer. Deterministic and keyless: the
    gate stage that fired, each answerability signal against its threshold, and
    the specific query terms no trusted source covers. 'Refusal is a feature'
    is only credible if the refusal can show its working."""

    stage: AbstainStage
    explanation: str
    signals: tuple[SignalCheck, ...] = ()
    uncovered_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class Abstention:
    question: str
    reason: str
    routing: Routing
    disclaimer: str = DISCLAIMER
    kind: Literal["abstain"] = "abstain"
    report: AbstentionReport | None = None


@dataclass(frozen=True)
class RoutingEvent:
    question: str
    reason: str
    routing: Routing
    matched: tuple[str, ...] = field(default=())
    disclaimer: str = DISCLAIMER
    kind: Literal["routing"] = "routing"


Response = AnswerCard | Abstention | RoutingEvent
