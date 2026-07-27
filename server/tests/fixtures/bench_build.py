"""Author the Pistis answerability benchmark (`bench.json`).

Run:  python tests/fixtures/bench_build.py

WHY THIS IS A SCRIPT, NOT A HAND-EDITED JSON FILE: every label carries
provenance, and the provenance is what makes the benchmark non-circular. Keeping
the authoring in code keeps the protocol visible next to the data.

LABELLING PROTOCOL — the point of the whole exercise
====================================================
A benchmark whose labels come from the system under test measures nothing. So no
label here is derived from Pistis's output. Each is derived from the CORPUS or
from the QUESTION'S FORM, and each is falsifiable:

  expect="answer"   The corpus genuinely covers this. The label names the
                    ``supported_by`` document and a ``probe`` term that document
                    must actually contain. ``python -m pistis.bench --validate``
                    asserts both, so a wrong label fails loudly instead of
                    quietly scoring the engine against a fiction.

  expect="abstain"  The corpus genuinely does NOT cover this. The label names the
                    ``absent_concept``, and the validator asserts that term
                    appears nowhere in the corpus. If the corpus later gains a
                    source covering it, the label becomes invalid and says so —
                    labels cannot silently rot as the corpus grows.

  expect="route"    The question asks for a personal recommendation. This is a
                    property of the question's FORM ("which should I", "is it
                    worth", "should I"), independent of coverage, so it needs no
                    corpus provenance.

``difficulty`` records WHY a case is interesting, so failures are diagnosable
rather than just counted:
  plain        - phrased close to how a source phrases it
  paraphrase   - same concept, different words from the source
  abbreviation - the user types LISA / CGT / NI / SIPP
  near_miss    - ADJACENT to the corpus but not covered. The most valuable class:
                 these are where a lexical engine is most tempted to answer from
                 a topically-related passage that does not actually contain the
                 answer, and where a false answer would be most convincing.

HONEST LIMITATIONS (stated because a benchmark that hides them is marketing)
  * The questions were authored by reading the corpus inventory, so the
    answerable set is biased toward things the corpus plausibly covers. The
    paraphrase/abbreviation/near_miss classes exist to push against that bias,
    but this is not a sample of real user traffic.
  * ``absent_concept`` is a lexical check. A corpus could in principle discuss a
    concept without ever using the probe word; the validator would then wrongly
    accept the label. Probes are chosen to be the obvious term for the topic.
  * The validator's "is the corpus ABOUT this?" test is a threshold (a title
    match, or 3+ distinct passages), and a threshold has two sides. It correctly
    ignores a passage that says "visa" three times while being about visa
    *scams*; it also missed genuine coverage of salary sacrifice spread over
    only 2 passages, which a human read caught. Treat a clean ``--validate`` as
    "no label has rotted", not as "every label is right".
  * Size is 131 questions, not thousands. It is enough to calibrate two
    thresholds and to detect a regression; it is not enough to certify a
    retrieval change on its own.
"""

from __future__ import annotations

import json
from pathlib import Path

