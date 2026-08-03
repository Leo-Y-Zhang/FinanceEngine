"""Corpus-gap report — the refusals turned into a roadmap.

Reads the local ask-log, replays each distinct question through the engine, and
aggregates the concepts that make Finance Answer Engine abstain — the query terms no trusted
source covers (the same ``uncovered_terms`` diagnostic the refusal shows the
user). The result is a keyless backlog of the concepts people ask about that no
trusted source in the corpus covers. Refusal is a feature; this makes the
refusals *actionable*.

**Absent from the corpus is not the same as belongs in the corpus.** Nothing in
the engine classifies topical scope (the advice-boundary classifier detects
personal-recommendation *shape*, and the gate decides on retrieval strength and
coverage), so this report cannot tell a real gap from a question Finance Answer Engine
correctly refused as out of scope. It reports evidence and leaves the triage to
a human. The two sections say only what was measured:

  * **No source shared any term** — every token of the concept is absent from
    the entire corpus. This is the STRONGEST evidence of absence the system can
    produce, not a weak signal.
  * **Partial match** — trusted sources did match the question, but not
    strongly or completely enough in one place.

They are listed apart so neither crowds the other out of the ranking; the
division is by evidence, and is NOT a scope judgement.

Privacy posture — what is and is not guaranteed:
  * Aggregate-only: the output is per-concept frequencies and counts, and there
    is no question field on the report. On a very small log, though, the set of
    concepts can still approximate the vocabulary of an individual question.
  * A **repetition floor over distinct normalised questions** (``min_distinct``)
    withholds any concept that recurs less often. This is NOT k-anonymity and
    NOT anonymity over people: the ask-log records no user or session identity,
    so N distinct questions may all come from one person, and raising the floor
    does not change that. What the floor does do is stop a *cosmetic* retype
    counting twice — "distinct" is measured on a question's content tokens (the
    same normalisation retrieval uses), so case, punctuation, stopwords and word
    order cannot manufacture a second question. A genuinely differently-worded
    second question by the same person still counts.
  * Treat the report as **trusted-single-operator output**. It is a stdout-only
    ops CLI, exposed by no API and no web surface. Anyone who can write to the
    ask-log can increment the floor's counter, so the floor is not a control
    against a party who already has that access.
  * Amount- and identifier-shaped tokens are dropped: bare numbers, £-prefixed
    and digit-leading tokens (£45k, 20k, 1aa), National-Insurance-number shapes,
    long alphanumeric mixtures, and both halves of any full postcode typed in a
    question. Short letter-led codes are deliberately KEPT (p45, sa302, ir35) —
    they are real corpus-expansion concepts. This is best-effort scrubbing, not
    a guarantee: an isolated outward postcode fragment ("sw1a", "e14") is
    indistinguishable by shape from a form code, and a rare proper noun is a
    word like any other.
  * Deterministic and offline — no network, no keys. The report names its own
    inputs (log, snapshot, snapshot date) so a reader can check what it read.

    python -m finance_answer_engine.gaps                 # human-readable report
    python -m finance_answer_engine.gaps --all           # list every concept above the floor
    python -m finance_answer_engine.gaps --json          # machine-readable record
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from finance_answer_engine.corpus.store import load_snapshot
from finance_answer_engine.engine.answer import Engine
from finance_answer_engine.index.bm25 import Bm25Index, tokenize
from finance_answer_engine.models import Abstention, RoutingEvent

# Paths mirror finance_answer_engine.api.app (kept local so this CLI does not import FastAPI).
_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG = _ROOT / "logs" / "ask.jsonl"
DEFAULT_SNAPSHOT = _ROOT / "data" / "corpus" / "snapshot.json"

# Repetition floor: a concept must recur across at least this many distinct
# normalised questions to be reported. Conservative default for a small
# pre-launch log. See the module docstring for what this does and does not give.
DEFAULT_MIN_DISTINCT = 2

# Exit codes, so an operator (or a script) can tell "nothing to report" apart
# from "I could not read what you pointed me at" — the two used to look
# identical, both a clean empty report at status 0.
EXIT_OK = 0
EXIT_NO_LOG = 2
EXIT_NO_SNAPSHOT = 3

_NI_NUMBER = re.compile(r"[a-z]{2}\d{6}[a-d]?")
# A FULL postcode only. The outward code alone ("sw1a", "e14") has the same
# shape as real form codes ("cf83", "r85"), so shape cannot decide it — the
# pair is what identifies, and the pair is what gets redacted.
_POSTCODE = re.compile(r"\b[a-z]{1,2}\d[a-z\d]?\s*\d[a-z]{2}\b")


def _is_concept(term: str) -> bool:
    """Is this uncovered term reportable as a concept?

    Rejects amounts and identifier shapes while KEEPING short letter-led codes:
    "p45", "sa302" and "ir35" are among the most actionable gaps a UK-finance
    corpus can have, so a blanket ban on digits would be a worse defect than
    the one it fixes. "Has a letter in it" is likewise no test at all — NI
    numbers, postcodes and IBANs all contain letters.
    """
    if not any(c.isalpha() for c in term):
        return False
    if "£" in term or term[0].isdigit():  # £45k, 20k, 1st, 1aa
        return False
    if _NI_NUMBER.fullmatch(term):  # qq123456c
        return False
    return not (len(term) > 12 and any(c.isdigit() for c in term))  # IBAN-ish


def _postcode_tokens(question: str) -> set[str]:
    """Tokens to redact because they form a full postcode in this question."""
    found = _POSTCODE.findall(question.lower())
    return {t for m in found for t in m.split()} | {m.replace(" ", "") for m in found}


def _concept_key(term: str) -> tuple[str, ...]:
    """The canonical identity of an uncovered term, for counting.

    ``uncovered_terms`` returns the user's own wording, deliberately, so the
    refusal can show it back to them. Counting on that wording splits one gap
    across typing variants: "passport" in one question and "passports" in
    another score 1 each, so a concept asked about twice falls below a floor of
    2 and the most-requested gap is reported as nothing at all. Keying on
    ``tokenize`` — the same plural fold and abbreviation expansion the corpus is
    searched with — makes them one concept.

    Scope of this canonicalisation, honestly: it merges the plural fold, the
    stopword drop and the synonym expansion. It does NOT merge an abbreviation
    against its spelled-out form — "cgt" keys as (capital, gain, tax) while the
    three typed words key separately — so those still count apart.
    """
    return tuple(sorted(set(tokenize(term))))


def _question_key(question: str) -> object:
    """The identity of a question for distinctness.

    Measured on content tokens, so the same question retyped with different
    case, punctuation, stopwords or word order is ONE question. Keyed on the raw
    text instead, one person could clear the floor by typing their own question
    twice — the engine saw one query, the report counted two.

    A SET (not a sequence) because bag-of-words retrieval cannot distinguish
    word order either, so collapsing order-variants matches what the engine
    actually sees and is the more conservative of the two options. An
    all-stopword question keeps its raw text, or they would all collapse into
    one. A str and a frozenset never compare equal, so the two kinds of key
    coexist safely.
    """
    tokens = frozenset(tokenize(question))
    return tokens if tokens else question.strip().lower()


@dataclass(frozen=True)
class GapConcept:
    term: str  # the normalised concept, never the user's own wording
    questions: int  # distinct question wordings in which it appeared


@dataclass(frozen=True)
class GapSection:
    """One ranked backlog. ``total`` is the count above the floor BEFORE any
    ``top`` cap, so a truncated listing can never read as the whole backlog."""

    listed: tuple[GapConcept, ...] = ()
    total: int = 0
    suppressed: int = 0  # distinct concepts seen but below the floor


@dataclass(frozen=True)
class GapReport:
    # What was read, so the report's own inputs are checkable.
    log_path: str = ""
    snapshot_path: str = ""
    snapshot_fetched: str = ""
    log_found: bool = True
    asks_read: int = 0  # log lines carrying a usable question, before dedup
    lines_skipped: int = 0  # blank, unparseable, or no usable question
    # What came back, so an empty backlog cannot be mistaken for a healthy one.
    questions_analyzed: int = 0  # distinct normalised questions
    answered: int = 0
    routed: int = 0
    refused: int = 0
    refusals_with_concepts: int = 0
    refusals_without_concepts: int = 0  # no term-level signal: NOT represented
    min_distinct: int = 0
    privacy_floor_active: bool = True  # False when min_distinct < 2
    # The backlogs.
    no_shared_term: GapSection = field(default_factory=GapSection)
    partial_match: GapSection = field(default_factory=GapSection)


@dataclass
class _LogRead:
    questions: list[str] = field(default_factory=list)
    asks_read: int = 0
    lines_skipped: int = 0
    found: bool = True


def _read_questions(log_path: Path) -> _LogRead:
    """Distinct questions from the JSONL ask-log, in first-seen order.

    Malformed *lines* are skipped AND COUNTED, so the report can disclose that
    it did not read everything rather than quietly understating the backlog: a
    line that is not JSON, is not an object, has no question, or whose question
    is not a string (``null``, a number, a nested object) is skipped. A question
    is never ``str()``-coerced — that turned ``{"question": null}`` into the
    phantom concept "none" and mined a nested object's JSON keys.

    A file that is not valid UTF-8 is a different matter and is refused OUTRIGHT
    with an actionable error. Decoding it with replacement characters was worse
    than useless: a mangled latin-1 record still parses as JSON and would be
    silently ACCEPTED with corrupted text feeding the counts, and a UTF-16 log
    would report zero questions at status 0 — the exact silent false negative
    the rest of this file works to eliminate. ``utf-8-sig`` is used so a leading
    byte-order mark does not fail the first record.
    """
    if not log_path.exists():
        return _LogRead(found=False)
    try:
        text = log_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"cannot read ask-log {log_path}: not valid UTF-8 ({exc.reason}). "
            "Re-export it as UTF-8 rather than letting the report silently "
            "analyse corrupted text."
        ) from exc
    except OSError as exc:
        raise ValueError(f"cannot read ask-log {log_path}: {exc}") from exc

    read = _LogRead()
    seen: set[object] = set()
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            read.lines_skipped += 1
            continue
        if not isinstance(record, dict):
            read.lines_skipped += 1
            continue
        question = record.get("question")
        if not isinstance(question, str) or not question.strip():
            read.lines_skipped += 1
            continue
        question = question.strip()
        read.asks_read += 1
        key = _question_key(question)
        if key in seen:
            continue
        seen.add(key)
        read.questions.append(question)

    # A file with content but not one usable question is unreadable, whatever
    # the encoding — UTF-16 ASCII is technically valid UTF-8 (the NUL bytes
    # decode fine, then fail every JSON parse), so strict decoding alone cannot
    # catch it. Refuse rather than print a clean empty report at status 0.
    if read.asks_read == 0 and read.lines_skipped:
        raise ValueError(
            f"cannot read ask-log {log_path}: {read.lines_skipped} line(s) present "
            "but not one carried a usable question. Expected UTF-8 JSONL with a "
            'string "question" field.'
        )
    return read


def _section(
    keys: list[tuple[str, ...]],
    counts: Counter[tuple[str, ...]],
    min_distinct: int,
    top: int | None,
) -> GapSection:
    above = [(key, counts[key]) for key in keys if counts[key] >= min_distinct]
    # Rank by demand, then by the concept itself for a stable order.
    above.sort(key=lambda kn: (-kn[1], kn[0]))
    suppressed = sum(1 for key in keys if counts[key] < min_distinct)
    total = len(above)
    if top is not None:
        above = above[:top]
    return GapSection(
        listed=tuple(GapConcept(term="+".join(key), questions=n) for key, n in above),
        total=total,
        suppressed=suppressed,
    )


def corpus_gap_report(
    log_path: Path,
    snapshot_path: Path,
    min_distinct: int = DEFAULT_MIN_DISTINCT,
    top: int | None = None,
) -> GapReport:
    """Replay the ask-log against the current corpus and aggregate the concepts
    that still make Finance Answer Engine abstain. Re-asking (rather than trusting the logged
    outcome) means the report reflects the corpus as it stands now: a gap the
    corpus has since filled simply stops appearing.

    ``top`` caps how many concepts each section LISTS (None = no cap). The cap
    is never silent: each section's ``total`` carries the full pre-cap count.
    """
    if top is not None and top < 0:
        raise ValueError("top must be non-negative (or None for no cap)")
    passages = load_snapshot(Path(snapshot_path))
    engine = Engine(Bm25Index(passages))
    read = _read_questions(Path(log_path))

    # A concept is counted ONCE across every refusal that named it, so its
    # demand is never split. Which SECTION it lands in is decided separately, by
    # where it mostly showed up — counting per section would re-create the
    # fragmentation this report exists to avoid.
    counts: Counter[tuple[str, ...]] = Counter()
    by_bucket: dict[str, Counter[tuple[str, ...]]] = {
        "no_shared_term": Counter(),
        "partial_match": Counter(),
    }
    answered = routed = refused = 0
    with_concepts = without_concepts = 0

    for question in read.questions:
        response = engine.ask(question)
        if isinstance(response, RoutingEvent):
            routed += 1
            continue
        if not isinstance(response, Abstention):
            answered += 1
            continue
        refused += 1
        report = response.report
        if report is None:
            without_concepts += 1
            continue
        bucket = "no_shared_term" if report.stage == "no_source" else "partial_match"
        redact = _postcode_tokens(question)
        # One vote per question per concept, even if the question spelled the
        # concept two ways.
        reportable: set[tuple[str, ...]] = set()
        for raw in report.uncovered_terms:
            if raw in redact or not _is_concept(raw):
                continue
            key = _concept_key(raw) or (raw,)
            reportable.add(key)
        if reportable:
            with_concepts += 1
        else:
            without_concepts += 1
        for key in reportable:
            counts[key] += 1
            by_bucket[bucket][key] += 1

    # Each concept belongs to the section it mostly came from. A tie goes to
    # "no shared term", which is the stronger evidence of absence.
    absent = [
        k
        for k in counts
        if by_bucket["no_shared_term"][k] >= by_bucket["partial_match"][k]
    ]
    partial = [k for k in counts if k not in set(absent)]

    return GapReport(
        log_path=str(log_path),
        snapshot_path=str(snapshot_path),
        snapshot_fetched=max((p.fetched_at for p in passages), default=""),
        log_found=read.found,
        asks_read=read.asks_read,
        lines_skipped=read.lines_skipped,
        questions_analyzed=len(read.questions),
        answered=answered,
        routed=routed,
        refused=refused,
        refusals_with_concepts=with_concepts,
        refusals_without_concepts=without_concepts,
        min_distinct=min_distinct,
        privacy_floor_active=min_distinct >= 2,
        no_shared_term=_section(absent, counts, min_distinct, top),
        partial_match=_section(partial, counts, min_distinct, top),
    )


def _format_section(section: GapSection, heading: str, blind: int) -> list[str]:
    lines = ["", heading]
    if section.listed:
        width = max(len(c.term) for c in section.listed)
        for c in section.listed:
            plural = "question" if c.questions == 1 else "questions"
            lines.append(f"  {c.term.ljust(width)}  {c.questions} distinct {plural}")
        hidden = section.total - len(section.listed)
        if hidden > 0:
            # Never let the --top cap pass itself off as the whole backlog.
            lines.append(f"  ... and {hidden} more (raise --top to list them)")
    elif section.total:
        # Above the floor but nothing listed: --top 0.
        lines.append(f"  (none listed — raise --top to list {section.total})")
    elif blind:
        lines.append(
            f"  (none above the floor; {blind} refusal(s) produced no term-level"
            " signal and are NOT represented here)"
        )
    else:
        lines.append("  (none above the floor)")
    if section.suppressed:
        lines.append(f"  [{section.suppressed} below the floor, withheld]")
    return lines


def _format(r: GapReport) -> str:
    lines = [
        "Finance Answer Engine corpus-gap report",
        "========================",
        f"Ask-log                   : {r.log_path}"
        + ("" if r.log_found else "   *** NOT FOUND — nothing was analysed ***"),
        f"Corpus snapshot           : {r.snapshot_path}",
        f"Snapshot fetched          : {r.snapshot_fetched or 'unknown'}",
        f"Log lines skipped         : {r.lines_skipped}  (blank, unparseable, or no question)",
        "",
        f"Distinct questions        : {r.questions_analyzed}  (from {r.asks_read} asks in the log)",
        f"  answered                : {r.answered}",
        f"  routed (advice boundary): {r.routed}",
        f"  refused                 : {r.refused}",
        f"    naming a concept      : {r.refusals_with_concepts}",
        f"    naming none           : {r.refusals_without_concepts}",
        (
            f"Reporting floor           : a concept must appear in >= {r.min_distinct}"
            " distinct questions"
        ),
    ]
    if not r.privacy_floor_active:
        lines.append(
            "  *** WARNING: the floor is OFF at this setting — a concept only one"
            " person ever typed can be listed. ***"
        )
    lines += [
        "",
        "Repeat asks of the same wording count once, so a frequently-asked gap",
        "phrased identically can fall below the floor and be withheld. An",
        "uncovered concept may be a real corpus gap OR a question Finance Answer Engine",
        "correctly refused as out of scope; this report cannot tell them apart.",
        "Triage before adding anything.",
    ]
    lines += _format_section(
        r.no_shared_term,
        "NO SOURCE SHARED ANY TERM — absent from the whole corpus:",
        r.refusals_without_concepts,
    )
    lines += _format_section(
        r.partial_match,
        "PARTIAL MATCH — sources matched the question but fell short:",
        r.refusals_without_concepts,
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Finance Answer Engine corpus-gap report")
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument(
        "--min-distinct",
        type=int,
        default=DEFAULT_MIN_DISTINCT,
        help="repetition floor: min distinct questions a concept must appear in"
        f" (default {DEFAULT_MIN_DISTINCT}; below 2 disables the floor)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=25,
        help="max concepts to LIST per section (default 25; the full count is"
        " always reported); use --all for no cap",
    )
    parser.add_argument(
        "--all", action="store_true", help="list every concept above the floor (no --top cap)"
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)
    if args.top < 0:
        parser.error("--top must be non-negative (or use --all for no cap)")
    if args.min_distinct < 0:
        parser.error("--min-distinct must be non-negative")
    if not Path(args.snapshot).exists():
        parser.exit(
            EXIT_NO_SNAPSHOT,
            f"No corpus snapshot at {args.snapshot}.\n"
            "Build one with:  python -m finance_answer_engine.corpus.refresh\n",
        )

    try:
        report = corpus_gap_report(
            args.log,
            args.snapshot,
            min_distinct=args.min_distinct,
            top=None if args.all else args.top,
        )
    except ValueError as exc:
        parser.error(str(exc))

    print(json.dumps(asdict(report), indent=2) if args.json else _format(report))
    return EXIT_OK if report.log_found else EXIT_NO_LOG


if __name__ == "__main__":
    raise SystemExit(main())
