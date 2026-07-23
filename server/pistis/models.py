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


@dataclass(frozen=True)
class Citation:
    org: SourceOrg
    title: str
    url: str
    fetched_at: str
    last_updated: str | None = None

    @classmethod
    def from_passage(cls, p: Passage) -> "Citation":
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
        cls, verdicts: "tuple[ClaimVerdict, ...] | list[ClaimVerdict]"
    ) -> "TrustReport":
        vs = tuple(verdicts)
        grounded = sum(1 for v in vs if v.verdict == "grounded")
        total = len(vs)
        return cls(
            verdicts=vs,
            grounded=grounded,
            total=total,
            all_grounded=total > 0 and grounded == total,
        )


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


@dataclass(frozen=True)
class Abstention:
    question: str
    reason: str
    routing: Routing
    disclaimer: str = DISCLAIMER
    kind: Literal["abstain"] = "abstain"


@dataclass(frozen=True)
class RoutingEvent:
    question: str
    reason: str
    routing: Routing
    matched: tuple[str, ...] = field(default=())
    disclaimer: str = DISCLAIMER
    kind: Literal["routing"] = "routing"


Response = AnswerCard | Abstention | RoutingEvent
