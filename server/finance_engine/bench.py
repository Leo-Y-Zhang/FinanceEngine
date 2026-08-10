"""Answerability benchmark — measuring the promise instead of asserting it.

``finance_engine.eval`` proves the faithfulness promise on 21 golden questions: every
claim grounded, every citation dated. That is necessary but it is not a
measurement of the *gate*, and the gate is where this product's central claim
lives. Two numbers were missing:

  * **How often does FinanceEngine answer something it should have refused?** This is
    the failure that matters. A confidently-cited answer to a question the corpus
    cannot support is exactly the harm the whole architecture exists to prevent.
  * **How often does it refuse something it could have answered?** The cost of
    the first guarantee, which has to be known rather than hoped small.

A single "accuracy" figure hides both, because it averages a serious failure
against a mild one. So this module never reports one. It reports the two rates
separately, under an explicit and arguable cost model, broken down by how hard
each question was.

    python -m finance_engine.bench --validate     # check the LABELS, not the engine
    python -m finance_engine.bench                # score the engine
    python -m finance_engine.bench --json         # machine-readable record
    python -m finance_engine.bench --by-difficulty

On the labels: none of them come from FinanceEngine's output. See
``tests/fixtures/bench_build.py`` for the protocol and its stated limits, and run
``--validate`` to confirm the dataset still describes the corpus it was written
against.
"""

from __future__ import annotations

import argparse
import json
import re as _re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from finance_engine.corpus.store import load_snapshot
from finance_engine.engine.answer import Engine
from finance_engine.index.bm25 import Bm25Index
from finance_engine.models import Passage

_FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
DEFAULT_BENCH = _FIXTURES / "bench.json"
_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SNAPSHOT = _ROOT / "data" / "corpus" / "snapshot.json"

# Response.kind -> the benchmark's label vocabulary.
_KIND_TO_STATE = {"answer": "answer", "abstain": "abstain", "routing": "route"}

# How much worse is answering-when-you-should-not than refusing-when-you-could?
# This is a JUDGEMENT, stated so it can be argued with rather than buried in a
# single score. 5x is the working figure: an unsupported answer about someone's
# money can be acted on and is presented with citations that make it credible,
# whereas a false refusal is visible, self-explaining (the refusal report names
# what was missing) and merely unhelpful. Change it here and the chosen operating
# point moves with it — that is the point of writing it down.
FALSE_ANSWER_WEIGHT = 5.0

# A concept counts as COVERED when a document is titled for it, or appears in at
# least this many DISTINCT passages of one document. Below that, a mention is
# incidental — see `_is_about` for the measurement this number came from.
_ABOUTNESS_PASSAGES = 3

# The vocabulary `bench_build.py` documents. A typo here would silently open a
# new difficulty bucket that quietly holds one question, so it is checked.
_DIFFICULTIES = {"plain", "paraphrase", "abbreviation", "near_miss"}
_EXPECTATIONS = {"answer", "abstain", "route"}


def _word_rx(term: str) -> _re.Pattern[str]:
    """Match ``term`` at a word START, letting the rest of the word differ.

    Anchored at the start deliberately: the naive substring test this replaced
    matched "roth" inside "growth", and that anchor is what stops it.

    But demanding the exact surface form was its own defect. Real prose says
    "bills" and "categories" where a label reasonably says "bill" and "categor",
    and three labels that were perfectly true got reported as broken. False
    alarms are not free here — a validator that cries wolf every time the corpus
    grows is one its operator learns to skip, which costs exactly the protection
    it exists to provide. Word-start anchoring keeps the "growth" class of error
    out while letting morphology through.
    """
    return _re.compile(r"\b" + _re.escape(term) + r"\w*")


@dataclass(frozen=True)
class Outcome:
    id: str
    question: str
    expected: str
    actual: str
    difficulty: str
    grounded: bool | None = None  # None when the response was not an answer


