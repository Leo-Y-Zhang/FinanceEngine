"""Deterministic BM25 retrieval over corpus passages.

Pure-python on purpose: no native deps on a locked-down box, and scoring
stays fully reproducible, which the gate's calibration tests rely on.
Uses Lucene-style smoothed IDF (never negative).
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from pistis.models import Passage

K1 = 1.5
B = 0.75

_TOKEN = re.compile(r"[a-z0-9£]+(?:/[0-9]+)?")

STOPWORDS = frozenset(
    """a an and are as at be but by can do does for from has have how i if in
    into is it its me my of on or that the their there these this to was what
    when where which who will with you your
    us we our ours get got much many people whether need use like also work
    works""".split()
)


def _fold(token: str) -> str:
    """Light plural fold so 'contributions' matches 'contribution'."""
    if len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "is", "us")):
        return token[:-1]
    return token

# Token-level expansions for UK-finance abbreviations users actually type.
# The abbreviation itself is kept so documents using it still match.
SYNONYMS: dict[str, tuple[str, ...]] = {
    "lisa": ("lisa", "lifetime", "isa"),
    "jisa": ("jisa", "junior", "isa"),
    "sipp": ("sipp", "self", "invested", "personal", "pension"),
    "ni": ("ni", "national", "insurance"),
    "cgt": ("cgt", "capital", "gains", "tax"),
    "sdlt": ("sdlt", "stamp", "duty", "land", "tax"),
    "fscs": ("fscs", "compensation", "protection"),
    "avc": ("avc", "additional", "voluntary", "contribution", "pension"),
}


def tokenize(text: str) -> list[str]:
    out: list[str] = []
    for t in _TOKEN.findall(text.lower()):
        out.extend(SYNONYMS.get(t, (t,)))
    return [_fold(t) for t in out if t not in STOPWORDS]


@dataclass(frozen=True)
class Hit:
    passage: Passage
    score: float


class Bm25Index:
    def __init__(self, passages: list[Passage]) -> None:
        self._passages = list(passages)
        self._docs = [tokenize(p.text) for p in self._passages]
        self._doc_freqs = [Counter(d) for d in self._docs]
        self._avgdl = (
            sum(len(d) for d in self._docs) / len(self._docs) if self._docs else 0.0
        )
        df: Counter[str] = Counter()
        for d in self._docs:
            df.update(set(d))
        n = len(self._docs)
        self._idf = {
            term: math.log(1 + (n - f + 0.5) / (f + 0.5)) for term, f in df.items()
        }

    def __len__(self) -> int:
        return len(self._passages)

    def search(self, query: str, k: int = 8) -> list[Hit]:
        terms = tokenize(query)
        if not terms or not self._docs:
            return []
        scored: list[Hit] = []
        for passage, doc, freqs in zip(self._passages, self._docs, self._doc_freqs):
            score = 0.0
            dl = len(doc)
            for term in terms:
                if term not in freqs:
                    continue
                idf = self._idf.get(term, 0.0)
                tf = freqs[term]
                score += idf * (tf * (K1 + 1)) / (
                    tf + K1 * (1 - B + B * dl / self._avgdl)
                )
            if score > 0:
                scored.append(Hit(passage=passage, score=score))
        scored.sort(key=lambda h: (-h.score, h.passage.id))
        return scored[:k]

    def coverage(self, query: str, hits: list[Hit], top_n: int = 4) -> float:
        """Best single-passage IDF-weighted coverage of the query's terms.

        The gate's second signal, with two deliberate properties. IDF
        weighting: rare, meaningful terms dominate, so a question can't pass
        because generic words happen to appear somewhere, and a term the
        corpus has never seen gets maximum weight and counts as uncovered —
        the strongest abstain signal there is. Best-single-passage: the
        terms must be covered *together* by one source passage; a union
        over passages would reward scattered incidental mentions from
        unrelated documents, which is not grounding.
        """
        terms = set(tokenize(query))
        if not terms:
            return 0.0
        max_idf = max(self._idf.values(), default=1.0)
        weight = lambda t: self._idf.get(t, max_idf)  # noqa: E731
        total = sum(weight(t) for t in terms)
        if not total:
            return 0.0
        best = 0.0
        for h in hits[:top_n]:
            available = set(tokenize(h.passage.text))
            best = max(best, sum(weight(t) for t in terms if t in available) / total)
        return best
