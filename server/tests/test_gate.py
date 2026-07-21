"""Calibration suite: the gate paradox, pinned by tests.

In-corpus questions must answer; out-of-corpus must abstain. If threshold
changes break these, the calibration — the product's core execution risk —
has drifted.
"""

import pytest

from pistis.engine.gate import _confidence_for, decide
from pistis.models import Passage, SourceOrg

ANSWERABLE = [
    "How does a Lifetime ISA work?",
    "What is the annual ISA allowance?",
    "How much is the full new State Pension per week?",
    "What is Stamp Duty Land Tax?",
    "How do workplace pension contributions work?",
    "What is the standard Personal Allowance?",
]

OUT_OF_CORPUS = [
    "How do I renew my passport?",
    "Who won the football world cup final?",
    "What is the weather forecast for Manchester?",
    "How do I install solar panels on a listed building?",
]


@pytest.mark.parametrize("question", ANSWERABLE)
def test_in_corpus_questions_answer(index, question):
    decision = decide(question, index)
    assert decision.answerable, (
        f"should answer {question!r}: reason={decision.reason} "
        f"top={decision.top_score:.2f} cov={decision.coverage:.2f}"
    )
    assert decision.claims


@pytest.mark.parametrize("question", OUT_OF_CORPUS)
def test_out_of_corpus_questions_abstain(index, question):
    decision = decide(question, index)
    assert not decision.answerable, (
        f"should abstain on {question!r} but answered with "
        f"top={decision.top_score:.2f} cov={decision.coverage:.2f}"
    )


def test_every_claim_is_cited_and_dated(index):
    decision = decide("How does a Lifetime ISA work?", index)
    for claim in decision.claims:
        assert claim.citation.url.startswith("https://")
        assert claim.citation.fetched_at
        assert claim.citation.title


def test_claims_deduplicated(index):
    decision = decide("What is the annual ISA allowance?", index)
    texts = [c.text for c in decision.claims]
    assert len(texts) == len(set(texts))


def make_passage(last_updated="2026-04-06"):
    return Passage(
        id="p#0", doc_id="p", text="t", doc_title="T", org=SourceOrg.GOVUK,
        url="https://www.gov.uk/t", fetched_at="2026-07-21",
        last_updated=last_updated,
    )


def test_confidence_depends_marker():
    s = "If you withdraw money for any other reason you pay a 25% charge."
    assert _confidence_for(s, make_passage()) == "depends"


def test_confidence_established_for_dated_figure():
    s = "The full rate of the new State Pension is £230.25 per week."
    assert _confidence_for(s, make_passage()) == "established"


def test_confidence_uncertain_for_undated_unfigured():
    s = "Investment scams are often sophisticated and difficult to spot."
    assert _confidence_for(s, make_passage(last_updated=None)) == "uncertain"