@dataclass
class BenchReport:
    total: int = 0
    # The two failures that matter, never averaged together.
    should_answer: int = 0
    false_refusals: int = 0          # should_answer but refused
    should_not_answer: int = 0       # abstain + route labels
    false_answers: int = 0           # answered anyway — the dangerous failure
    false_answers_ungrounded: int = 0  # of those, the ones faithfulness also caught
    # Routing is a third state, not a kind of refusal.
    should_route: int = 0
    routed_correctly: int = 0
    # Faithfulness of whatever it did choose to answer.
    answers_given: int = 0
    answers_fully_grounded: int = 0
    # Derived
    false_answer_rate: float = 0.0
    false_refusal_rate: float = 0.0
    routing_recall: float = 0.0
    # None, not 1.0, when nothing was answered: a rate over zero answers is not a
    # perfect score, it is an absent measurement, and this file exists to stop
    # unearned numbers being printed.
    grounded_rate: float | None = None
    weighted_cost: float = 0.0
    confusion: dict[str, int] = field(default_factory=dict)
    by_difficulty: dict[str, dict[str, int]] = field(default_factory=dict)
    failures: tuple[Outcome, ...] = ()
    # Provenance — the report says what it was measured against, so a reader can
    # tell a result on today's corpus from one on a stale snapshot.
    snapshot: str = ""
    snapshot_fetched: str = ""
    bench_file: str = ""
    labels_valid: bool = False


