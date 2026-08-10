"""Calibration suite: the gate paradox, pinned by tests.

In-corpus questions must answer; out-of-corpus must abstain. If threshold
changes break these, the calibration — the product's core execution risk —
has drifted.
"""

import pytest

from finance_engine.engine.gate import _confidence_for, _phrase_terms, _signal_pair, decide
from finance_engine.models import AbstentionReport, Passage, SourceOrg

ANSWERABLE = [
    "How does a Lifetime ISA work?",
    "How does a LISA bonus work?",
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


def test_answerable_decision_carries_no_report(index):
    decision = decide("What is the annual ISA allowance?", index)
    assert decision.answerable
    assert decision.report is None


def test_no_source_refusal_names_uncovered_terms(index):
    decision = decide("How do I renew my passport?", index)
    assert not decision.answerable
    report = decision.report
    assert isinstance(report, AbstentionReport)
    assert report.stage == "no_source"
    assert "passport" in report.uncovered_terms
    assert report.explanation.strip()


def test_weak_coverage_refusal_shows_signal_meters(index):
    # In-domain retrieval fires but coverage is too thin: both answerability
    # signals must be shown, with the coverage signal failing.
    decision = decide("What is the weather forecast for Manchester?", index)
    assert not decision.answerable
    report = decision.report
    assert report.stage == "weak_coverage"
    assert {s.name for s in report.signals} == {"retrieval strength", "source coverage"}
    by_name = {s.name: s for s in report.signals}
    assert by_name["source coverage"].passed is False
    assert by_name["source coverage"].threshold == 0.6
    assert "weather" in report.uncovered_terms


def test_every_out_of_corpus_refusal_is_explained(index):
    for question in [
        "How do I renew my passport?",
        "Who won the football world cup final?",
        "What is the weather forecast for Manchester?",
        "How do I install solar panels on a listed building?",
    ]:
        report = decide(question, index).report
        assert report is not None, question
        assert report.explanation.strip(), question


def test_no_groundable_statement_stage_when_matched_but_uncitable(passages):
    # The third refusal stage: retrieval is strong and coverage is full (both
    # answerability signals pass), yet every sentence sits below the per-sentence
    # overlap bar, so nothing is citable. Also the only path that exercises the
    # both-signals-passed rendering.
    from finance_engine.index.bm25 import Bm25Index

    terms = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel"]
    text = " ".join(f"The {t} paragraph explains one separate idea here." for t in terms)
    spread = Passage(
        id="spread#0", doc_id="spread", text=text, doc_title="Spread",
        org=SourceOrg.GOVUK, url="https://www.gov.uk/spread",
        fetched_at="2026-07-21", last_updated="2026-04-06",
    )
    index = Bm25Index([*list(passages), spread])
    decision = decide(" ".join(terms), index)
    assert not decision.answerable
    report = decision.report
    assert report.stage == "no_groundable_statement"
    assert report.explanation.strip()
    assert len(report.signals) == 2
    assert all(s.passed for s in report.signals)  # both_pass=True path


def test_signal_meter_never_contradicts_its_pass_flag():
    # A displayed value must never sit at/above its threshold while marked
    # failed — round() alone could nudge 0.599 up to 0.60. The meters exist to
    # make a refusal credible, so they must be internally consistent.
    for top, cov in [(1.999, 0.599), (2.5, 0.33), (2.0, 0.6), (0.0, 0.0)]:
        for signal in _signal_pair(top, cov):
            assert (signal.value >= signal.threshold) == signal.passed, (
                signal.name, signal.value, signal.threshold, signal.passed,
            )


def test_signal_meter_both_pass_marks_all_passed():
    for signal in _signal_pair(2.5, 0.9, both_pass=True):
        assert signal.passed
        assert signal.value >= signal.threshold


def test_phrase_terms_caps_list_and_counts_overflow():
    terms = ("building", "install", "listed", "panels", "solar")
    assert _phrase_terms(terms) == "'building', 'install', 'listed', 'panels', and 1 more"


def test_phrase_terms_no_tail_within_limit():
    assert _phrase_terms(("passport", "renew")) == "'passport', 'renew'"


def test_no_source_refusal_summarises_overflow_terms(index):
    report = decide("How do I install solar panels on a listed building?", index).report
    assert report.stage == "no_source"
    assert report.explanation.endswith("and 1 more.")


def test_confidence_depends_marker():
    s = "If you withdraw money for any other reason you pay a 25% charge."
    assert _confidence_for(s, make_passage()) == "depends"


def test_confidence_established_for_dated_figure():
    s = "The full rate of the new State Pension is £230.25 per week."
    assert _confidence_for(s, make_passage()) == "established"


def test_confidence_uncertain_for_undated_unfigured():
    s = "Investment scams are often sophisticated and difficult to spot."
    assert _confidence_for(s, make_passage(last_updated=None)) == "uncertain"


def test_worked_example_claims_capped_and_not_boosted(passages):
    # A GOV.UK-style worked example must not be emitted as 'established'
    # fact, and its arithmetic must not win the figure boost over a real rule.
    from finance_engine.corpus.store import Document, passages_for
    from finance_engine.index.bm25 import Bm25Index

    rule = Document(
        doc_id="rule", title="Tax on savings interest", org=SourceOrg.HMRC,
        url="https://www.gov.uk/rule", fetched_at="2026-07-21",
        last_updated="2026-04-06",
        text="Your personal savings allowance for interest is £1,000 for basic rate taxpayers. "
             "Savings interest above the personal savings allowance is taxed at your usual rate. "
             "The personal savings allowance applies to interest from banks and building societies.",
    )
    example = Document(
        doc_id="ex", title="Tax on savings interest", org=SourceOrg.HMRC,
        url="https://www.gov.uk/ex", fetched_at="2026-07-21",
        last_updated="2026-04-06",
        text="Example. You earn £20,000 of wages and get £1,500 of savings interest over your personal savings allowance. "
             "You would pay tax on £500 of savings interest in this example. "
             "Your total taxable savings interest would be £500.",
    )
    index = Bm25Index(list(passages) + passages_for(rule) + passages_for(example))
    decision = decide("What is the personal savings allowance for interest?", index)
    assert decision.answerable
    example_claims = [c for c in decision.claims if c.citation.url.endswith("/ex")]
    assert example_claims, "example sentences can still be cited"
    assert all(c.confidence == "uncertain" for c in example_claims)
    # the un-boosted example must not outrank the real rule
    assert decision.claims[0].citation.url.endswith("/rule")


def test_worked_example_detected_in_the_phrasings_govuk_actually_uses():
    """The marker only caught a capitalised "Example" opening a passage.

    Measured against realistic phrasings it missed six of ten, including the
    commonest of all - "For example, if you earn ...". Those sentences carry
    currency figures, so they were not merely emitted as 'established' but also
    won the factual boost and rose up the ledger: invented arithmetic shown to
    the reader as settled fact.
    """
    from finance_engine.engine.gate import _EXAMPLE_MARK

    introduces_an_example = [
        "Example. Bill earns £50,000.",
        "Example 1. Bill earns £50,000.",
        "Example: Bill earns £50,000.",
        "For example, if you earn £50,000 you pay £7,486.",
        "Worked example. Bill earns £50,000.",
        "Worked example: Bill earns £50,000.",
        "example. Bill earns £50,000.",
        "Here is an example. Bill earns £50,000.",
        "Examples. Bill earns £50,000.",
        "## Example",
        "* Example: a basic rate taxpayer.",
        "You pay tax on some income, e.g. £50,000 of salary.",
        "Consider the following examples: Bill earns £50,000.",
    ]
    states_a_rule = [
        "The ISA allowance for 2026 to 2027 is £20,000.",
        "You can save up to £20,000 each tax year.",
        "Higher rate tax applies above £50,270.",
        "Capital gains tax is charged at 20% on most assets.",
        # prose that merely mentions the word must not downgrade a real rule
        "This rule has one example in Annex B of the guidance.",
    ]

    for text in introduces_an_example:
        assert _EXAMPLE_MARK.search(text), f"should be marked illustrative: {text!r}"
    for text in states_a_rule:
        assert not _EXAMPLE_MARK.search(text), f"should stay a rule: {text!r}"


def test_for_example_arithmetic_is_not_emitted_as_established(passages):
    """The same guarantee as the test above, through the whole engine.

    Identical to test_worked_example_claims_capped_and_not_boosted except that
    the example is introduced the way GOV.UK usually introduces one. Before the
    marker was widened this passage produced 'established' claims carrying
    hypothetical figures.
    """
    from finance_engine.corpus.store import Document, passages_for
    from finance_engine.index.bm25 import Bm25Index

    rule = Document(
        doc_id="rule", title="Tax on savings interest", org=SourceOrg.HMRC,
        url="https://www.gov.uk/rule", fetched_at="2026-07-21",
        last_updated="2026-04-06",
        text="Your personal savings allowance for interest is £1,000 for basic rate taxpayers. "
             "Savings interest above the personal savings allowance is taxed at your usual rate. "
             "The personal savings allowance applies to interest from banks and building societies.",
    )
    example = Document(
        doc_id="ex", title="Tax on savings interest", org=SourceOrg.HMRC,
        url="https://www.gov.uk/ex", fetched_at="2026-07-21",
        last_updated="2026-04-06",
        text="For example, you earn £20,000 of wages and get £1,500 of savings interest "
             "over your personal savings allowance. "
             "You would pay tax on £500 of savings interest. "
             "Your total taxable savings interest would be £500.",
    )
    index = Bm25Index(list(passages) + passages_for(rule) + passages_for(example))
    decision = decide("What is the personal savings allowance for interest?", index)
    assert decision.answerable
    example_claims = [c for c in decision.claims if c.citation.url.endswith("/ex")]
    assert example_claims, "example sentences can still be cited"
    assert all(c.confidence == "uncertain" for c in example_claims)
    assert decision.claims[0].citation.url.endswith("/rule")


def _passage(doc_id, idx, title, text):
    return Passage(
        id=f"{doc_id}#{idx}",
        doc_id=doc_id,
        text=text,
        doc_title=title,
        org=SourceOrg.GOVUK,
        url="https://www.gov.uk/inheritance-tax",
        fetched_at="2026-07-27",
        last_updated="2026-07-01",
    )


def test_off_topic_sources_are_refused_and_told_apart_from_uncitable_ones():
    """The relevance guard: matching the words is not addressing the subject.

    This is the crypto failure in miniature. A document about Inheritance Tax
    mentions cryptocurrency once, in a list of chargeable assets. Retrieval and
    coverage are both satisfied — the words really are there — and any sentence
    drawn from it is perfectly grounded in its own passage. It still does not
    answer how cryptocurrency is taxed.
    """
    from finance_engine.index.bm25 import Bm25Index

    passages = [
        _passage("iht", 0, "Inheritance Tax",
                 "Chargeable assets are taxed and include property, shares and cryptocurrency."),
        _passage("iht", 1, "Inheritance Tax",
                 "Gifts given 3 to 7 years before death are taxed on a sliding scale."),
        _passage("iht", 2, "Inheritance Tax",
                 "The Inheritance Tax threshold is reviewed each tax year by HMRC."),
        _passage("iht", 3, "Inheritance Tax",
                 "Taper relief reduces the amount of Inheritance Tax due on a gift."),
    ]
    decision = decide("How is cryptocurrency taxed?", Bm25Index(passages))

    assert not decision.answerable
    assert decision.report is not None
    assert decision.report.stage == "off_topic"
    # The explanation must say why, not borrow another stage's account of itself.
    assert "about" in decision.report.explanation.lower()
    assert decision.claims == ()


def test_the_relevance_guard_cannot_turn_a_refusal_into_an_answer():
    """Safety property: it only ever removes material.

    Anything the gate would previously have refused it must still refuse, so the
    guard can never widen what FinanceEngine is willing to say.
    """
    from finance_engine.index.bm25 import Bm25Index

    index = Bm25Index([
        _passage("d", 0, "Some guide", "This document is about something else entirely."),
        _passage("d", 1, "Some guide", "It has nothing to do with the question asked."),
    ])
    for question in OUT_OF_CORPUS:
        assert not decide(question, index).answerable
