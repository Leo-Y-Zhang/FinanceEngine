"""Deterministic, keyless per-claim faithfulness verification.

Pistis emits each claim as a verbatim sentence extracted from one source
passage. This module *proves* that grounding: it checks a claim's text against
the passage it was drawn from and returns a verdict with the exact matched
span. It serves three roles:

  1. an emission guard in the grounding gate — a sentence that is not grounded
     in its passage is never shipped as a claim;
  2. the evidence surfaced in an answer's trust report (the exact backing span
     the UI can highlight);
  3. the metric the honesty-eval reports.

It also future-proofs the optional LLM composer (README): any composed answer
must ground in the same sources to pass.

Pure functions only — no network, no model, fully reproducible. The token model
is shared with retrieval (``bm25.tokenize``) so the paraphrase fallback speaks
the same vocabulary as the gate.
"""

from __future__ import annotations

import re

from pistis.index.bm25 import tokenize
from pistis.models import ClaimVerdict, Passage

# A claim is grounded-by-paraphrase when at least this fraction of its content
# tokens also appear in the source passage.
GROUNDED_TOKEN_FRACTION = 0.85
# At/above this (but below GROUNDED) is partial support — real overlap, not
# enough to ship. Below it is unsupported.
PARTIAL_TOKEN_FRACTION = 0.5

_WS = re.compile(r"\s+")


def verify(claim_text: str, passage: Passage) -> ClaimVerdict:
    """Ground ``claim_text`` against ``passage.text``.

    Fast path: a contiguous (whitespace- and case-insensitive) substring match
    is fully grounded, and its char span within the ORIGINAL passage text is
    reported so callers can highlight the exact backing sentence. Fallback:
    shared-token fraction using the retrieval tokenizer.
    """
    claim = claim_text.strip()
    if not claim or not passage.text.strip():
        return ClaimVerdict(verdict="unsupported", score=0.0, passage_id=passage.id, span=None)

    span = _substring_span(claim, passage.text)
    if span is not None:
        return ClaimVerdict(verdict="grounded", score=1.0, passage_id=passage.id, span=span)

    claim_tokens = tokenize(claim)
    if not claim_tokens:
        return ClaimVerdict(verdict="unsupported", score=0.0, passage_id=passage.id, span=None)
    source_tokens = set(tokenize(passage.text))
    covered = sum(1 for t in claim_tokens if t in source_tokens)
    score = covered / len(claim_tokens)
    if score >= GROUNDED_TOKEN_FRACTION:
        verdict = "grounded"
    elif score >= PARTIAL_TOKEN_FRACTION:
        verdict = "partial"
    else:
        verdict = "unsupported"
    return ClaimVerdict(
        verdict=verdict, score=round(score, 4), passage_id=passage.id, span=None
    )


def _substring_span(claim: str, source: str) -> tuple[int, int] | None:
    """(start, end) char offsets of ``claim`` within ``source``, or None.

    Tries an exact match first (gate claims are verbatim extracts, so this is
    the common path and yields precise offsets), then a whitespace- and
    case-insensitive match whose offsets are mapped back onto the original
    ``source`` string.
    """
    idx = source.find(claim)
    if idx != -1:
        return (idx, idx + len(claim))

    # Whitespace/case-insensitive fallback: normalise runs of whitespace to a
    # single space and lowercase, keeping a map from each normalised char back
    # to its offset in the original source.
    norm_chars: list[str] = []
    offsets: list[int] = []
    prev_ws = False
    for i, ch in enumerate(source):
        if ch.isspace():
            if prev_ws:
                continue
            norm_chars.append(" ")
            offsets.append(i)
            prev_ws = True
        else:
            norm_chars.append(ch.lower())
            offsets.append(i)
            prev_ws = False
    norm_source = "".join(norm_chars)
    needle = _WS.sub(" ", claim).lower()
    pos = norm_source.find(needle)
    if pos == -1:
        return None
    start = offsets[pos]
    end = offsets[pos + len(needle) - 1] + 1
    return (start, end)
