"""Corpus-gap report — refusals aggregated into a keyless, privacy-safe backlog."""

import json
from pathlib import Path

from pistis.gaps import corpus_gap_report, main

FIXTURES = Path(__file__).parent / "fixtures"
SNAPSHOT = FIXTURES / "snapshot.json"


def _write_log(path, questions):
    lines = [
        json.dumps({"ts": 1784900000 + i, "question": q, "kind": "x"})
        for i, q in enumerate(questions)
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# passport appears in 3 distinct questions, weather in 2, solar/panels once each;
# the ISA questions answer / route and contribute no gap.
GAP_QUESTIONS = [
    "How do I renew my passport?",
    "Do I need a passport to travel abroad?",
    "Will my passport application be delayed?",
    "What is the weather forecast for Manchester?",
    "What is the weather like today?",
    "How do I install solar panels?",
    "How does a Lifetime ISA work?",
    "Which ISA should I open?",
]


def test_ranks_most_requested_uncovered_concepts(tmp_path):
    log = tmp_path / "ask.jsonl"
    _write_log(log, GAP_QUESTIONS)
    report = corpus_gap_report(log, SNAPSHOT, min_distinct=2)
    ranked = [(c.term, c.questions) for c in report.concepts]
    assert ranked[0] == ("passport", 3)  # most-requested gap leads
    assert ("weather", 2) in ranked
    assert all(c.questions >= 2 for c in report.concepts)  # floor holds


def test_answerable_and_routing_questions_contribute_no_gap(tmp_path):
    log = tmp_path / "ask.jsonl"
    _write_log(log, ["How does a Lifetime ISA work?", "Which ISA should I open?"])
    report = corpus_gap_report(log, SNAPSHOT, min_distinct=1)
    assert report.concepts == ()
    assert report.refusals_with_gaps == 0


def test_k_anonymity_floor_suppresses_rare_concepts(tmp_path):
    log = tmp_path / "ask.jsonl"
    _write_log(log, GAP_QUESTIONS)
    at2 = {c.term for c in corpus_gap_report(log, SNAPSHOT, min_distinct=2).concepts}
    at3 = {c.term for c in corpus_gap_report(log, SNAPSHOT, min_distinct=3).concepts}
    assert at3 <= at2  # raising the floor can only shrink the reported set
    assert "weather" in at2 and "weather" not in at3  # weather is in exactly 2 questions
    assert "passport" in at3  # passport is in 3, so it survives the higher floor


def test_bare_numbers_are_not_reported_as_concepts(tmp_path):
    log = tmp_path / "ask.jsonl"
    _write_log(log, ["Is 999999 a taxable amount?", "Is 999999 really taxable income?"])
    report = corpus_gap_report(log, SNAPSHOT, min_distinct=2)
    assert "999999" not in {c.term for c in report.concepts}
    assert all(any(ch.isalpha() for ch in c.term) for c in report.concepts)


def test_report_never_leaks_raw_questions(tmp_path):
    # Privacy invariant: concept terms are single tokens (no spaces) — a whole
    # question can never appear, and there is no question field on the report.
    log = tmp_path / "ask.jsonl"
    _write_log(log, GAP_QUESTIONS)
    report = corpus_gap_report(log, SNAPSHOT, min_distinct=2)
    for c in report.concepts:
        assert " " not in c.term
    assert report.questions_analyzed == len(GAP_QUESTIONS)


def test_deduplicates_repeated_questions(tmp_path):
    log = tmp_path / "ask.jsonl"
    _write_log(log, ["How do I renew my passport?"] * 5)
    report = corpus_gap_report(log, SNAPSHOT, min_distinct=2)
    # five identical asks are one distinct question, so the concept is below a floor of 2
    assert report.questions_analyzed == 1
    assert report.concepts == ()


def test_missing_log_is_an_empty_report(tmp_path):
    report = corpus_gap_report(tmp_path / "nope.jsonl", SNAPSHOT, min_distinct=2)
    assert report.questions_analyzed == 0
    assert report.concepts == ()


def test_skips_malformed_log_lines(tmp_path):
    log = tmp_path / "ask.jsonl"
    log.write_text(
        "not json\n"
        + json.dumps({"ts": 1, "kind": "x"})  # missing question
        + "\n"
        + json.dumps({"ts": 2, "question": "How do I renew my passport?", "kind": "x"})
        + "\n",
        encoding="utf-8",
    )
    report = corpus_gap_report(log, SNAPSHOT, min_distinct=1)
    assert report.questions_analyzed == 1


def test_cli_human_and_json(tmp_path, capsys):
    log = tmp_path / "ask.jsonl"
    _write_log(log, GAP_QUESTIONS)

    code = main(["--log", str(log), "--snapshot", str(SNAPSHOT), "--min-distinct", "2"])
    out = capsys.readouterr().out
    assert code == 0
    assert "corpus-gap report" in out
    assert "passport" in out

    code = main(
        ["--log", str(log), "--snapshot", str(SNAPSHOT), "--min-distinct", "2", "--json"]
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["questions_analyzed"] == len(GAP_QUESTIONS)
    assert any(c["term"] == "passport" for c in payload["concepts"])