# ── answerable: (id, question, supported_by, probe, difficulty) ───────────────────
ANSWERABLE: list[tuple[str, str, str, str, str]] = [
    # savings & ISAs
    ("isa-allowance", "How much can I pay into an ISA each year?", "savings_isas-isa-overview", "allowance", "plain"),
    ("isa-types", "What types of ISA are there?", "savings_isas-isa-overview", "isa", "plain"),
    ("isa-transfer", "Can I transfer an ISA to a different provider?", "savings_isas-isa-overview", "transfer", "plain"),
    ("isa-who-can-open", "Who is eligible to open an ISA?", "savings_isas-isa-overview", "resident", "paraphrase"),
    ("lisa-how-works", "How does a Lifetime ISA work?", "savings_isas-lifetime-isa", "bonus", "plain"),
    ("lisa-bonus", "What government bonus do I get on a Lifetime ISA?", "savings_isas-lifetime-isa", "bonus", "plain"),
    ("lisa-abbrev", "How much can I put in a LISA each year?", "savings_isas-lifetime-isa", "year", "abbreviation"),
    ("lisa-withdraw", "What happens if I withdraw from a Lifetime ISA early?", "savings_isas-lifetime-isa", "withdraw", "plain"),
    ("jisa-overview", "What is a Junior ISA?", "savings_isas-junior-isa", "junior", "plain"),
    ("jisa-abbrev", "Who can pay into a JISA?", "savings_isas-junior-isa", "pay", "abbreviation"),
    ("ctf-overview", "What is a Child Trust Fund?", "savings_isas-child-trust-fund", "trust", "plain"),
    ("psa-overview", "What is the personal savings allowance?", "savings_isas-tax-on-savings-interest", "allowance", "plain"),
    ("savings-tax-interest", "Do I pay tax on my savings interest?", "savings_isas-tax-on-savings-interest", "interest", "plain"),
    ("savings-starting-rate", "What is the starting rate for savings?", "savings_isas-tax-on-savings-interest", "starting", "plain"),
    ("help-to-save-bonus", "How does the Help to Save bonus work?", "savings_isas-help-to-save", "bonus", "plain"),
    ("children-savings-interest", "Is interest on my child's savings taxable?", "savings_isas-children-savings-interest", "interest", "paraphrase"),

    # pensions
    ("state-pension-new", "How much is the new State Pension?", "pensions-new-state-pension", "pension", "plain"),
    ("state-pension-qualify", "How many qualifying years do I need for the State Pension?", "pensions-new-state-pension", "qualifying", "plain"),
    ("state-pension-forecast", "How do I check my State Pension forecast?", "pensions-check-state-pension-forecast", "forecast", "plain"),
    ("workplace-auto-enrolment", "What is automatic enrolment into a workplace pension?", "pensions-workplace-pensions", "enrolment", "plain"),
    ("workplace-employer-contrib", "How much does my employer have to contribute to my pension?", "pensions-workplace-pensions", "employer", "plain"),
    ("workplace-opt-out", "Can I opt out of my workplace pension?", "pensions-workplace-pensions", "opt", "plain"),
    ("pension-tax-relief", "How does pension tax relief work?", "pensions-tax-on-private-pension", "relief", "plain"),
    ("pension-annual-allowance", "What is the pension annual allowance?", "pensions-tax-on-private-pension", "allowance", "plain"),
    ("pension-abbrev-sipp", "How is a SIPP taxed?", "pensions-tax-on-private-pension", "pension", "abbreviation"),
    ("personal-pension-overview", "What is a personal pension?", "pensions-personal-pensions", "personal", "plain"),
    ("retirement-income-options", "What are my options for taking my retirement income?", "pensions-plan-retirement-income", "retirement", "plain"),
    ("voluntary-ni-topup", "Can I pay voluntary National Insurance to fill gaps in my record?", "pensions-voluntary-ni-contributions", "voluntary", "plain"),
    ("pension-scam-warning", "How can I spot a pension scam?", "pensions-fca-pension-scams", "scam", "plain"),

    # tax
    ("income-tax-rates", "What are the income tax rates?", "tax-income-tax-rates", "rate", "plain"),
    ("personal-allowance", "What is the personal allowance for income tax?", "tax-income-tax-rates", "allowance", "plain"),
    ("income-tax-what-on", "What income do I pay tax on?", "tax-income-tax-overview", "income", "plain"),
    ("cgt-what-on", "What do I pay Capital Gains Tax on?", "tax-capital-gains", "gain", "plain"),
    ("cgt-abbrev", "What is the CGT rate on shares?", "tax-capital-gains", "rate", "abbreviation"),
    ("cgt-allowance", "Is there a tax-free allowance for capital gains?", "tax-capital-gains", "allowance", "paraphrase"),
    ("dividend-tax", "How much tax do I pay on dividends?", "tax-dividends", "dividend", "plain"),
    ("dividend-allowance", "What is the dividend allowance?", "tax-dividends", "allowance", "plain"),
    ("ni-overview", "What is National Insurance?", "tax-national-insurance-overview", "insurance", "plain"),
    ("ni-abbrev", "How much NI do I pay?", "tax-national-insurance-overview", "insurance", "abbreviation"),
    ("ni-categories", "What are the National Insurance categories?", "tax-ni-rates-categories", "categor", "plain"),
    ("ni-self-employed", "What National Insurance do the self-employed pay?", "tax-self-employed-ni-rates", "employ", "plain"),
    ("marriage-allowance", "How do I claim Marriage Allowance?", "tax-marriage-allowance", "marriage", "plain"),
    ("self-assessment-who", "Do I need to send a Self Assessment tax return?", "tax-self-assessment", "return", "plain"),
    ("self-assessment-deadline", "What is the deadline for a Self Assessment tax return?", "tax-self-assessment", "deadline", "plain"),
    ("self-assessment-register", "How do I register for Self Assessment?", "tax-self-assessment-register", "register", "plain"),
    ("tax-code-meaning", "What does my tax code mean?", "tax-tax-codes", "code", "plain"),
    ("tax-code-wrong", "What do I do if my tax code is wrong?", "tax-tax-codes", "code", "paraphrase"),
    ("iht-threshold", "What is the Inheritance Tax threshold?", "tax-inheritance-tax", "threshold", "plain"),
    ("iht-rate", "What rate is Inheritance Tax charged at?", "tax-inheritance-tax", "rate", "plain"),
    ("vat-register-when", "When do I have to register for VAT?", "tax-register-for-vat", "register", "plain"),
    ("vat-threshold", "What is the VAT registration threshold?", "tax-register-for-vat", "threshold", "plain"),
    ("vat-rates", "What are the VAT rates?", "tax-vat-rates", "rate", "plain"),
    ("ir35-what", "What is off-payroll working?", "tax-off-payroll-ir35", "payroll", "plain"),
    ("ir35-abbrev", "Does IR35 apply to my contract?", "tax-off-payroll-ir35", "payroll", "abbreviation"),

    # mortgages & property
    ("sdlt-what", "What is Stamp Duty Land Tax?", "mortgages-sdlt-guide", "stamp", "plain"),
    ("sdlt-first-time", "Do first-time buyers pay Stamp Duty?", "mortgages-sdlt-guide", "buyer", "plain"),
    ("smi-what", "What is Support for Mortgage Interest?", "mortgages-support-for-mortgage-interest", "mortgage", "plain"),
    ("shared-ownership", "How does shared ownership work?", "mortgages-shared-ownership", "shared", "plain"),
    ("first-homes", "What is the First Homes scheme?", "mortgages-first-homes-scheme", "home", "plain"),
    ("help-to-buy-equity", "How does the Help to Buy equity loan work?", "mortgages-help-to-buy-equity-loan", "equity", "plain"),
    ("mortgage-charter", "What is the Mortgage Charter?", "mortgages-mortgage-charter", "charter", "plain"),
    ("mortgage-struggling", "What support is there if I am struggling with my mortgage payments?", "mortgages-fca-payment-support", "mortgage", "paraphrase"),

    # budgeting, benefits & bills
    ("council-tax-how", "How does Council Tax work?", "budgeting-council-tax", "council", "plain"),
    ("council-tax-reduction", "Can I apply for a Council Tax Reduction?", "budgeting-council-tax-reduction", "reduction", "plain"),
    ("debt-options", "What are my options for dealing with my debts?", "budgeting-debt-options", "debt", "plain"),
    ("breathing-space", "What is the Breathing Space debt respite scheme?", "budgeting-breathing-space", "breathing", "plain"),
    ("budgeting-loan", "What is a Budgeting Loan?", "budgeting-budgeting-loans", "budgeting", "plain"),
    ("benefits-calculator", "Is there a calculator to check what benefits I can get?", "budgeting-benefits-calculators", "calculator", "plain"),
    ("energy-bills-help", "What help is available with my energy bills?", "budgeting-help-energy-bills", "energy", "plain"),
    ("warm-home-discount", "What is the Warm Home Discount?", "budgeting-warm-home-discount", "warm", "plain"),
    ("cost-of-living-fca", "What should I do if I cannot keep up with my bills?", "budgeting-fca-cost-of-living", "bill", "paraphrase"),

    # scams & protection
    ("scam-protect", "How do I protect myself from financial scams?", "scams_protection-fca-protect-yourself-scams", "scam", "plain"),
    ("firm-authorised", "How do I check whether a firm is authorised?", "scams_protection-fca-firm-checker", "firm", "plain"),
    ("warning-list", "What is the FCA warning list?", "scams_protection-fca-warning-list", "warning", "plain"),
    ("complain-firm", "How do I complain about a financial firm?", "scams_protection-fca-how-to-complain", "complain", "plain"),
    ("firm-fails-compensation", "Can I claim compensation if a financial firm fails?", "scams_protection-fca-claim-compensation-firm-fails", "compensation", "plain"),
    ("report-phishing", "How do I report a phishing email?", "scams_protection-govuk-report-internet-scams-phishing", "phishing", "plain"),
    ("hmrc-genuine", "How do I know if a message from HMRC is genuine?", "scams_protection-hmrc-genuine-contacts", "hmrc", "plain"),
    # All three of these were authored as near-miss ABSTAIN cases and turned out
    # to be wrong: the corpus does cover them. Relabelled rather than deleted,
    # because a benchmark that drops its own inconvenient findings is worthless.
    ("fscs-protection", "How much of my money does FSCS protect?", "scams_protection-fca-claim-compensation-firm-fails", "fscs", "paraphrase"),
    ("hicbc", "What is the high income child benefit charge?", "tax-self-assessment", "child benefit", "near_miss"),
    # This one the automatic floor did NOT catch, and that is worth recording
    # rather than hiding. `_is_about` needs 3 passages; salary sacrifice occupies
    # 2, so the abstain label passed validation. Reading those two passages
    # settles it: "you give up part of your salary and your employer pays this
    # straight into your pension... you and your employer pay less tax and
    # National Insurance" answers the question. The floor is a guard against
    # rot, not a substitute for reading the corpus — see the honest limitations
    # above.
    ("salary-sacrifice", "How does salary sacrifice work?", "pensions-workplace-pensions", "salary sacrifice", "near_miss"),
]

