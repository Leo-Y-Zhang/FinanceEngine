"""Corpus-gap report — the refusals turned into a roadmap.

Reads the local ask-log, replays each distinct question through the engine, and
aggregates the concepts that make Pistis abstain — the query terms no trusted
source covers (the same ``uncovered_terms`` diagnostic the refusal shows the
user). The result is a keyless, privacy-safe backlog of what to add to the
corpus next: the money questions people ask that Pistis cannot yet answer.
Refusal is a feature; this makes the refusals *actionable*.

Two kinds of gap, reported separately and never mixed, because they mean
opposite things to whoever curates the corpus:

  * **Thin coverage** — trusted sources DID match the question, but not
    strongly or completely enough in one place. These are the real
    corpus-expansion candidates: Pistis is on the topic and short of material.
  * **No overlap** — nothing in the corpus matched the question at all. Most of
    these are simply OUT OF SCOPE for a UK personal-finance corpus (a passport
    question, a weather question), and a zero-hit refusal names every content
    word in the question rather than one missing concept. Ranking them together
    with the thin-coverage gaps let off-topic noise outrank the genuine ones,
    so they are listed apart and must be triaged for scope before anything is
    added.

Privacy by construction:
  * Aggregate-only. Raw questions never leave the function; the output is
    concept frequencies, nothing else.
  * A reporting floor. A concept is reported only when it appears across at
    least ``min_distinct`` distinct questions. **What that does and does not
    guarantee:** the ask-log records no user identity, so the floor counts
    DISTINCT QUESTIONS, not distinct people — it is not k-anonymity over users,
    and one person asking about the same thing in two genuinely different ways
    can still cross it. To stop a single person crossing the floor by merely
    retyping, "distinct" is measured on a question's CONTENT TOKENS (the same
    normalisation the index matches on), so case, punctuation, stopwords and
    word order do not manufacture a second question. Raise the floor before
    exposing the report to more than one person's questions.
  * Concepts are canonicalised the way the index matches them, so a gap cannot
    hide by fragmenting across its spellings ("passport" / "passports").
  * Amounts and identifier-shaped strings are dropped: a term containing a
    digit is withheld unless it is a known UK tax-form code, so an amount
    ("50k"), a National Insurance number, a postcode or an IBAN can never be
    published as a "concept".
  * Deterministic and offline — no network, no keys. The report names its own
    inputs (log, snapshot, snapshot date) so a reader can check what it read.

    python -m pistis.gaps                 # human-readable report
    python -m pistis.gaps --json          # machine-readable record
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

from pistis.corpus.store import load_snapshot
from pistis.engine.answer import Engine
from pistis.index.bm25 import Bm25Index, tokenize
from pistis.models import Abstention, RoutingEvent

# Paths mirror pistis.api.app (kept local so this CLI does not import FastAPI).
_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG = _ROOT / "logs" / "ask.jsonl"
DEFAULT_SNAPSHOT = _ROOT / "data" / "corpus" / "snapshot.json"

# Reporting floor: a concept must appear across at least this many distinct
# questions to be reported. Conservative default for a small pre-launch log;
# raise it before exposing the report to more than one person's questions.
DEFAULT_MIN_DISTINCT = 2

# Exit codes, so an operator (or a script) can tell "nothing to report" apart
# from "I could not read what you pointed me at" — the two used to look
# identical, both a clean empty report with status 0.
EXIT_OK = 0
EXIT_NO_LOG = 2
EXIT_NO_SNAPSHOT = 3

# The ONLY digit-bearing terms allowed through: UK tax and benefit form codes
# users genuinely ask about by name, and which a corpus curator would want to
# see. Everything else containing a digit is withheld, because an amount or an
# identifier is not a concept to add to the corpus — and NI numbers, postcodes
# and IBANs all contain letters, so "has a letter in it" cannot be the test.
FORM_CODES = frozenset(
    """p45 p46 p60 p87 p11d p800 p53 p55 sa100 sa102 sa105 sa106 sa302 sa800
    ct600 r40 r85 iht205 iht400 vat100 sc2""".split()
)


def _is_concept(term: str) -> bool:
    """Is this uncovered term reportable as a concept?

    Default-deny: it must carry alphabetic content, and if it carries a digit
    it must be a known form code. That withholds amounts ("50k", "£45k") and
    every identifier shape — National Insurance numbers, postcodes, IBANs,
    account and reference numbers — which are not corpus concepts and could
    identify the person who typed them.
    """
    if not any(c.isalpha() for c in term):
        return False
    if any(c.isdigit() for c in term):
        return term.lower().lstrip("£") in FORM_CODES
    return True


def _concept_key(term: str) -> tuple[str, ...]:
    """The canonical identity of an uncovered term, for counting.

    Two surface words name the same concept when the index matches them on the
    same tokens — ``tokenize`` applies the plural fold and the abbreviation
    expansions the corpus is searched with. Counting raw surface words instead
    splits one gap across its spellings: "passport" in one question and
    "passports" in another each score 1, so a concept asked about twice falls
    below a floor of 2 and the most-requested gap is reported as nothing.
    """
    return tuple(sorted(set(tokenize(term))))


def _question_key(question: str) -> tuple[str, ...]:
    """The identity of a question for distinctness.

    Measured on content tokens, so the same question retyped with different
    case, punctuation, stopwords or word order is ONE question. Keying on the
    raw text instead let a single person clear the reporting floor by typing
    their question twice — the engine saw one query, the report counted two.
    An all-stopword question keeps its raw text so those do not all collapse
    into one.
    """
    tokens = tuple(sorted(set(tokenize(question))))
    return tokens if tokens else ("\x00raw", question.strip().lower())


@dataclass(frozen=True)
class GapConcept:
    term: str  # the most-used surface wording of this concept
    questions: int  # distinct questions in which this uncovered concept appeared


@dataclass(frozen=True)
class GapSection:
    """One ranked backlog. ``total`` is the count above the floor BEFORE any
    ``top`` cap, so a truncated listing can never read as the whole backlog."""

    listed: tuple[GapConcept, ...] = ()
    total: int = 0
    suppressed: int = 0  # distinct concepts seen but below the floor


@dataclass(frozen=True)
class GapReport:
    # What was read (so the reader can check the report's own inputs).
    log_path: str = ""
    snapshot_path: str = ""
    snapshot_fetched: str = ""
    log_found: bool = True
    lines_skipped: int = 0  # blank, unparseable, or no usable question
    # What came back, so an empty backlog cannot be mistaken for a healthy one.
    questions_analyzed: int = 0  # distinct questions
    answered: int = 0
    routed: int = 0
    refused: int = 0
    refusals_with_concepts: int = 0
    refusals_without_concepts: int = 0
    refusals_no_overlap: int = 0  # zero corpus hits: often out of scope
    min_distinct: int = 0
    # The backlogs.
    thin_coverage: GapSection = field(default_factory=GapSection)
    no_overlap: GapSection = field(default_factory=GapSection)


@dataclass
class _LogRead:
    questions: list[str] = field(default_factory=list)
    lines_skipped: int = 0
    found: bool = True


def _read_questions(log_path: Path) -> _LogRead:
    """Distinct questions from the JSONL ask-log, in first-seen order.

    Best-effort, and it says so afterwards: blank lines, unparseable lines, a
    missing question and a question that is not a string are all SKIPPED AND
    COUNTED, so the report can disclose that it did not read everything rather
    than quietly understating the backlog. Undecodable bytes (a log copied
    through a tool that rewrote it as UTF-16, say) degrade to replacement
    characters and fail the JSON parse — they are skipped like any other bad
    line instead of raising, which is what "best-effort" has to mean.
    """
    if not log_path.exists():
        return _LogRead(found=False)
    text = log_path.read_bytes().decode("utf-8", errors="replace")
    read = _LogRead()
    seen: set[tuple[str, ...]] = set()
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
        # Only a real string: str()-coercing a dict or a list would mine the
        # Python repr of a structure that was never a question.
        if not isinstance(question, str) or not question.strip():
            read.lines_skipped += 1
            continue
        question = question.strip()
        key = _question_key(question)
        if key in seen:
            continue
        seen.add(key)
        read.questions.append(question)
    return read


def _section(
    keys: list[tuple[str, ...]],
    counts: Counter[tuple[str, ...]],
    variants: dict[tuple[str, ...], Counter[str]],
    min_distinct: int,
    top: int | None,
) -> GapSection:
    above = [(key, counts[key]) for key in keys if counts[key] >= min_distinct]
    # Rank by demand, then by the displayed wording for a stable order.
    above.sort(key=lambda kn: (-kn[1], _display(variants[kn[0]])))
    suppressed = sum(1 for key in keys if counts[key] < min_distinct)
    total = len(above)
    if top is not None:
        above = above[:top]
    return GapSection(
        listed=tuple(
            GapConcept(term=_display(variants[key]), questions=n) for key, n in above
        ),
        total=total,
        suppressed=suppressed,
    )


def _display(seen: Counter[str]) -> str:
    """The wording to show for a concept: the most-used surface form, ties
    broken alphabetically so the report is deterministic."""
    return min(seen.items(), key=lambda tv: (-tv[1], tv[0]))[0]


def corpus_gap_report(
    log_path: Path,
    snapshot_path: Path,
    min_distinct: int = DEFAULT_MIN_DISTINCT,
    top: int | None = None,
) -> GapReport:
    """Replay the ask-log against the current corpus and aggregate the concepts
    that still make Pistis abstain. Re-asking (rather than trusting the logged
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
    # demand is never split. Which SECTION it lands in is decided separately,
    # by where it mostly showed up (see below) — splitting the count by section
    # would re-introduce the fragmentation this report exists to avoid.
    counts: Counter[tuple[str, ...]] = Counter()
    by_bucket: dict[str, Counter[tuple[str, ...]]] = {
        "thin": Counter(),
        "no_overlap": Counter(),
    }
    variants: dict[tuple[str, ...], Counter[str]] = defaultdict(Counter)
    answered = routed = refused = 0
    with_concepts = without_concepts = no_overlap_refusals = 0

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
        bucket = "no_overlap" if report.stage == "no_source" else "thin"
        if bucket == "no_overlap":
            no_overlap_refusals += 1
        # One vote per question per concept, even if the question spelled the
        # concept two ways.
        reportable: dict[tuple[str, ...], str] = {}
        for raw in report.uncovered_terms:
            if not _is_concept(raw):
                continue
            key = _concept_key(raw)
            if not key:
                continue
            reportable.setdefault(key, raw)
        if reportable:
            with_concepts += 1
        else:
            without_concepts += 1
        for key, raw in reportable.items():
            counts[key] += 1
            by_bucket[bucket][key] += 1
            variants[key][raw] += 1

    # Each concept belongs to the section it mostly came from. A tie goes to
    # NO OVERLAP: the conservative call is to quarantine a concept for scope
    # triage rather than present it as a corpus-expansion candidate.
    thin_keys = [k for k in counts if by_bucket["thin"][k] > by_bucket["no_overlap"][k]]
    no_overlap_keys = [k for k in counts if k not in set(thin_keys)]

    newest = max((p.fetched_at for p in passages), default="")
    return GapReport(
        log_path=str(log_path),
        snapshot_path=str(snapshot_path),
        snapshot_fetched=newest,
        log_found=read.found,
        lines_skipped=read.lines_skipped,
        questions_analyzed=len(read.questions),
        answered=answered,
        routed=routed,
        refused=refused,
        refusals_with_concepts=with_concepts,
        refusals_without_concepts=without_concepts,
        refusals_no_overlap=no_overlap_refusals,
        min_distinct=min_distinct,
        thin_coverage=_section(thin_keys, counts, variants, min_distinct, top),
        no_overlap=_section(no_overlap_keys, counts, variants, min_distinct, top),
    )


def _format_section(section: GapSection, heading: str, note: str) -> list[str]:
    lines = ["", heading, note]
    if section.listed:
        width = max(len(c.term) for c in section.listed)
        for c in section.listed:
            plural = "question" if c.questions == 1 else "questions"
            lines.append(f"  {c.term.ljust(width)}  {c.questions} {plural}")
        hidden = section.total - len(section.listed)
        if hidden > 0:
            # Never let the --top cap pass itself off as the whole backlog.
            lines.append(f"  ... and {hidden} more (raise --top to list them)")
    elif section.total:
        # Above the floor but nothing listed: --top 0.
        lines.append(f"  (none listed — raise --top to list {section.total})")
    else:
        lines.append("  (none above the floor)")
    if section.suppressed:
        lines.append(
            f"  [{section.suppressed} below the floor, withheld for privacy]"
        )
    return lines


def _format(r: GapReport) -> str:
    lines = [
        "Pistis corpus-gap report",
        "========================",
        f"Ask-log                   : {r.log_path}"
        + ("" if r.log_found else "   *** NOT FOUND — nothing was analysed ***"),
        f"Corpus snapshot           : {r.snapshot_path}",
        f"Snapshot fetched          : {r.snapshot_fetched or 'unknown'}",
        f"Log lines skipped         : {r.lines_skipped}  (blank, unparseable, or no question)",
        "",
        f"Distinct questions        : {r.questions_analyzed}",
        f"  answered                : {r.answered}",
        f"  routed (advice boundary): {r.routed}",
        f"  refused                 : {r.refused}",
        f"    naming a concept      : {r.refusals_with_concepts}",
        f"    naming none           : {r.refusals_without_concepts}",
        f"    with no corpus overlap: {r.refusals_no_overlap}",
        f"Reporting floor           : a concept must appear in >= {r.min_distinct} distinct questions",
    ]
    lines += _format_section(
        r.thin_coverage,
        "THIN COVERAGE — sources matched but fell short (corpus-expansion candidates):",
        "  the corpus is on these topics and short of material.",
    )
    lines += _format_section(
        r.no_overlap,
        "NO OVERLAP — nothing in the corpus matched at all (triage for scope first):",
        "  a zero-hit refusal names every content word, and most are simply\n"
        "  out of scope for a UK personal-finance corpus. Do not add blindly.",
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pistis corpus-gap report")
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument(
        "--min-distinct",
        type=int,
        default=DEFAULT_MIN_DISTINCT,
        help="privacy floor: min distinct questions a concept must appear in",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=25,
        help="max concepts to LIST per section (the full count is always reported);"
        " use --all for no cap",
    )
    parser.add_argument(
        "--all", action="store_true", help="list every concept above the floor (no --top cap)"
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)
    if args.top < 0:
        parser.error("--top must be non-negative (or use --all for no cap)")

    try:
        report = corpus_gap_report(
            args.log,
            args.snapshot,
            min_distinct=args.min_distinct,
            top=None if args.all else args.top,
        )
    except (FileNotFoundError, IsADirectoryError, json.JSONDecodeError) as exc:
        # A missing or unreadable snapshot is the operator's most likely
        # mistake on a fresh clone (the snapshot is gitignored). Say what to do
        # instead of raising a traceback at them.
        parser.exit(
            EXIT_NO_SNAPSHOT,
            f"Cannot read the corpus snapshot {args.snapshot}: {exc}\n"
            "Build one with:  python -m pistis.corpus.refresh\n",
        )

    print(json.dumps(asdict(report), indent=2) if args.json else _format(report))
    return EXIT_OK if report.log_found else EXIT_NO_LOG


if __name__ == "__main__":
    raise SystemExit(main())
