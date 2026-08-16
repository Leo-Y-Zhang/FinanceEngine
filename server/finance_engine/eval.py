"""Reproducible honesty evaluation — FinanceEngine proving its own promises.

Runs a golden question set through the engine over a snapshot and reports:

  * Faithfulness   — every asserted claim is grounded in its cited source
                     (grounded_rate target 1.0; unsupported target 0). The
                     product's core promise, quantified.
  * Citations      — every claim carries a dated https citation.
  * Answerability  — answer / abstain / route matches the expected label.

Deterministic and network-free over the committed fixture snapshot, so it runs
anywhere (and in the test suite). Point ``--snapshot`` at the live corpus to
evaluate production.

    python -m finance_engine.eval            # human-readable report over the fixtures
    python -m finance_engine.eval --json     # machine-readable record
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from finance_engine.corpus.store import load_snapshot
from finance_engine.engine.answer import Engine
from finance_engine.index.bm25 import Bm25Index

_FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
DEFAULT_SNAPSHOT = _FIXTURES / "snapshot.json"
DEFAULT_GOLDEN = _FIXTURES / "golden.json"

# Response.kind -> the golden set's state vocabulary.
_KIND_TO_STATE = {"answer": "answer", "abstain": "abstain", "routing": "route"}


@dataclass(frozen=True)
class EvalReport:
    questions: int
    answerability_correct: int
    answerability_accuracy: float
    total_claims: int
    grounded_claims: int
    unsupported_claims: int
    grounded_rate: float
    citations_complete: bool
    abstentions: int
    abstentions_explained: int
    passed: bool
    mismatches: tuple[str, ...]


def run_eval(snapshot_path: Path, golden_path: Path) -> EvalReport:
    engine = Engine(Bm25Index(load_snapshot(Path(snapshot_path))))
    golden = json.loads(Path(golden_path).read_text(encoding="utf-8"))["questions"]

    correct = 0
    total_claims = grounded = unsupported = 0
    abstentions = abstentions_explained = 0
    citations_complete = True
    mismatches: list[str] = []

    for item in golden:
        question, expect = item["question"], item["expect"]
        resp = engine.ask(question)
        state = _KIND_TO_STATE[resp.kind]
        if state == expect:
            correct += 1
        else:
            mismatches.append(f"{question!r}: expected {expect}, got {state}")

        if resp.kind == "abstain":
            # Symmetric with faithfulness: a refusal must explain itself, or the
            # 'refusal is a feature' promise is not actually being kept.
            abstentions += 1
            if resp.report is not None and resp.report.explanation.strip():
                abstentions_explained += 1

        if resp.kind == "answer":
            for claim in resp.claims:
                if not (claim.citation.url.startswith("https://") and claim.citation.fetched_at):
                    citations_complete = False
            # The trust report always accompanies an answer (engine invariant).
            for verdict in resp.trust_report.verdicts:
                total_claims += 1
                if verdict.verdict == "grounded":
                    grounded += 1
                elif verdict.verdict == "unsupported":
                    unsupported += 1

    n = len(golden)
    accuracy = correct / n if n else 0.0
    grounded_rate = grounded / total_claims if total_claims else 1.0
    passed = (
        # An empty golden set would otherwise satisfy every clause below and
        # report a flawless zero-question eval — a clean bill of health from
        # nothing. `bench.validate_labels` already refuses an empty dataset for
        # this reason; this is the gate CI runs, so it has to refuse one too.
        n > 0
        and correct == n
        and unsupported == 0
        and grounded == total_claims
        and citations_complete
        and abstentions_explained == abstentions
    )
    return EvalReport(
        questions=n,
        answerability_correct=correct,
        answerability_accuracy=accuracy,
        total_claims=total_claims,
        grounded_claims=grounded,
        unsupported_claims=unsupported,
        grounded_rate=grounded_rate,
        citations_complete=citations_complete,
        abstentions=abstentions,
        abstentions_explained=abstentions_explained,
        passed=passed,
        mismatches=tuple(mismatches),
    )


def _format(r: EvalReport) -> str:
    lines = [
        "FinanceEngine honesty eval",
        "=" * len("FinanceEngine honesty eval"),
        f"Golden questions       : {r.questions}",
        (
            f"Answerability accuracy : {r.answerability_correct}/{r.questions}"
            f" ({r.answerability_accuracy:.0%})"
        ),
        f"Claims asserted        : {r.total_claims}",
        f"Claims grounded        : {r.grounded_claims}/{r.total_claims} ({r.grounded_rate:.0%})",
        f"Unsupported claims     : {r.unsupported_claims}  (must be 0)",
        f"Citations complete     : {'yes' if r.citations_complete else 'NO'}",
        f"Refusals explained     : {r.abstentions_explained}/{r.abstentions}  (must be all)",
        f"RESULT                 : {'PASS' if r.passed else 'FAIL'}",
    ]
    if r.questions == 0:
        lines += [
            "",
            "The golden set holds no questions, so there is nothing to measure and",
            "every figure above is over an empty set. That is not a pass.",
        ]
    if r.mismatches:
        lines += ["", "Answerability mismatches:"]
        lines += [f"  - {m}" for m in r.mismatches]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="FinanceEngine honesty evaluation")
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    report = run_eval(args.snapshot, args.golden)
    print(json.dumps(asdict(report), indent=2) if args.json else _format(report))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