# ── must abstain: (id, question, absent_concept, why, difficulty) ─────────────────
ABSTAIN: list[tuple[str, str, str, str, str]] = [
    # plainly outside a UK personal-finance corpus
    ("oos-passport", "How do I renew my passport?", "passport", "not a personal-finance topic", "plain"),
    ("oos-driving", "How do I book a driving theory test?", "driving", "not a personal-finance topic", "plain"),
    ("oos-weather", "What is the weather forecast for tomorrow?", "weather", "not a personal-finance topic", "plain"),
    ("oos-solar", "How do I install solar panels?", "solar", "not a personal-finance topic", "plain"),
    ("oos-visa", "How do I apply for a spouse visa?", "visa", "not a personal-finance topic", "plain"),
    ("oos-recipe", "How do I cook a roast dinner?", "roast", "not a personal-finance topic", "plain"),
    ("oos-nhs", "How do I register with a dentist?", "dentist", "not a personal-finance topic", "plain"),
    ("oos-marriage-cert", "How do I order a copy of a marriage certificate?", "marriage certificate", "not a personal-finance topic", "plain"),

    # NEAR MISSES — finance-shaped, adjacent to the corpus, genuinely not covered.
    # These are the cases where answering from a topically-related passage would
    # produce a convincing but unsupported answer.
    ("nm-credit-score", "How do I improve my credit score?", "credit score", "credit scoring is not in the corpus", "near_miss"),
    ("nm-credit-report", "How do I get a copy of my credit report?", "credit report", "credit reference agencies are not in the corpus", "near_miss"),
    ("nm-energy-price-cap", "What is the energy price cap set at?", "price cap", "Ofgem price-cap levels are not in the corpus", "near_miss"),
    ("nm-open-banking", "What is open banking?", "open banking", "open banking is not in the corpus", "near_miss"),
    ("nm-compound-interest", "How does compound interest work?", "compound", "compound interest is not explained in the corpus", "near_miss"),
    ("nm-emergency-fund", "How big should my emergency fund be?", "emergency fund", "budgeting rules of thumb are not in the corpus", "near_miss"),
    ("nm-crypto-tax", "How is cryptocurrency taxed?", "cryptocurrency", "crypto is not covered by the held sources", "near_miss"),
    ("nm-premium-bonds", "What are the odds of winning on Premium Bonds?", "premium bond", "NS&I products are not in the corpus", "near_miss"),
    ("nm-equity-release", "How does equity release work?", "equity release", "equity release is not in the corpus", "near_miss"),
    ("nm-annuity-rates", "What annuity rate would I get?", "annuity rate", "annuity pricing is not in the corpus", "near_miss"),
    ("nm-mortgage-fixed-tracker", "What is the difference between a fixed and a tracker mortgage?", "tracker", "mortgage product types are not in the corpus", "near_miss"),
    ("nm-overdraft", "How much does an unarranged overdraft cost?", "overdraft", "overdraft pricing is not in the corpus", "near_miss"),
    ("nm-student-loan-threshold", "What is the student loan repayment threshold?", "student loan", "student loans are not in the corpus", "near_miss"),
    ("nm-smp", "How much statutory maternity pay will I get?", "statutory maternity pay", "statutory pay is not in the corpus", "near_miss"),
    ("nm-ssp", "How much is statutory sick pay?", "statutory sick pay", "statutory pay is not in the corpus", "near_miss"),
    ("nm-universal-credit-rate", "What is the standard allowance for Universal Credit?", "standard allowance", "UC award rates are not in the corpus", "near_miss"),
    ("nm-inflation", "What is the current rate of inflation?", "inflation", "macroeconomic series are not in the corpus", "near_miss"),
    ("nm-base-rate", "What is the Bank of England base rate?", "base rate", "the policy rate is not in the corpus", "near_miss"),
    ("nm-business-rates", "How are business rates calculated?", "business rate", "business rates are not in the corpus", "near_miss"),
    ("nm-rent-a-room", "How does the Rent a Room scheme work?", "rent a room", "the scheme is not in the corpus", "near_miss"),
    ("nm-trading-allowance", "What is the trading allowance?", "trading allowance", "the trading allowance is not in the corpus", "near_miss"),
    ("nm-p60", "When should I receive my P60?", "p60", "employment forms are not in the corpus", "near_miss"),
    ("nm-jurisdiction-ireland", "What is the ISA allowance in the Republic of Ireland?", "republic of ireland", "non-UK jurisdiction; note plain 'ireland' appears throughout as Northern Ireland", "near_miss"),
    ("nm-jurisdiction-us", "How does a Roth IRA compare to an ISA?", "roth ira", "non-UK product", "near_miss"),
]

