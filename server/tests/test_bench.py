"""Answerability benchmark — the labels, the arithmetic, and the refusals to score.

The benchmark's whole value is that its labels do not come from the engine. So
most of what is worth testing here is the *validator*: the thing that stops the
dataset quietly becoming fiction as the corpus grows. Each test pins a property
that a real run got wrong before it was fixed, and every "is absent" assertion
carries a positive control so it cannot pass vacuously.
"""

import json
from pathlib import Path

import pytest

from finance_answer_engine.bench import (
    FALSE_ANSWER_WEIGHT,
    BenchReport,
    format_report,
    load_bench,
    main,
    run_bench,
    validate_labels,
)
from finance_answer_engine.models import Passage, SourceOrg

FIXTURES = Path(__file__).parent / "fixtures"
SNAPSHOT = FIXTURES / "snapshot.json"
BENCH = FIXTURES / "bench.json"


def _p(pid: str, doc_id: str, text: str, title: str = "A document") -> Passage:
    return Passage(
        id=pid,
        doc_id=doc_id,
        text=text,
        doc_title=title,
        org=SourceOrg.GOVUK,
        url="https://www.gov.uk/example",
        fetched_at="2026-07-27",
    )


def _q(**kw) -> dict:
    q = {"id": "q1", "question": "A question?", "difficulty": "plain"}
    q.update(kw)
    return q


def _bench(*questions) -> dict:
    return {"schema_version": 1, "questions": list(questions)}


# ── the probe check: does the cited document really support the label? ────────


def test_probe_matches_a_longer_form_of_the_same_word():
    # "bills" in the source, "bill" in the label. Three true labels were reported
    # broken over exactly this, and false alarms teach an operator to ignore the
    # validator — which costs the protection it exists to give.
    passages = [_p("d#1", "d", "Help with your energy bills and council tax.")]
    ok = _q(expect="answer", supported_by=["d"], probe="bill")
    assert validate_labels(_bench(ok), passages) == []

    # positive control: a probe that genuinely is not there still fails
    missing = _q(expect="answer", supported_by=["d"], probe="annuity")
    assert len(validate_labels(_bench(missing), passages)) == 1


def test_probe_cannot_match_inside_a_word():
    # The anchor that survived: a naive substring test matched "roth" inside
    # "growth" and wrongly validated a Roth-IRA label against a UK corpus.
    passages = [_p("d#1", "d", "Your savings show steady growth over time.")]
    problems = validate_labels(
        _bench(_q(expect="answer", supported_by=["d"], probe="roth")), passages
    )
    assert len(problems) == 1
    assert "roth" in problems[0]


def test_answer_label_naming_a_document_the_corpus_lacks_is_flagged():
    passages = [_p("d#1", "d", "Income Tax rates.")]
    problems = validate_labels(
        _bench(_q(expect="answer", supported_by=["gone"], probe="tax")), passages
    )
    assert len(problems) == 1
    assert "absent from the corpus" in problems[0]


def test_answer_label_without_provenance_is_flagged():
    passages = [_p("d#1", "d", "Income Tax rates.")]
    problems = validate_labels(_bench(_q(expect="answer")), passages)
    assert any("supported_by" in p for p in problems)
    assert any("probe" in p for p in problems)


# ── the abstain check: is the corpus really silent on this? ───────────────────


def test_repetition_inside_one_passage_is_not_coverage():
    # The visa case. One passage about visa SCAMS says the word three times; that
    # does not make the corpus able to say how to apply for a spouse visa.
    # Counting mentions called this covered, which is why spread is counted now.
    passages = [_p("d#1", "d", "Report visa scams. Never pay for a visa in cash. Visa fraud is common.")]
    assert validate_labels(_bench(_q(expect="abstain", absent_concept="visa")), passages) == []


