"""End-to-end: the three response states over the fixture corpus."""

from pistis.models import Abstention, AnswerCard, DISCLAIMER, RoutingEvent


def test_guidance_question_returns_answer_card(engine):
    response = engine.ask("How does a Lifetime ISA work?")
    assert isinstance(response, AnswerCard)
    assert response.claims
    assert response.disclaimer == DISCLAIMER
    for claim in response.claims:
        assert claim.citation.url
        assert claim.citation.fetched_at
        assert claim.confidence in {"established", "depends", "uncertain"}


def test_personal_rec_question_returns_routing_event(engine):
    response = engine.ask("Which ISA should I open?")
    assert isinstance(response, RoutingEvent)
    assert response.matched
    assert any("moneyhelper" in l.url for l in response.routing.links)
    assert any("register.fca.org.uk" in l.url for l in response.routing.links)


def test_personal_rec_wins_even_when_corpus_could_answer(engine):
    # The advice gate runs first: an answerable topic phrased as a personal
    # decision must still route, never answer.
    response = engine.ask("Should I open a Lifetime ISA?")
    assert isinstance(response, RoutingEvent)


def test_out_of_corpus_question_abstains_with_routing(engine):
    response = engine.ask("How do I renew my passport?")
    assert isinstance(response, Abstention)
    assert response.routing.links


def test_empty_question_abstains(engine):
    response = engine.ask("   ")
    assert isinstance(response, Abstention)


def test_abstention_response_is_explained(engine):
    response = engine.ask("How do I renew my passport?")
    assert isinstance(response, Abstention)
    assert response.report is not None
    assert response.report.stage in {"no_source", "weak_coverage"}
    assert "passport" in response.report.uncovered_terms


def test_empty_question_refusal_is_explained(engine):
    response = engine.ask("   ")
    assert isinstance(response, Abstention)
    assert response.report is not None
    assert response.report.stage == "empty_question"


def test_answer_carries_no_abstention_report(engine):
    # report is scoped to refusals (answers use trust_report instead). Asserting
    # the abstain side too ties this test to the feature: a revert breaks it.
    answer = engine.ask("How does a Lifetime ISA work?")
    abstain = engine.ask("How do I renew my passport?")
    assert isinstance(answer, AnswerCard)
    assert isinstance(abstain, Abstention)
    assert not hasattr(answer, "report")
    assert abstain.report is not None


def test_no_response_ever_lacks_disclaimer(engine):
    for q in [
        "How does a Lifetime ISA work?",
        "Which ISA should I open?",
        "How do I renew my passport?",
    ]:
        assert engine.ask(q).disclaimer == DISCLAIMER
