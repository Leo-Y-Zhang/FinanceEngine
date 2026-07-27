"""Corpus-gap report — the refusals turned into a roadmap.

Reads the local ask-log, replays each question through the engine, and
aggregates the concepts that make Pistis abstain — the query terms no trusted
source covers (the same ``uncovered_terms`` diagnostic the refusal shows the
user). The result is a keyless, privacy-safe backlog of what to add to the
corpus next: the money questions people ask that Pistis cannot yet answer.
Refusal is a feature; this makes the refusals *actionable*.

Privacy by construction:
  * Aggregate-only. Raw questions never leave the function; the output is
    concept frequencies, nothing else.
  * A k-anonymity floor. A concept is reported only when it appears across at
    least ``min_distinct`` DISTINCT questions, so no single question's wording
    (e.g. a rare proper noun someone typed) is ever surfaced. Raise the floor
    before any multi-user deployment.
  * Bare numbers/amounts are dropped — they are not concepts to add to the
    corpus and could be incidental identifiers.
  * Deterministic and offline — no network, no keys.

    python -m pistis.gaps                 # human-readable report
    python -m pistis.gaps --json          # machine-readable record
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from pistis.corpus.store import load_snapshot
from pistis.engine.answer import Engine
from pistis.index.bm25 import Bm25Index
from pistis.models import Abstention

# Paths mirror pistis.api.app (kept local so this CLI does not import FastAPI).
_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG = _ROOT / "logs" / "ask.jsonl"
DEFAULT_SNAPSHOT = _ROOT / "data" / "corpus" / "snapshot.json"

# Privacy floor: a concept must appear across at least this many DISTINCT
# questions to be reported. Conservative default for a small pre-launch log;
# raise it before exposing the report to more than one person's questions.
DEFAULT_MIN_DISTINCT = 2


def _read_questions(log_path: Path) -> list[str]:
    """Distinct question texts from the JSONL ask-log, in first-seen order.
    Best-effort: blank lines, unparseable lines, and entries without a question
    are skipped rather than raising (the same posture as the retention pass)."""
    if not log_path.exists():
        return []
    seen: set[str] = set()
    out: list[str] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            question = str(record["question"]).strip()
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            continue
        if not question:
            continue
        key = question.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(question)
    return out


def _is_concept(term: str) -> bool:
    """A reportable concept has alphabetic content — a bare number or amount is
    not something to add to the corpus and could be an incidental identifier."""
    return any(c.isalpha() for c in term)


@dataclass(frozen=True)
class GapConcept:
    term: str
    questions: int  # distinct questions in which this uncovered concept appeared


@dataclass(frozen=True)
class GapReport:
    questions_analyzed: int
    refusals_with_gaps: int
    min_distinct: int
    concepts: tuple[GapConcept, ...]  # above the floor, ranked; may be capped by ``top``
    total_gap_concepts: int           # distinct concepts above the floor (pre-cap)
    suppressed_concepts: int          # distinct concepts seen but below the floor


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

    ``top`` caps how many concepts are LISTED (None = no cap). The cap is never
    silent: ``total_gap_concepts`` always carries the full pre-cap count, so a
    truncated listing cannot be mistaken for the whole backlog."""
    engine = Engine(Bm25Index(load_snapshot(Path(snapshot_path))))
    questions = _read_questions(Path(log_path))

    counts: Counter[str] = Counter()
    refusals_with_gaps = 0
    for question in questions:
        response = engine.ask(question)
        if not isinstance(response, Abstention) or response.report is None:
            continue
        terms = {t for t in response.report.uncovered_terms if _is_concept(t)}
        if terms:
            refusals_with_gaps += 1
        for term in terms:
            counts[term] += 1

    above = [(t, n) for t, n in counts.items() if n >= min_distinct]
    above.sort(key=lambda tn: (-tn[1], tn[0]))
    suppressed = sum(1 for n in counts.values() if n < min_distinct)
    total_above = len(above)
    if top is not None:
        if top < 0:
            raise ValueError("top must be non-negative (or None for no cap)")
        above = above[:top]

    return GapReport(
        questions_analyzed=len(questions),
        refusals_with_gaps=refusals_with_gaps,
        min_distinct=min_distinct,
        concepts=tuple(GapConcept(term=t, questions=n) for t, n in above),
        total_gap_concepts=total_above,
        suppressed_concepts=suppressed,
    )


def _format(r: GapReport) -> str:
    lines = [
        "Pistis corpus-gap report",
        "========================",
        f"Questions analysed        : {r.questions_analyzed}",
        f"Refusals with a gap       : {r.refusals_with_gaps}",
        f"Reporting floor           : a concept must appear in >= {r.min_distinct} distinct questions",
        f"Concepts above the floor  : {r.total_gap_concepts}",
        f"Concepts below the floor  : {r.suppressed_concepts}  (withheld for privacy)",
        "",
        "Most-requested uncovered concepts (candidates to add to the corpus):",
    ]
    if r.concepts:
        width = max(len(c.term) for c in r.concepts)
        for c in r.concepts:
            plural = "question" if c.questions == 1 else "questions"
            lines.append(f"  {c.term.ljust(width)}  {c.questions} {plural}")
        hidden = r.total_gap_concepts - len(r.concepts)
        if hidden > 0:
            # Never let the --top cap pass itself off as the whole backlog.
            lines.append(f"  ... and {hidden} more (raise --top to list them)")
    elif r.total_gap_concepts:
        # Above the floor but nothing listed: --top 0.
        lines.append(f"  (none listed — raise --top to list {r.total_gap_concepts})")
    else:
        lines.append("  (none above the floor)")
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
        help="max concepts to LIST (the full count is always reported); use --all for no cap",
    )
    parser.add_argument(
        "--all", action="store_true", help="list every concept above the floor (no --top cap)"
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)
    if args.top < 0:
        parser.error("--top must be non-negative (or use --all for no cap)")

    report = corpus_gap_report(
        args.log,
        args.snapshot,
        min_distinct=args.min_distinct,
        top=None if args.all else args.top,
    )
    print(json.dumps(asdict(report), indent=2) if args.json else _format(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
