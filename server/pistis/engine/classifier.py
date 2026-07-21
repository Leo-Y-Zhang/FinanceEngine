"""Advice-boundary classifier.

Detects personal-recommendation-shaped questions and converts them into
routing events before any retrieval happens. The bright line (Art 53 RAO /
PERG 8.30B): a communication presented as suitable for a person, or based on
their circumstances, about a specific investment. Two traps designed against:
implicit suitability ("people like you choose X") and multi-factor
personalised narrowing. Deliberately conservative — a false route is safe,
a false answer is not.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ClassifierResult:
    is_personal_rec: bool
    matched: tuple[str, ...]

    @property
    def reason(self) -> str:
        if not self.is_personal_rec:
            return "guidance-shaped question"
        return (
            "This looks like a request for a personal recommendation, which "
            "only an FCA-authorised adviser can give."
        )


# Each pattern is (name, compiled regex). Names surface in RoutingEvent.matched
# so red-team tests can assert exactly which rule fired.
_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (name, re.compile(rx, re.IGNORECASE))
    for name, rx in [
        # Direct ask for a decision: "should I ...", "what should I do"
        ("should-i", r"\bshould\s+(i|we)\b"),
        ("shall-i", r"\bshall\s+(i|we)\b"),
        # "which/what X do I pick/choose/transfer into" — reallocation verbs
        # (transfer/move/switch/put) are the highest-stakes selection asks
        ("which-for-me", r"\bwhich\b[^?.]{0,60}\b(pick|choose|go\s+(for|with|into)|buy|get|open|invest|transfer|move|switch|put|pay\s+into|use)\b"),
        # Suitability framing: "best/right/good ... for me/my"
        ("best-for-me", r"\b(best|right|good|better|ideal|suitable)\b[^?.]{0,60}\bfor\s+(me|my|us|our|someone\s+like\s+me)\b"),
        ("right-for-me", r"\bfor\s+(me|my\s+situation|my\s+circumstances)\b[^?.]{0,40}\b(best|right|suitable|good\s+idea|worth)\b"),
        # Product superlative without "for me": "what is the best ISA?" is a
        # selection ask. Lookahead excludes process phrasings ("best way to").
        ("product-superlative", r"\b(best|better|ideal|top)\b(?!\s+(way|time|place|method)\b)[^?.]{0,30}\b(isa|lisa|jisa|sipp|pension|annuity|mortgage|fund|account|provider|platform)\b"),
        # Explicit advice ask
        ("recommend", r"\b(recommend|advise\s+me|advice\s+for\s+me|what\s+would\s+you\s+(do|pick|choose|buy))\b"),
        # "is it worth (it) (for me)" / "good idea to"
        ("worth-it", r"\b(is\s+it\s+worth|worthwhile|good\s+idea\s+(for\s+me\s+)?to)\b"),
        # Suitability verbs beyond "worth": smart/wise/sensible/makes sense/
        # the way to go — the same ask in everyday phrasing
        ("suitability-verb", r"\b(is|are|was|would|does|do|did)\b[^?.]{0,50}\b(smart|wise|sensible|prudent|make[s]?\s+sense|the\s+way\s+to\s+go|the\s+right\s+(call|move|choice|option)|the\s+better\s+(pick|option|choice)|a\s+good\s+move)\b"),
        # Implicit suitability via population framing: "what do most people
        # do", "people in my position" — PERG 8.30B's people-like-you trap
        ("population-suitability", r"\b(most\s+people|people\s+(usually|typically|normally|generally|tend)|people\s+(like\s+me|in\s+my\s+(position|situation|shoes))|people\s+my\s+age|others?\s+in\s+my\s+(position|situation))\b"),
        # Imperative recommendation: "tell me to open X", "tell me whether to"
        ("imperative-rec", r"\b(tell|show)\s+me\b[^?.]{0,40}\b(to\s+(open|buy|get|choose|pick|put|move|transfer|invest|switch)|whether\s+(to|i)\b)"),
        # Personalised narrowing: personal circumstances + a which/what-product ask
        ("circumstances-narrowing", r"\bi\s+(have|earn|make|own|am|'m)\b[^?.]{0,80}\b(which|what|where)\b[^?.]{0,60}\b(isa|pension|mortgage|fund|account|invest|save|put)\b"),
        # Where should my money go
        ("where-money", r"\bwhere\b[^?.]{0,40}\b(put|invest|move)\b[^?.]{0,30}\b(money|savings|cash|pension|£)"),
    ]
)

# Named-provider suitability: a specific provider + a decision verb. Providers
# list is a seed, not a registry — the classifier is one of two gates, and the
# composer never emits provider names it wasn't given by a source.
_PROVIDERS = re.compile(
    r"\b(vanguard|nutmeg|moneybox|moneyfarm|wealthify|hargreaves\s+lansdown|"
    r"aj\s+bell|trading\s*212|freetrade|plum|chip|monzo|starling|revolut|"
    r"zopa|marcus|halifax|barclays|hsbc|lloyds|natwest|santander|nationwide)\b",
    re.IGNORECASE,
)
_DECISION_VERB = re.compile(
    r"\b(buy|sell|hold|switch|open|invest|move|transfer|choose|pick|use|join|worth|good|best)\b",
    re.IGNORECASE,
)


def classify(question: str) -> ClassifierResult:
    matched = [name for name, rx in _PATTERNS if rx.search(question)]
    if _PROVIDERS.search(question) and _DECISION_VERB.search(question):
        matched.append("named-provider")
    return ClassifierResult(is_personal_rec=bool(matched), matched=tuple(matched))
