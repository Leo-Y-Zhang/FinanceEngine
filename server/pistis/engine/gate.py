"""The default-deny grounding gate.

The posture is *not to answer*. An answer is earned when (a) retrieval is
strong enough on two independent signals — absolute BM25 score AND query-term
coverage — and (b) individual sentences can each be tied back to a passage.
Below threshold the engine abstains honestly. Thresholds are calibrated
against the fixture corpus by the calibration test-suite; calibration is
per-corpus and is the product's core execution risk (spec §5), so the numbers
live here in one visible place.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pistis.index.bm25 import Bm25Index, Hit, tokenize
from pistis.models import Citation, Claim, Confidence, Passage

# Answerability thresholds (both must pass).
MIN_TOP_SCORE = 2.0
MIN_COVERAGE = 0.45

# Per-sentence emission threshold: fraction of the sentence-relevant query
# terms a sentence must contain to be emitted as a claim.
MIN_SENTENCE_OVERLAP = 0.25
MAX_CLAIMS = 6

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9£])")

# Confidence-tier markers: sentences whose truth depends on the reader's
# circumstances are flagged, not resolved (spec: "depends-on-your-situation").
_DEPENDS = re.compile(
    r"\b(depends|if\s+you|when\s+you|may\s+be\s+able|might\s+be|eligib|"
    r"your\s+circumstances|in\s+some\s+cases|usually|can\s+vary|check\s+whether)\b",
    re.IGNORECASE,
)
_FACTUAL = re.compile(r"(£[\d,]+|\b\d{1,3}(,\d{3})*\b|\b\d+(\.\d+)?%|\b20\d{2}\b)")


@dataclass(frozen=True)
class GateDecision:
    answerable: bool
    reason: str
    claims: tuple[Claim, ...] = ()
    top_score: float = 0.0
    coverage: float = 0.0


def _confidence_for(sentence: str, passage: Passage) -> Confidence:
    if _DEPENDS.search(sentence):
        return "depends"
    if passage.last_updated is None and not _FACTUAL.search(sentence):
        # Undated source and no checkable figure: honest tier is "uncertain".
        return "uncertain"
    return "established"


def _sentence_claims(question: str, hits: list[Hit]) -> list[Claim]:
    q_terms = set(tokenize(question))
    candidates: list[tuple[float, str, str, Claim]] = []
    seen_texts: set[str] = set()
    for hit in hits:
        for sentence in _SENTENCE_END.split(hit.passage.text):
            sentence = sentence.strip()
            if len(sentence) < 20:
                continue
            s_terms = set(tokenize(sentence))
            if not q_terms:
                continue
            overlap = len(q_terms & s_terms) / len(q_terms)
            if overlap < MIN_SENTENCE_OVERLAP:
                continue
            normalized = " ".join(s_terms) or sentence.lower()
            if normalized in seen_texts:
                continue
            seen_texts.add(normalized)
            claim = Claim(
                text=sentence,
                citation=Citation.from_passage(hit.passage),
                confidence=_confidence_for(sentence, hit.passage),
            )
            candidates.append((overlap * (1 + hit.score / 10), sentence, hit.passage.id, claim))
    candidates.sort(key=lambda c: (-c[0], c[2], c[1]))
    return [c[3] for c in candidates[:MAX_CLAIMS]]


def decide(question: str, index: Bm25Index, k: int = 8) -> GateDecision:
    hits = index.search(question, k=k)
    if not hits:
        return GateDecision(
            answerable=False,
            reason="No source in the corpus addresses this question.",
        )
    top = hits[0].score
    cov = index.coverage(question, hits)
    if top < MIN_TOP_SCORE or cov < MIN_COVERAGE:
        return GateDecision(
            answerable=False,
            reason=(
                "The sources Pistis trusts do not cover this well enough to "
                "answer reliably."
            ),
            top_score=top,
            coverage=cov,
        )
    claims = _sentence_claims(question, hits)
    if not claims:
        return GateDecision(
            answerable=False,
            reason=(
                "Relevant sources were found, but no individual statement "
                "could be tied to the question confidently enough to cite."
            ),
            top_score=top,
            coverage=cov,
        )
    return GateDecision(
        answerable=True,
        reason="grounded",
        claims=tuple(claims),
        top_score=top,
        coverage=cov,
    )
