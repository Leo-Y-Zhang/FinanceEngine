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

from pistis.engine.faithfulness import verify
from pistis.index.bm25 import Bm25Index, Hit, tokenize
from pistis.models import (
    AbstentionReport,
    Citation,
    Claim,
    ClaimVerdict,
    Confidence,
    Passage,
    SignalCheck,
)

# Answerability thresholds (both must pass).
MIN_TOP_SCORE = 2.0
MIN_COVERAGE = 0.6

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

# GOV.UK worked examples appear as an "Example." heading followed by
# hypothetical arithmetic. Those figures are illustrative, not rules — they
# must not be emitted as 'established' facts nor win the factual boost.
_EXAMPLE_MARK = re.compile(r"(?:^|\.\s)Example[\s.:]")


@dataclass(frozen=True)
class GateDecision:
    answerable: bool
    reason: str
    claims: tuple[Claim, ...] = ()
    verdicts: tuple[ClaimVerdict, ...] = ()
    top_score: float = 0.0
    coverage: float = 0.0
    # Present only on a refusal: the explainable-refusal diagnostic.
    report: AbstentionReport | None = None


def _phrase_terms(terms: tuple[str, ...], limit: int = 4) -> str:
    """Human-readable list of uncovered terms, capped so a long query does not
    produce an unreadable wall of words."""
    shown = list(terms[:limit])
    extra = len(terms) - len(shown)
    joined = ", ".join(f"'{t}'" for t in shown)
    if extra > 0:
        joined += f", and {extra} more"
    return joined


def _signal(name: str, raw: float, threshold: float, forced_pass: bool) -> SignalCheck:
    """One signal for display. The pass/fail decision uses the raw score (the
    gate's own semantics); the shown value is kept from contradicting that glyph
    — round() alone can nudge a sub-threshold score up to its bar (0.599 -> 0.60,
    displayed as "0.6 / 0.6 needed" yet marked failed), which is exactly the kind
    of self-contradiction this whole feature exists to avoid."""
    passed = forced_pass or raw >= threshold
    value = round(raw, 2)
    if passed and value < threshold:
        value = threshold
    elif not passed and value >= threshold:
        value = round(threshold - 0.01, 2)
    return SignalCheck(name=name, value=value, threshold=threshold, passed=passed)


def _signal_pair(top: float, cov: float, both_pass: bool = False) -> tuple[SignalCheck, ...]:
    return (
        _signal("retrieval strength", top, MIN_TOP_SCORE, both_pass),
        _signal("source coverage", cov, MIN_COVERAGE, both_pass),
    )


def _confidence_for(sentence: str, passage: Passage) -> Confidence:
    if _DEPENDS.search(sentence):
        return "depends"
    if passage.last_updated is None and not _FACTUAL.search(sentence):
        # Undated source and no checkable figure: honest tier is "uncertain".
        return "uncertain"
    return "established"


def _sentence_claims(question: str, hits: list[Hit]) -> list[tuple[Claim, ClaimVerdict]]:
    q_terms = set(tokenize(question))
    candidates: list[tuple[float, str, str, Claim, ClaimVerdict]] = []
    seen_texts: set[str] = set()
    for hit in hits:
        in_example = bool(_EXAMPLE_MARK.search(hit.passage.text))
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
            normalized = " ".join(sorted(s_terms)) or sentence.lower()
            if normalized in seen_texts:
                continue
            seen_texts.add(normalized)
            # Faithfulness guard: a sentence must be grounded in the passage it
            # is drawn from, or it is never emitted as a claim (same posture as
            # the overlap threshold above). This also guards a future composer.
            verdict = verify(sentence, hit.passage)
            if verdict.verdict != "grounded":
                continue
            claim = Claim(
                text=sentence,
                citation=Citation.from_passage(hit.passage),
                confidence="uncertain" if in_example else _confidence_for(sentence, hit.passage),
            )
            # Sentences carrying checkable figures (£, %, years) are the ones
            # users came to verify — nudge them up the ledger. Never boost
            # worked-example arithmetic.
            boost = 1.15 if _FACTUAL.search(sentence) and not in_example else 1.0
            rank = overlap * (1 + hit.score / 10) * boost
            candidates.append((rank, sentence, hit.passage.id, claim, verdict))
    candidates.sort(key=lambda c: (-c[0], c[2], c[1]))
    return [(c[3], c[4]) for c in candidates[:MAX_CLAIMS]]


def decide(question: str, index: Bm25Index, k: int = 8) -> GateDecision:
    hits = index.search(question, k=k)
    if not hits:
        uncovered = tuple(index.uncovered_terms(question, []))
        explanation = (
            f"No trusted source in Pistis's corpus covers {_phrase_terms(uncovered)}."
            if uncovered
            else "No trusted source in Pistis's corpus addresses this question."
        )
        return GateDecision(
            answerable=False,
            reason="No source in the corpus addresses this question.",
            report=AbstentionReport(
                stage="no_source",
                explanation=explanation,
                uncovered_terms=uncovered,
            ),
        )
    top = hits[0].score
    cov = index.coverage(question, hits)
    if top < MIN_TOP_SCORE or cov < MIN_COVERAGE:
        uncovered = tuple(index.uncovered_terms(question, hits))
        explanation = (
            f"Pistis found related material but no trusted source covers "
            f"{_phrase_terms(uncovered)} — the part it could not verify."
            if uncovered
            else (
                "Trusted sources mention your question, but not strongly or "
                "completely enough in one place to answer without guessing."
            )
        )
        return GateDecision(
            answerable=False,
            reason=(
                "The sources Pistis trusts do not cover this well enough to "
                "answer reliably."
            ),
            top_score=top,
            coverage=cov,
            report=AbstentionReport(
                stage="weak_coverage",
                explanation=explanation,
                signals=_signal_pair(top, cov),
                uncovered_terms=uncovered,
            ),
        )
    pairs = _sentence_claims(question, hits)
    if not pairs:
        return GateDecision(
            answerable=False,
            reason=(
                "Relevant sources were found, but no individual statement "
                "could be tied to the question confidently enough to cite."
            ),
            top_score=top,
            coverage=cov,
            report=AbstentionReport(
                stage="no_groundable_statement",
                explanation=(
                    "Relevant sources were found and matched your question well, "
                    "but no single statement in them could be tied to your "
                    "question confidently enough to quote and cite."
                ),
                signals=_signal_pair(top, cov, both_pass=True),
            ),
        )
    return GateDecision(
        answerable=True,
        reason="grounded",
        claims=tuple(c for c, _ in pairs),
        verdicts=tuple(v for _, v in pairs),
        top_score=top,
        coverage=cov,
    )
