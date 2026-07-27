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

# How many distinct passages of one document must use a term before that
# document counts as being ABOUT it rather than mentioning it in passing. Two,
# measured: on the live corpus incidental terms sit in a single passage, and
# raising this to three bought no extra false answers blocked while costing
# real answers ("how do I know if a message from HMRC is genuine?").
ABOUTNESS_PASSAGES = 2

_TOKEN = re.compile(r"[a-z0-9£]+(?:/[0-9]+)?")

# Closed-class function words, dropped before matching. This list is
# load-bearing for HONESTY, not just for ranking: a query word absent from the
# list and absent from the corpus is scored at MAXIMUM idf by coverage(), and is
# named to the user by uncovered_terms as a concept "no trusted source covers".
# A missing function word therefore does real damage twice — it drags coverage
# down as hard as a genuinely unknown finance term, pushing borderline questions
# into a false refusal, and then it explains that refusal with a word like "am".
# Measured on the live 46-doc corpus before "am" was added here: idf("am") =
# 6.966, identical to idf("vat"), a concept the corpus really is missing.
#
# Only add words that cannot be a UK-finance concept. Deliberately NOT stopped,
# because each can carry real meaning in a money question: over, under, before,
# after, between, during, may (the month), less, up, down, out, off.
STOPWORDS = frozenset(
    """a an and are as at be but by can do does for from has have how i if in
    into is it its me my of on or that the their there these this to was what
    when where which who will with you your
    us we our ours get got much many people whether need use like also work
    works
    am been being were did doing done
    he she him her hers his they them theirs
    myself yourself himself herself itself ourselves yourselves themselves""".split()
)


def _fold(token: str) -> str:
    """Light plural fold so 'contributions' matches 'contribution'.

    Deliberately NOT a stemmer. See docs/SESSION_HANDOFF.md (session 8) for the
    measured evaluation of adding one: it answers ~3 more questions in 80 but
    changes every IDF and BM25 score, and the gate's thresholds were calibrated
    against THIS tokenizer, so it needs re-certification rather than a green eval.
    """
    if len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "is", "us")):
        return token[:-1]
    return token

# Token-level expansions for UK-finance abbreviations users actually type.
# The expansion REPLACES the abbreviation: official sources spell terms out,
# so keeping the raw abbreviation would leave an out-of-vocabulary token in
# the query that IDF-weighted coverage() counts as maximally uncovered —
# making well-covered abbreviation queries wrongly abstain.
SYNONYMS: dict[str, tuple[str, ...]] = {
    "lisa": ("lifetime", "isa"),
    "jisa": ("junior", "isa"),
    "sipp": ("self", "invested", "personal", "pension"),
    "ni": ("national", "insurance"),
    "cgt": ("capital", "gains", "tax"),
    "sdlt": ("stamp", "duty", "land", "tax"),
    "avc": ("additional", "voluntary", "contribution", "pension"),
}


def tokenize(text: str) -> list[str]:
    out: list[str] = []
    for t in _TOKEN.findall(text.lower()):
        out.extend(SYNONYMS.get(t, (t,)))
    return [_fold(t) for t in out if t not in STOPWORDS]


def _passage_vocab(passage: Passage) -> set[str]:
    """A passage's searchable vocabulary. Includes the document title: chunking
    strips the subject name from later passages ("the 25% bonus" passage of the
    Lifetime ISA guide), but the citation names it."""
    return set(tokenize(passage.text)) | set(tokenize(passage.doc_title))