def test_a_concept_spread_across_passages_is_coverage():
    # Positive control for the test above: the same three mentions, spread out,
    # ARE a subject, and the stale abstain label must be flagged.
    passages = [
        _p("d#1", "d", "An annuity converts your pension pot into an income."),
        _p("d#2", "d", "You can shop around for an annuity."),
        _p("d#3", "d", "An annuity is paid for life."),
    ]
    problems = validate_labels(
        _bench(_q(expect="abstain", absent_concept="annuity")), passages
    )
    assert len(problems) == 1
    assert "the corpus IS about" in problems[0]


def test_a_titled_document_is_coverage_on_its_own():
    passages = [_p("d#1", "d", "Some text.", title="Cryptoassets and tax")]
    problems = validate_labels(
        _bench(_q(expect="abstain", absent_concept="cryptoasset")), passages
    )
    assert len(problems) == 1
    assert "title" in problems[0]


def test_abstain_label_without_a_named_concept_is_flagged():
    passages = [_p("d#1", "d", "Some text.")]
    problems = validate_labels(_bench(_q(expect="abstain")), passages)
    assert any("absent_concept" in p for p in problems)


# ── dataset hygiene ──────────────────────────────────────────────────────────


def test_an_empty_dataset_is_refused_rather_than_validated():
    # Otherwise a zero-question benchmark validates perfectly and then scores a
    # flawless nothing — a clean bill of health from an empty file.
    passages = [_p("d#1", "d", "text")]
    assert validate_labels({"questions": []}, passages) != []
    assert validate_labels({}, passages) != []


def test_duplicate_ids_and_repeated_questions_are_flagged():
    passages = [_p("d#1", "d", "text")]
    dupe_id = _bench(
        _q(id="same", expect="route", trigger="t", question="Which should I pick?"),
        _q(id="same", expect="route", trigger="t", question="Something else?"),
    )
    assert any("duplicate id" in p for p in validate_labels(dupe_id, passages))

    dupe_text = _bench(
        _q(id="a", expect="route", trigger="t", question="Which should I pick?"),
        _q(id="b", expect="route", trigger="t", question="which should i pick?"),
    )
    assert any("scored twice" in p for p in validate_labels(dupe_text, passages))


def test_unknown_expect_and_difficulty_are_flagged():
    passages = [_p("d#1", "d", "text")]
    assert any(
        "unknown expect" in p
        for p in validate_labels(_bench(_q(expect="maybe")), passages)
    )
    # A typo'd difficulty would silently open a bucket holding one question.
    assert any(
        "unknown difficulty" in p
        for p in validate_labels(
            _bench(_q(expect="route", trigger="t", difficulty="tricky")), passages
        )
    )


def test_route_label_must_record_its_trigger():
    passages = [_p("d#1", "d", "text")]
    problems = validate_labels(_bench(_q(expect="route")), passages)
    assert any("trigger" in p for p in problems)
    # positive control: with a trigger recorded, the label is fine
    assert validate_labels(_bench(_q(expect="route", trigger="which should I")), passages) == []


def test_a_question_without_text_is_flagged():
    passages = [_p("d#1", "d", "text")]
    problems = validate_labels(_bench(_q(expect="route", trigger="t", question="  ")), passages)
    assert any("no question text" in p for p in problems)


# ── the shipped dataset ──────────────────────────────────────────────────────


