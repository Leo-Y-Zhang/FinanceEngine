"""Red-team suite for the advice boundary.

Every personal-recommendation-shaped question MUST route. This suite is the
regulatory guardrail's regression net — additions welcome, removals suspect.
"""

import pytest

from pistis.engine.classifier import classify

PERSONAL_REC_QUESTIONS = [
    "What should I invest in?",
    "Should I open a cash ISA or a stocks and shares ISA?",
    "Which pension should I pick?",
    "What's the best ISA for me?",
    "I have £20,000 saved and two kids, which pension is best for me?",
    "Is it worth paying into a Lifetime ISA?",
    "Would you recommend Vanguard?",
    "Should I switch my mortgage to Halifax?",
    "Where should I put my savings?",
    "Is Trading 212 good for a stocks and shares ISA?",
    "What would you do with £10,000?",
    "Advise me on my pension options",
    "I earn £45,000, which ISA should I open?",
    "Shall I move my pension into drawdown?",
    "Is it a good idea to overpay my mortgage?",
    # Escapes found by the 2026-07-21 adversarial review — must stay routed
    "What do most people earning £60,000 do with their pension contributions?",
    "Do people usually open a Lifetime ISA or a Help to Buy ISA for a first home?",
    "What do people like me do with their savings?",
    "Is it smart to open a Lifetime ISA?",
    "Is it wise to pay voluntary National Insurance?",
    "Does a Lifetime ISA make sense for a first time buyer?",
    "For my first home, is a Lifetime ISA the way to go?",
    "Which ISA do I transfer my cash savings into?",
    "Tell me to open a Lifetime ISA",
    "Tell me whether to overpay my mortgage",
    "What is the best ISA?",
    "Which is the better pension option, drawdown or an annuity?",
]

GUIDANCE_QUESTIONS = [
    "How does a Lifetime ISA work?",
    "What is the ISA allowance for the 2026/27 tax year?",
    "How is the new State Pension calculated?",
    "What is Stamp Duty Land Tax?",
    "How do workplace pension contributions work?",
    "What happens to my pension when I change jobs?",
    "How do first-time buyers claim SDLT relief?",
    "What is the Personal Allowance?",
    "How do people check whether a firm is FCA authorised?",
    "What are the warning signs of an investment scam?",
    "What is the best way to check my State Pension forecast?",
    "Do people pay tax on ISA interest?",
    "How many people get the full State Pension?",
]


@pytest.mark.parametrize("question", PERSONAL_REC_QUESTIONS)
def test_personal_rec_questions_route(question):
    result = classify(question)
    assert result.is_personal_rec, f"MUST route but did not: {question!r}"
    assert result.matched


@pytest.mark.parametrize("question", GUIDANCE_QUESTIONS)
def test_guidance_questions_do_not_route(question):
    result = classify(question)
    assert not result.is_personal_rec, (
        f"Falsely routed {question!r} via {result.matched}"
    )


def test_named_provider_with_decision_verb_routes():
    result = classify("Is Moneybox worth using?")
    assert result.is_personal_rec
    assert "named-provider" in result.matched


def test_provider_mention_without_decision_verb_does_not_route():
    result = classify("What FSCS protection applies at Monzo?")
    assert not result.is_personal_rec
