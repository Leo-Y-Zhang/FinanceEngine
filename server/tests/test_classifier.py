"""Red-team suite for the advice boundary.

Every personal-recommendation-shaped question MUST route. This suite is the
regulatory guardrail's regression net — additions welcome, removals suspect.
"""

import pytest

from finance_answer_engine.engine.classifier import classify

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
    # Hardening pass 2 (2026-07-21) — five new paraphrase categories found by
    # adversarial review of docs/compliance-review-2026-07-21.md finding #1.
    # (1) Third-person / on-behalf-of framing — the "asking for a friend"
    # disguise. A suitability-shaped question about someone else's
    # circumstances is still suitability-shaped.
    "My friend wants to know if she should open a Lifetime ISA",
    "Asking for a friend, should she overpay her mortgage?",
    "My mum is wondering whether she should transfer her pension into drawdown",
    "A colleague of mine wants to know if he should pick a Lifetime ISA",
    "My brother earns £35,000, what should he do with his savings?",
    "Should my partner switch her mortgage to a fixed rate?",
    # (2) Hypothetical self-insertion — role-playing the composer into a
    # personalised recommendation without saying "should" or "recommend".
    "Were you in my shoes, would you open a Lifetime ISA or a SIPP?",
    "In my position, what would you invest in?",
    "What would you put your money into, a pension or an ISA?",
    # (3) Informal/slang decision framing — none of these contain "best/
    # right/should/smart/wise/sensible/worth", the words the pre-hardening
    # patterns looked for.
    "LISA or SIPP for retirement — no-brainer or nah?",
    "Is a SIPP a no-brainer for a higher earner like me?",
    "Overpaying my mortgage — good shout or not?",
    "Everyone says overpay your mortgage first — is that the move?",
    # (4) ESL/non-native-English-style polite-request phrasing.
    "Please suggest me an approach for my Lifetime ISA withdrawal",
    "Kindly advise on my pension options",
    "Guide me on my pension options",
    "What do you suggest for my pension contributions?",
    # Escape found by the answerability benchmark, 2026-07-27. The "worth-it"
    # pattern recognised only the PRONOUN subject, so "is it worth it for me"
    # routed while the identical ask about a NAMED PRODUCT was answered. Each of
    # these was checked against the pre-fix pattern set first: all five escaped,
    # and no other rule caught them.
    "Is a Lifetime ISA worth it for me?",
    "Is a Lifetime ISA worth it?",
    "Is the Help to Save bonus worth it for someone on my income?",
    "Are voluntary National Insurance contributions worth it?",
    "Overpaying my mortgage — is that worth it?",
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
    # Boundary probes added alongside the 2026-07-21 hardening-pass-2
    # patterns (third-party framing, hypothetical self-insertion) — these
    # are genuinely factual/guidance questions that share surface features
    # (a relative, "if you", "people") with the new positive patterns, and
    # must NOT be swept up by them.
    "My sister already gets Child Benefit — does that change how much I can claim?",
    "What would happen to my Help to Buy ISA bonus if I change jobs?",
    "Is it common for people to switch pension providers when they change jobs?",
    "If you already have a Lifetime ISA, can you also pay into a Help to Buy ISA in the same tax year?",
    # Boundary probes for the 2026-07-27 "worth it" widening. "Worth" without
    # "it" is a VALUATION question, not a suitability one, and must stay
    # answerable — this is the negative control that stops the new alternative
    # quietly swallowing a whole class of factual questions.
    "How much is my pension pot worth?",
    "What is my ISA worth after five years?",
    "How much is the new State Pension worth?",
    "What is the Help to Save bonus worth?",
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
