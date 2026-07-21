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

    def __post_init__(self) -> None:
        # Structural invariant of the entire product: no uncited claims.
        if not self.claims:
            raise ValueError("AnswerCard requires at least one claim")
        for c in self.claims:
            if not c.citation.url or not c.citation.fetched_at:
                raise ValueError("every claim must carry a dated, linked citation")


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