def _query_words(query: str) -> list[tuple[str, frozenset[str]]]:
    """Original query words mapped to their content tokens (synonym expansion +
    plural fold, stopwords dropped), in first-seen order, deduplicated by the
    raw word. Keeps the user's own wording for display while matching on the
    same normalised tokens the index uses."""
    out: list[tuple[str, frozenset[str]]] = []
    seen: set[str] = set()
    for raw in _TOKEN.findall(query.lower()):
        if raw in seen:
            continue
        toks = frozenset(
            _fold(t) for t in SYNONYMS.get(raw, (raw,)) if t not in STOPWORDS
        )
        if not toks:
            continue
        seen.add(raw)
        out.append((raw, toks))
    return out


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
        # Document-level topical index: for each source document, how many of its
        # DISTINCT passages use each term, plus the terms in its title. Passage
        # counts are taken from passage TEXT alone here — deliberately not
        # `_passage_vocab`, which folds the title into every passage and would
        # make a title term look like it saturates the whole document.
        self._doc_passage_df: dict[str, Counter[str]] = {}
        self._doc_title_terms: dict[str, set[str]] = {}
        self._doc_passage_count: Counter[str] = Counter()
        for passage, toks in zip(self._passages, self._docs):
            self._doc_passage_df.setdefault(passage.doc_id, Counter()).update(set(toks))
            self._doc_title_terms.setdefault(
                passage.doc_id, set(tokenize(passage.doc_title))
            )
            self._doc_passage_count[passage.doc_id] += 1

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
            available = _passage_vocab(h.passage)
            best = max(best, sum(weight(t) for t in terms if t in available) / total)
        return best

    def is_about(self, doc_id: str, term: str) -> bool:
        """Does this document TREAT ``term`` as a subject, rather than mention it?

        Titled for it, or using it across at least ABOUTNESS_PASSAGES distinct
        passages. Measured on the live corpus, incidental terms occupy one
        passage and never reach a title, while genuinely covered subjects do
        both — the same separation the benchmark's label validator relies on.
        """
        if term in self._doc_title_terms.get(doc_id, frozenset()):
            return True
        # Relative to document length, because a raw passage count means very
        # different things at different sizes: live documents run to a median of
        # 32 passages, but some hold only two, and in a two-passage document one
        # passage IS half the subject matter. Without this, "about" silently
        # became "impossible to satisfy" for short sources.
        total = self._doc_passage_count.get(doc_id, 0)
        required = min(ABOUTNESS_PASSAGES, math.ceil(total / 2)) if total else ABOUTNESS_PASSAGES
        return self._doc_passage_df.get(doc_id, {}).get(term, 0) >= max(1, required)

    def topic_share(self, query: str, doc_id: str) -> float:
        """How much of the question's meaning this document is actually ABOUT.

        The third signal, and a different question from the other two.
        ``coverage`` asks whether the words are present; ``faithfulness`` asks
        whether a claim is supported by the passage it came from. Neither asks
        whether the source addresses the subject that was raised — so a passage
        listing "statutory sick pay" among types of earnings scores a perfect
        coverage for "how much is statutory sick pay?", and a grounded, correctly
        cited claim about inheritance-tax taper relief comes back for "how is
        cryptocurrency taxed?". Both were real, measured failures.

        IDF-weighted for the same reason ``coverage`` is, and for one more: it
        makes the measure immune to a single junk term. "How much can I pay into
        an ISA each year?" has "each" as its RAREST token — rarer than "isa" —
        so any rule keyed on the single rarest word puts the whole question on a
        function word. Weighting by share of total meaning lets "isa" carry it.
        """
        terms = set(tokenize(query))
        if not terms:
            return 0.0
        max_idf = max(self._idf.values(), default=1.0)
        weight = lambda t: self._idf.get(t, max_idf)  # noqa: E731
        total = sum(weight(t) for t in terms)
        if not total:
            return 0.0
        return sum(weight(t) for t in terms if self.is_about(doc_id, t)) / total

    def uncovered_terms(self, query: str, hits: list[Hit], top_n: int = 4) -> list[str]:
        """The query's own words that no top passage covers — the concepts the
        corpus is silent on. A word counts as uncovered only when *every* token
        it expands to is absent from the union of the top passages, so a partly
        matched term (e.g. "tax" present, "capital"/"gains" absent) is not
        wrongly flagged. Ordered by IDF weight (rarest, most telling gap first),
        then alphabetically for determinism. This turns an opaque abstain into a
        specific, honest 'we don't cover X' — without ever leaking the corpus."""
        words = _query_words(query)
        if not words:
            return []
        available: set[str] = set()
        for h in hits[:top_n]:
            available |= _passage_vocab(h.passage)
        max_idf = max(self._idf.values(), default=1.0)
        weight = lambda toks: max(  # noqa: E731
            (self._idf.get(t, max_idf) for t in toks), default=max_idf
        )
        missing = [(raw, weight(toks)) for raw, toks in words if toks.isdisjoint(available)]
        missing.sort(key=lambda rw: (-rw[1], rw[0]))
        return [raw for raw, _ in missing]