def test_shipped_dataset_is_exactly_what_the_build_script_produces():
    """A hand-edit to bench.json would bypass the documented labelling protocol."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "bench_build", FIXTURES / "bench_build.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.build() == load_bench(BENCH)


def test_shipped_dataset_is_internally_consistent():
    bench = load_bench(BENCH)
    questions = bench["questions"]
    counts = bench["counts"]
    assert counts["total"] == len(questions)
    assert len({q["id"] for q in questions}) == len(questions)
    for q in questions:
        assert q["expect"] in {"answer", "abstain", "route"}
        assert q["difficulty"] in {"plain", "paraphrase", "abbreviation", "near_miss"}
        if q["expect"] == "answer":
            assert q["supported_by"] and q["probe"]
        elif q["expect"] == "abstain":
            assert q["absent_concept"]
        else:
            assert q["trigger"]


def test_the_adversarial_class_is_actually_populated():
    # near_miss is the class the benchmark exists for — finance-shaped questions
    # adjacent to the corpus. A dataset without them measures nothing interesting.
    bench = load_bench(BENCH)
    near = [q for q in bench["questions"] if q["difficulty"] == "near_miss"]
    assert len(near) >= 20
    assert any(q["expect"] == "abstain" for q in near)


# ── scoring ──────────────────────────────────────────────────────────────────


def _mini_bench() -> dict:
    """Labels that are true of the FIXTURE corpus, derived from it, not the engine."""
    return _bench(
        {
            "id": "ans-isa", "question": "How much can I pay into an ISA each year?",
            "expect": "answer", "supported_by": ["isa-overview"], "probe": "isa",
            "difficulty": "plain",
        },
        {
            "id": "abs-crypto", "question": "How is cryptocurrency taxed?",
            "expect": "abstain", "absent_concept": "cryptocurrency",
            "difficulty": "near_miss",
        },
        {
            "id": "rte-which", "question": "Which ISA should I open?",
            "expect": "route", "trigger": "which should I", "difficulty": "plain",
        },
    )


def test_mini_bench_labels_hold_against_the_fixture_corpus():
    from finance_answer_engine.corpus.store import load_snapshot

    assert validate_labels(_mini_bench(), load_snapshot(SNAPSHOT)) == []


def test_scoring_arithmetic_holds_whatever_the_engine_does():
    """Engine-independent invariants — the accounting must never contradict itself."""
    r = run_bench(SNAPSHOT, _mini_bench())
    assert r.total == 3
    assert r.should_answer + r.should_not_answer == r.total
    assert sum(r.confusion.values()) == r.total
    assert sum(b["n"] for b in r.by_difficulty.values()) == r.total
    # the two failure counts are bounded by their own denominators
    assert 0 <= r.false_answers <= r.should_not_answer
    assert 0 <= r.false_refusals <= r.should_answer
    # "of those, ungrounded" really is a subset of the false answers
    assert 0 <= r.false_answers_ungrounded <= r.false_answers
    assert r.weighted_cost == FALSE_ANSWER_WEIGHT * r.false_answers + r.false_refusals
    assert all(f.actual != f.expected for f in r.failures)
    assert len(r.failures) == sum(
        n for key, n in r.confusion.items() for a, b in [key.split("->")] if a != b
    )


def test_report_carries_the_provenance_of_what_it_measured():
    # A score with no snapshot date cannot be told apart from one run on a stale
    # corpus — the same reason gaps.py prints its snapshot date.
    r = run_bench(SNAPSHOT, _mini_bench(), bench_file=BENCH, labels_valid=True)
    assert r.snapshot_fetched
    assert str(SNAPSHOT) == r.snapshot
    assert r.bench_file == str(BENCH)
    assert r.labels_valid is True
    assert r.snapshot_fetched in format_report(r)


def test_a_run_that_answers_nothing_reports_no_grounded_rate():
    # 0 of 0 grounded is not 100% — it is an absent measurement, and printing it
    # as a perfect score is exactly the unearned number this module exists to
    # avoid. Gibberish cannot be answered by an extractive gate, by construction.
    bench = _bench(
        {
            "id": "abs-gibberish", "question": "qwertyuiop zxcvbnm asdfghjkl?",
            "expect": "abstain", "absent_concept": "qwertyuiop", "difficulty": "plain",
        }
    )
    r = run_bench(SNAPSHOT, bench)
    assert r.answers_given == 0
    assert r.grounded_rate is None
    out = format_report(r)
    assert "100.0%" not in out
    assert "n/a" in out


def test_grounded_rate_is_reported_when_answers_exist():
    # Positive control for the test above.
    r = BenchReport(total=1, answers_given=2, answers_fully_grounded=2, grounded_rate=1.0)
    assert "2/2 (100.0%)" in format_report(r)


def test_report_never_prints_a_bare_average_of_the_two_failures():
    """The design commitment: one number would hide a serious failure inside a mild one."""
    r = run_bench(SNAPSHOT, _mini_bench())
    out = format_report(r, by_difficulty=True)
    assert "false answers" in out
    assert "false refusals" in out
    assert "accuracy" not in out.lower()


def test_passages_may_be_supplied_so_the_snapshot_is_parsed_once():
    from finance_answer_engine.corpus.store import load_snapshot

    passages = load_snapshot(SNAPSHOT)
    assert run_bench(SNAPSHOT, _mini_bench(), passages) == run_bench(SNAPSHOT, _mini_bench())


# ── CLI ──────────────────────────────────────────────────────────────────────


def _write(tmp_path: Path, bench: dict) -> Path:
    path = tmp_path / "mini.json"
    path.write_text(json.dumps(bench), encoding="utf-8")
    return path


def test_cli_validate_passes_on_a_consistent_dataset(tmp_path, capsys):
    code = main(["--snapshot", str(SNAPSHOT), "--bench", str(_write(tmp_path, _mini_bench())),
                 "--validate"])
    assert code == 0
    assert "check out" in capsys.readouterr().out


def test_cli_refuses_to_score_against_broken_labels(tmp_path, capsys):
    # Scoring anyway would publish a number measured against something untrue.
    broken = _bench(_q(expect="abstain", absent_concept="isa"))  # the fixture corpus IS about ISAs
    with pytest.raises(SystemExit) as exc:
        main(["--snapshot", str(SNAPSHOT), "--bench", str(_write(tmp_path, broken))])
    assert exc.value.code == 2
    assert "Refusing to score" in capsys.readouterr().err


def test_cli_validate_exits_nonzero_when_labels_are_broken(tmp_path, capsys):
    broken = _bench(_q(expect="abstain", absent_concept="isa"))
    code = main(["--snapshot", str(SNAPSHOT), "--bench", str(_write(tmp_path, broken)),
                 "--validate"])
    assert code == 1
    assert "label problem" in capsys.readouterr().out


def test_cli_scores_and_reports(tmp_path, capsys):
    code = main(["--snapshot", str(SNAPSHOT), "--bench", str(_write(tmp_path, _mini_bench())),
                 "--by-difficulty"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Finance Answer Engine answerability benchmark" in out
    assert "THE FAILURE THAT MATTERS" in out
    assert "By difficulty" in out


def test_cli_json_is_machine_readable(tmp_path, capsys):
    code = main(["--snapshot", str(SNAPSHOT), "--bench", str(_write(tmp_path, _mini_bench())),
                 "--json"])
    assert code == 0
    record = json.loads(capsys.readouterr().out)
    assert record["total"] == 3
    assert record["labels_valid"] is True
    assert record["snapshot_fetched"]


def test_cli_missing_snapshot_says_how_to_build_one(tmp_path):
    with pytest.raises(SystemExit) as exc:
        main(["--snapshot", str(tmp_path / "nope.json"), "--bench", str(BENCH)])
    assert exc.value.code == 3


def test_cli_missing_or_corrupt_dataset_does_not_traceback(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--snapshot", str(SNAPSHOT), "--bench", str(tmp_path / "absent.json")])
    assert exc.value.code == 3
    assert "bench_build.py" in capsys.readouterr().err

    truncated = tmp_path / "truncated.json"
    truncated.write_text('{"questions": [', encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        main(["--snapshot", str(SNAPSHOT), "--bench", str(truncated)])
    assert exc.value.code == 3
    assert "not valid JSON" in capsys.readouterr().err
