"""Faithfulness verification — the evidence behind 'every claim is grounded'.

Covers the verifier itself, the gate emission guard, the per-answer trust
report, and the strengthened AnswerCard invariant.
"""

import pytest

from finance_answer_engine.engine.faithfulness import verify
from finance_answer_engine.engine.gate import decide
from finance_answer_engine.models import (
    AnswerCard,
    Citation,
    Claim,
    ClaimVerdict,
    Passage,
    SourceOrg,
    TrustReport,
)


def _passage(text: str, pid: str = "d#0") -> Passage:
    return Passage(
        id=pid, doc_id="d", text=text, doc_title="T", org=SourceOrg.GOVUK,
        url="https://www.gov.uk/t", fetched_at="2026-07-21", last_updated="2026-04-06",
    )


# --- verify(): grounding a claim against its source passage ---

def test_verbatim_substring_is_grounded_with_exact_span():
    p = _passage("The annual ISA allowance is £20,000. It can be split across ISA types.")
    claim = "The annual ISA allowance is £20,000."
    v = verify(claim, p)
    assert v.verdict == "grounded"
    assert v.score == 1.0
    assert v.passage_id == "d#0"
    assert v.span is not None
    # the span must slice the source back to exactly the claim text
    assert p.text[v.span[0]:v.span[1]] == claim


def test_whitespace_and_case_insensitive_substring_is_grounded():
    p = _passage("The annual ISA   allowance\nis £20,000 each tax year.")
    v = verify("the annual isa allowance is £20,000", p)
    assert v.verdict == "grounded"
    assert v.score == 1.0
    assert v.span is not None


def test_paraphrase_within_source_vocabulary_is_grounded():
    p = _passage(
        "You pay a 25 percent government bonus on Lifetime ISA contributions each year."
    )
    v = verify("Lifetime ISA contributions earn a 25 percent government bonus", p)
    assert v.verdict == "grounded"
    assert v.score >= 0.85


def test_partial_overlap_is_partial():
    p = _passage("The annual ISA allowance is £20,000 for the current tax year.")
    # shares ISA/allowance/tax but introduces unsupported content
    v = verify("The ISA allowance for pension drawdown depends on your marginal tax band", p)
    assert v.verdict in ("partial", "unsupported")
    assert v.score < 0.85


def test_unrelated_claim_is_unsupported():
    p = _passage("The annual ISA allowance is £20,000 for the current tax year.")
    v = verify("You must renew your passport every ten years at the post office.", p)
    assert v.verdict == "unsupported"
    assert v.score < 0.5


def test_empty_claim_or_passage_is_unsupported():
    p = _passage("Some real content about pensions and tax relief.")
    assert verify("", p).verdict == "unsupported"
    assert verify("   ", p).verdict == "unsupported"
    assert verify("anything at all here", _passage("")).verdict == "unsupported"


# --- gate: emitted claims are all grounded; verdicts parallel the claims ---

def test_gate_emits_only_grounded_claims(index):
    decision = decide("How does a Lifetime ISA work?", index)
    assert decision.answerable
    assert len(decision.verdicts) == len(decision.claims)
    assert all(v.verdict == "grounded" for v in decision.verdicts)
    # claims are verbatim extracts, so grounding is exact
    assert all(v.score == 1.0 for v in decision.verdicts)


# --- engine: an answer carries an all-grounded trust report ---

def test_answer_carries_all_grounded_trust_report(engine):
    resp = engine.ask("What is the annual ISA allowance?")
    assert resp.kind == "answer"
    tr = resp.trust_report
    assert tr is not None
    assert tr.total == len(resp.claims)
    assert tr.grounded == tr.total
    assert tr.all_grounded is True


# --- TrustReport aggregation ---

def test_trust_report_from_verdicts_counts():
    tr = TrustReport.from_verdicts(
        [ClaimVerdict("grounded", 1.0, "a#0"), ClaimVerdict("grounded", 1.0, "b#1")]
    )
    assert (tr.grounded, tr.total, tr.all_grounded) == (2, 2, True)

    mixed = TrustReport.from_verdicts(
        [ClaimVerdict("grounded", 1.0, "a#0"), ClaimVerdict("partial", 0.6, "b#1")]
    )
    assert (mixed.grounded, mixed.total, mixed.all_grounded) == (1, 2, False)

    assert TrustReport.from_verdicts([]).all_grounded is False


# --- AnswerCard invariant: no ungrounded claim may ship ---

def _claim(text: str = "A grounded statement about ISAs and tax.") -> Claim:
    return Claim(
        text=text,
        citation=Citation(
            org=SourceOrg.GOVUK, title="T", url="https://www.gov.uk/t",
            fetched_at="2026-07-21", last_updated="2026-04-06",
        ),
        confidence="established",
    )


def test_answercard_accepts_all_grounded_trust_report():
    card = AnswerCard(
        question="q",
        claims=(_claim(),),
        trust_report=TrustReport.from_verdicts([ClaimVerdict("grounded", 1.0, "d#0")]),
    )
    assert card.trust_report.all_grounded


def test_answercard_rejects_ungrounded_claim():
    with pytest.raises(ValueError, match="grounded"):
        AnswerCard(
            question="q",
            claims=(_claim(),),
            trust_report=TrustReport.from_verdicts([ClaimVerdict("unsupported", 0.1, "d#0")]),
        )


def test_answercard_rejects_trust_report_not_covering_every_claim():
    with pytest.raises(ValueError, match="cover every claim"):
        AnswerCard(
            question="q",
            claims=(_claim("one"), _claim("two about tax")),
            trust_report=TrustReport.from_verdicts([ClaimVerdict("grounded", 1.0, "d#0")]),
        )


def test_answercard_without_trust_report_is_backward_compatible():
    card = AnswerCard(question="q", claims=(_claim(),))
    assert card.trust_report is None