def load_bench(path: Path = DEFAULT_BENCH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_labels(bench: dict, passages: list[Passage]) -> list[str]:
    """Check the DATASET against the corpus. Returns a list of problems.

    This is the guard that stops the benchmark quietly becoming fiction. An
    ``answer`` label claims a specific document supports the question, so that
    document must exist and must contain the probe term. An ``abstain`` label
    claims the corpus is silent on a concept, so that concept must appear
    nowhere. When the corpus changes — and it does; it grew 46 -> 53 documents in
    a day — a label that no longer holds shows up here instead of silently
    scoring the engine against something untrue.
    """
    problems: list[str] = []
    doc_body: dict[str, list[str]] = {}
    doc_title: dict[str, str] = {}
    for p in passages:
        doc_body.setdefault(p.doc_id, []).append(p.text.lower())
        doc_title[p.doc_id] = p.doc_title.lower()
    doc_text = {doc: "\n".join(parts) for doc, parts in doc_body.items()}

    def _is_about(concept: str) -> tuple[bool, str]:
        """Is any document ABOUT this concept, rather than mentioning it once?

        This distinction was learned the hard way. A naive substring test called
        24 of the first 35 abstain labels invalid, and it was wrong twice over.
        It matched "roth" inside "growth"; and it counted a single passing mention
        as coverage — the capital-gains page lists "cryptocurrency" once among
        chargeable assets, which does not make the corpus able to say how crypto
        is taxed. Measured over the 53-document corpus, incidental terms occupy
        1-2 passages and never reach a title, while the one genuinely covered case
        (FSCS) held a title AND ran across 5 passages.

        Spread is what separates them, so spread is what is counted: DISTINCT
        passages, not total mentions. Counting mentions instead — which this did
        at first, contradicting both its own name and this docstring — reads three
        repetitions inside a single sentence-cluster as a subject. That is not a
        hypothetical: it flagged "visa" as covered because one passage about
        *visa scams* says the word three times, and the corpus cannot tell anyone
        how to apply for a spouse visa.
        """
        rx = _word_rx(concept)
        best_doc, best_n = "", 0
        for doc, parts in doc_body.items():
            if rx.search(doc_title[doc]):
                return True, f"{doc} — it is in the document's title"
            n = sum(1 for text in parts if rx.search(text))
            if n > best_n:
                best_doc, best_n = doc, n
        if best_n >= _ABOUTNESS_PASSAGES:
            return True, f"{best_doc} — {best_n} passages, so it is a subject not an aside"
        return False, ""

    questions = bench.get("questions")
    if not isinstance(questions, list) or not questions:
        # An empty dataset would otherwise validate perfectly and then score a
        # flawless zero-question benchmark — a clean bill of health from nothing.
        return ["the dataset holds no questions — there is nothing to measure"]

    seen: set[str] = set()
    seen_text: dict[str, str] = {}
    for q in questions:
        qid = q.get("id", "<missing id>")
        if qid in seen:
            problems.append(f"{qid}: duplicate id")
        seen.add(qid)

        text = (q.get("question") or "").strip()
        if not text:
            problems.append(f"{qid}: no question text")
        elif text.lower() in seen_text:
            problems.append(f"{qid}: same question as {seen_text[text.lower()]} — it would be "
                            "scored twice, over-weighting whatever it happens to exercise")
        else:
            seen_text[text.lower()] = qid

        difficulty = q.get("difficulty", "plain")
        if difficulty not in _DIFFICULTIES:
            problems.append(f"{qid}: unknown difficulty {difficulty!r} (not one of "
                            f"{', '.join(sorted(_DIFFICULTIES))})")

        expect = q.get("expect")
        if expect not in _EXPECTATIONS:
            problems.append(f"{qid}: unknown expect {expect!r}")
            continue

        if expect == "answer":
            docs = q.get("supported_by") or []
            if not docs:
                problems.append(f"{qid}: expect=answer with no supported_by provenance")
            probe = (q.get("probe") or "").lower()
            if not probe:
                problems.append(f"{qid}: expect=answer with no probe term")
            for doc in docs:
                if doc not in doc_text:
                    problems.append(f"{qid}: supported_by names {doc!r}, absent from the corpus")
                elif probe and not _word_rx(probe).search(
                    doc_text[doc] + " " + doc_title[doc]
                ):
                    problems.append(
                        f"{qid}: probe {probe!r} does not appear in {doc!r} — the label claims "
                        "support this document does not provide"
                    )
        elif expect == "abstain":
            concept = (q.get("absent_concept") or "").lower()
            if not concept:
                problems.append(f"{qid}: expect=abstain with no absent_concept")
            else:
                covered, where = _is_about(concept)
                if covered:
                    problems.append(
                        f"{qid}: the corpus IS about {concept!r} ({where}). The label is no longer "
                        "true, so this question may now be answerable"
                    )
        else:  # route — a property of the question's form, so it needs no corpus
            if not (q.get("trigger") or "").strip():
                problems.append(
                    f"{qid}: expect=route with no trigger recorded — the label has to say which "
                    "part of the question's form makes it a request for advice"
                )
    return problems


def run_bench(
    snapshot_path: Path,
    bench: dict,
    passages: list[Passage] | None = None,
    *,
    bench_file: Path | None = None,
    labels_valid: bool = False,
) -> BenchReport:
    # `passages` is accepted already-loaded so the CLI does not parse and index a
    # half-megabyte snapshot twice, once to validate the labels and again to score.
    if passages is None:
        passages = load_snapshot(Path(snapshot_path))
    engine = Engine(Bm25Index(passages))
    r = BenchReport(
        total=len(bench["questions"]),
        snapshot=str(snapshot_path),
        snapshot_fetched=max((p.fetched_at for p in passages), default=""),
        bench_file=str(bench_file) if bench_file else "",
        labels_valid=labels_valid,
    )
    failures: list[Outcome] = []

    for q in bench["questions"]:
        expected = q["expect"]
        difficulty = q.get("difficulty", "plain")
        response = engine.ask(q["question"])
        actual = _KIND_TO_STATE.get(getattr(response, "kind", ""), "unknown")

        grounded: bool | None = None
        if actual == "answer":
            r.answers_given += 1
            report = getattr(response, "trust_report", None)
            grounded = bool(report.all_grounded) if report else False
            r.answers_fully_grounded += int(grounded)

        r.confusion[f"{expected}->{actual}"] = r.confusion.get(f"{expected}->{actual}", 0) + 1
        bucket = r.by_difficulty.setdefault(
            difficulty, {"n": 0, "false_answers": 0, "false_refusals": 0, "correct": 0}
        )
        bucket["n"] += 1

        if expected == "answer":
            r.should_answer += 1
            if actual == "answer":
                bucket["correct"] += 1
            else:
                r.false_refusals += 1
                bucket["false_refusals"] += 1
        else:
            # abstain and route labels share one property: answering is wrong.
            r.should_not_answer += 1
            if expected == "route":
                r.should_route += 1
                if actual == "route":
                    r.routed_correctly += 1
            if actual == "answer":
                r.false_answers += 1
                bucket["false_answers"] += 1
                if not grounded:
                    r.false_answers_ungrounded += 1
            elif actual == expected:
                bucket["correct"] += 1

        if actual != expected:
            failures.append(Outcome(q["id"], q["question"], expected, actual, difficulty, grounded))

    r.false_answer_rate = r.false_answers / r.should_not_answer if r.should_not_answer else 0.0
    r.false_refusal_rate = r.false_refusals / r.should_answer if r.should_answer else 0.0
    r.routing_recall = r.routed_correctly / r.should_route if r.should_route else 0.0
    r.grounded_rate = r.answers_fully_grounded / r.answers_given if r.answers_given else None
    r.weighted_cost = FALSE_ANSWER_WEIGHT * r.false_answers + r.false_refusals
    r.failures = tuple(failures)
    return r


def format_report(r: BenchReport, by_difficulty: bool = False) -> str:
    grounded = (
        f"{r.answers_fully_grounded}/{r.answers_given} ({r.grounded_rate:.1%})"
        if r.grounded_rate is not None
        else "n/a - it answered nothing, so there is no rate to report"
    )
    lines = [
        "FinanceEngine answerability benchmark",
        "=" * len("FinanceEngine answerability benchmark"),
        f"Questions                 : {r.total}",
        f"Snapshot                  : {r.snapshot or 'unknown'}",
        f"Snapshot fetched          : {r.snapshot_fetched or 'unknown'}",
        "",
        "THE FAILURE THAT MATTERS — answered something it should not have:",
        (
            f"  false answers           : {r.false_answers} of {r.should_not_answer}"
            f"  ({r.false_answer_rate:.1%})"
        ),
        (
            f"  of those, ungrounded    : {r.false_answers_ungrounded}"
            "   (the faithfulness verifier is the second line of defence)"
        ),
        "",
        "THE COST OF THAT GUARANTEE — refused something it could have answered:",
        (
            f"  false refusals          : {r.false_refusals} of {r.should_answer}"
            f"  ({r.false_refusal_rate:.1%})"
        ),
        "",
        (
            f"Advice-boundary routing   : {r.routed_correctly}/{r.should_route}"
            f" ({r.routing_recall:.1%})"
        ),
        f"Answers fully grounded    : {grounded}",
        "",
        (
            f"Weighted cost             : {r.weighted_cost:.1f}"
            f"   (a false answer counted {FALSE_ANSWER_WEIGHT:g}x a false refusal)"
        ),
        "",
        "Confusion (expected -> actual):",
    ]
    for key in sorted(r.confusion):
        lines.append(f"  {key:24} {r.confusion[key]}")
    if by_difficulty:
        lines += ["", "By difficulty (near_miss is the adversarial class):"]
        for name in sorted(r.by_difficulty):
            b = r.by_difficulty[name]
            lines.append(
                f"  {name:13} n={b['n']:3}  correct={b['correct']:3}"
                f"  false_answers={b['false_answers']:3}  false_refusals={b['false_refusals']:3}"
            )
    if r.failures:
        lines += ["", f"Disagreements with the labels ({len(r.failures)}):"]
        for f in r.failures:
            flag = "  <-- FALSE ANSWER" if f.actual == "answer" and f.expected != "answer" else ""
            lines.append(f"  [{f.expected:7} -> {f.actual:7}] {f.id:34} {f.question[:44]}{flag}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="FinanceEngine answerability benchmark")
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--bench", type=Path, default=DEFAULT_BENCH)
    parser.add_argument("--validate", action="store_true",
                        help="check the dataset's labels against the corpus and stop")
    parser.add_argument("--by-difficulty", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if not Path(args.snapshot).exists():
        parser.exit(3, f"No corpus snapshot at {args.snapshot}.\n"
                       "Build one with:  python -m finance_engine.corpus.refresh\n")
    try:
        bench = load_bench(args.bench)
    except FileNotFoundError:
        parser.exit(3, f"No benchmark dataset at {args.bench}.\n"
                       "Build one with:  python tests/fixtures/bench_build.py\n")
    except json.JSONDecodeError as exc:
        # A truncated dataset must not be scored as though it were the whole set.
        parser.exit(3, f"The benchmark dataset at {args.bench} is not valid JSON ({exc}).\n")
    passages = load_snapshot(Path(args.snapshot))

    problems = validate_labels(bench, passages)
    if args.validate:
        if args.json:
            print(json.dumps({"problems": problems, "valid": not problems}, indent=2))
        elif problems:
            print(f"{len(problems)} label problem(s) — the dataset no longer describes the corpus:")
            for p in problems:
                print(f"  {p}")
        else:
            print(f"All {len(bench['questions'])} labels check out against the corpus.")
        return 1 if problems else 0

    if problems:
        # Refuse to publish a score against labels known to be wrong. Scoring
        # anyway would be exactly the kind of unearned number this file exists to
        # avoid producing.
        parser.exit(2, f"Refusing to score: {len(problems)} label problem(s). "
                       "Run --validate to see them.\n")

    report = run_bench(
        args.snapshot, bench, passages, bench_file=args.bench, labels_valid=True
    )
    print(json.dumps(asdict(report), indent=2, default=list) if args.json
          else format_report(report, by_difficulty=args.by_difficulty))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
