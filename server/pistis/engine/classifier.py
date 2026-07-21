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
        # "which/what X should|do I pick/choose/go for/buy"
        ("which-for-me", r"\bwhich\b[^?.]{0,60}\b(pick|choose|go\s+for|buy|get|open|invest)\b"),
        # Suitability framing: "best/right/good ... for me/my"
        ("best-for-me", r"\b(best|right|good|better|ideal|suitable)\b[^?.]{0,60}\bfor\s+(me|my|us|our|someone\s+like\s+me)\b"),
        ("right-for-me", r"\bfor\s+(me|my\s+situation|my\s+circumstances)\b[^?.]{0,40}\b(best|right|suitable|good\s+idea|worth)\b"),
        # Explicit advice ask
        ("recommend", r"\b(recommend|advise\s+me|advice\s+for\s+me|what\s+would\s+you\s+(do|pick|choose|buy))\b"),
        # "is it worth (it) (for me)" / "good idea to"
        ("worth-it", r"\b(is\s+it\s+worth|good\s+idea\s+(for\s+me\s+)?to)\b"),
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