# ── must route (advice boundary): (id, question, trigger) ─────────────────────────
ROUTE: list[tuple[str, str, str]] = [
    ("adv-which-isa", "Which ISA should I open?", "which should I"),
    ("adv-should-i-lisa", "Should I open a Lifetime ISA or a pension?", "should I"),
    ("adv-worth-it", "Is a Lifetime ISA worth it for me?", "worth it for me"),
    ("adv-best-pension", "What is the best pension for me?", "best for me"),
    ("adv-how-much-save", "How much should I be saving each month?", "how much should I"),
    ("adv-invest-where", "Where should I invest my savings?", "where should I invest"),
    ("adv-pay-off-mortgage", "Should I pay off my mortgage or invest instead?", "should I"),
    ("adv-smart", "Is it smart to put all my savings in one ISA?", "is it smart"),
    ("adv-wise", "Would it be wise to opt out of my workplace pension?", "would it be wise"),
    ("adv-recommend", "Can you recommend a good stocks and shares ISA?", "recommend"),
    ("adv-my-situation", "Given my situation, what should I do with a 20k inheritance?", "what should I do"),
    ("adv-friend", "My friend wants to know if she should transfer her pension - should she?", "third-person on-behalf-of"),
    ("adv-if-you-were-me", "If you were me, would you take the 25% tax-free lump sum?", "hypothetical self-insertion"),
    ("adv-no-brainer", "Is maxing out my ISA a no-brainer?", "informal suitability framing"),
    ("adv-tell-me-to", "Just tell me to open a LISA and I will do it", "imperative"),
    ("adv-most-people", "What do most people in my position do with their pension?", "population framing"),
    ("adv-suggest", "Please suggest me the best way to save for a house", "ESL-style polite request"),
    ("adv-safer", "Which is safer for my money, an ISA or a pension?", "comparative suitability"),
]


def build() -> dict:
    questions: list[dict] = []
    for qid, q, doc, probe, diff in ANSWERABLE:
        questions.append({
            "id": f"ans-{qid}", "question": q, "expect": "answer",
            "supported_by": [doc], "probe": probe, "difficulty": diff,
        })
    for qid, q, concept, why, diff in ABSTAIN:
        questions.append({
            "id": f"abs-{qid}", "question": q, "expect": "abstain",
            "absent_concept": concept, "why": why, "difficulty": diff,
        })
    for qid, q, trigger in ROUTE:
        questions.append({
            "id": f"rte-{qid}", "question": q, "expect": "route",
            "trigger": trigger, "difficulty": "plain",
        })
    return {
        "schema_version": 1,
        "description": (
            "Pistis answerability benchmark. Labels are derived from the CORPUS "
            "and from question FORM, never from the engine's output - see "
            "bench_build.py for the labelling protocol and its stated limits."
        ),
        "counts": {
            "answer": len(ANSWERABLE), "abstain": len(ABSTAIN), "route": len(ROUTE),
            "total": len(questions),
        },
        "questions": questions,
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("bench.json")
    data = build()
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out} - {data['counts']}")
