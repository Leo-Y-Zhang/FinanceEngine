"""Corpus-gap report — refusals aggregated into a keyless, privacy-safe backlog.

Each test here pins a property that an adversarial review found could break.
Where a property is about something being ABSENT from the output, the test also
carries a positive control that makes the term appear, so the assertion cannot
pass vacuously.
"""

import json
from pathlib import Path

import pytest

from pistis.gaps import DEFAULT_MIN_DISTINCT, corpus_gap_report, main

FIXTURES = Path(__file__).parent / "fixtures"
SNAPSHOT = FIXTURES / "snapshot.json"


def _write_log(path, questions):
    lines = [
        json.dumps({"ts": 1784900000 + i, "question": q, "kind": "x"})
        for i, q in enumerate(questions)
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _terms(report):
    return [c.term for c in report.thin_coverage.listed] + [
        c.term for c in report.no_overlap.listed
    ]


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

    # These questions share nothing with a UK personal-finance corpus, so they
    # are quarantined for scope triage rather than sold as things to add.
    ranked = [(c.term, c.questions) for c in report.no_overlap.listed]
    assert ranked[0] == ("passport", 3)  # most-requested gap leads
    assert ("weather", 2) in ranked
    assert all(c.questions >= 2 for c in report.no_overlap.listed)  # floor holds
    assert report.refusals_no_overlap == 4


def test_a_concept_is_counted_once_not_split_across_its_spellings(tmp_path):
    """The report's whole purpose is finding the MOST-requested gap. Keyed on
    the raw surface word, one concept asked about twice split into two entries
    of one question each and both fell below the floor — the top gap was
    reported as nothing at all."""
    log = tmp_path / "ask.jsonl"
    _write_log(
        log,
        ["How do I renew my passport?", "Do I need passports to travel abroad?"],
    )
    report = corpus_gap_report(log, SNAPSHOT, min_distinct=2)

    listed = {c.term: c.questions for c in report.no_overlap.listed}
    assert listed.get("passport") == 2  # one concept, two questions
    assert "passports" not in listed  # not a second concept


def test_concepts_are_grouped_by_where_they_mostly_appeared(tmp_path):
    """A concept's demand is counted once across every refusal, but it is filed
    under the section it mostly came from — counting per section would split the
    count again and re-create the fragmentation above."""
    log = tmp_path / "ask.jsonl"
    _write_log(log, GAP_QUESTIONS)
    report = corpus_gap_report(log, SNAPSHOT, min_distinct=2)

    thin = {c.term for c in report.thin_coverage.listed}
    no_overlap = {c.term for c in report.no_overlap.listed}
    assert not (thin & no_overlap)  # a concept is filed in exactly one section
    # passport is named by 3 questions in total, and lands in ONE section with
    # that full count rather than 2 here and 1 there.
    assert {c.questions for c in report.no_overlap.listed if c.term == "passport"} == {3}


def test_answerable_and_routing_questions_contribute_no_gap(tmp_path):
    log = tmp_path / "ask.jsonl"
    _write_log(log, ["How does a Lifetime ISA work?", "Which ISA should I open?"])
    report = corpus_gap_report(log, SNAPSHOT, min_distinct=1)
    assert report.thin_coverage.listed == ()
    assert report.no_overlap.listed == ()
    assert report.answered == 1
    assert report.routed == 1
    assert report.refused == 0


def test_reporting_floor_suppresses_rare_concepts(tmp_path):
    log = tmp_path / "ask.jsonl"
    _write_log(log, GAP_QUESTIONS)
    at2 = {c.term for c in corpus_gap_report(log, SNAPSHOT, min_distinct=2).no_overlap.listed}
    at3 = {c.term for c in corpus_gap_report(log, SNAPSHOT, min_distinct=3).no_overlap.listed}
    assert at3 <= at2  # raising the floor can only shrink the reported set
    assert "weather" in at2 and "weather" not in at3  # weather is in exactly 2 questions
    assert "passport" in at3  # passport is in 3, so it survives the higher floor


def test_the_shipped_default_floor_is_the_one_that_withholds(tmp_path):
    """DEFAULT_MIN_DISTINCT is what an operator actually runs with; pin that the
    default (not just an explicitly-passed 2) withholds a single-question term."""
    assert DEFAULT_MIN_DISTINCT == 2
    log = tmp_path / "ask.jsonl"
    _write_log(log, GAP_QUESTIONS)
    default = corpus_gap_report(log, SNAPSHOT)
    assert "solar" not in _terms(default)  # named by one question only
    assert default.no_overlap.suppressed > 0
    # positive control: the same term surfaces once a second question names it
    _write_log(log, GAP_QUESTIONS + ["Can I get a grant for solar panels?"])
    assert "solar" in _terms(corpus_gap_report(log, SNAPSHOT))


def test_amounts_and_identifiers_are_never_reported_as_concepts(tmp_path):
    """'has a letter in it' is not a test for a concept: NI numbers, postcodes
    and IBANs all contain letters, and '50k' is an amount, not a topic."""
    log = tmp_path / "ask.jsonl"
    _write_log(
        log,
        [
            "Is my NI number AB123456C valid for 50k of savings?",
            "Does AB123456C matter at SW1A1AA for 50k and GB29NWBK60161331926819?",
        ],
    )
    report = corpus_gap_report(log, SNAPSHOT, min_distinct=1)
    listed = _terms(report)
    for identifier in ("ab123456c", "sw1a1aa", "gb29nwbk60161331926819", "50k"):
        assert identifier not in listed
    # and nothing digit-bearing slipped through under another spelling
    assert not [t for t in listed if any(ch.isdigit() for ch in t)]


def test_known_form_codes_survive_the_identifier_filter(tmp_path):
    """The positive control for the rule above: a real UK form code IS a concept
    a curator wants, so the digit rule must not be a blanket ban."""
    log = tmp_path / "ask.jsonl"
    _write_log(
        log,
        ["Do I need form P60 for a passport claim?", "Where does form P60 go on a claim?"],
    )
    report = corpus_gap_report(log, SNAPSHOT, min_distinct=2)
    assert "p60" in _terms(report)


def test_one_person_retyping_cannot_clear_the_floor(tmp_path):
    """The floor counts distinct QUESTIONS. Keyed on raw text, one person could
    cross a floor of 2 by retyping their own question with a '?' or a stopword,
    publishing a rare proper noun only they had ever typed."""
    log = tmp_path / "ask.jsonl"
    _write_log(
        log,
        [
            "Does Hildegarde Ravensworth qualify",
            "Does Hildegarde Ravensworth qualify?",
            "does the Hildegarde Ravensworth qualify ?",
        ],
    )
    report = corpus_gap_report(log, SNAPSHOT, min_distinct=2)
    assert report.questions_analyzed == 1  # one question, typed three ways
    assert "hildegarde" not in _terms(report)
    assert "ravensworth" not in _terms(report)

    # positive control: two GENUINELY different questions do cross the floor,
    # so the assertions above are testing the floor and not a tautology.
    _write_log(
        log,
        [
            "Does Hildegarde Ravensworth qualify",
            "What relief can Hildegarde Ravensworth claim on a pension",
        ],
    )
    assert "hildegarde" in _terms(corpus_gap_report(log, SNAPSHOT, min_distinct=2))


def test_report_carries_no_question_text(tmp_path):
    """A concept is a single normalised word, so no multi-word phrase from a
    question can appear, and the report has no question field at all."""
    log = tmp_path / "ask.jsonl"
    _write_log(log, GAP_QUESTIONS)
    report = corpus_gap_report(log, SNAPSHOT, min_distinct=2)
    payload = json.dumps(report, default=lambda o: o.__dict__).lower()
    for question in GAP_QUESTIONS:
        assert question.lower() not in payload
    assert "question" not in {c.term for c in report.no_overlap.listed}
    for c in report.no_overlap.listed:
        assert " " not in c.term


def test_deduplicates_repeated_questions(tmp_path):
    log = tmp_path / "ask.jsonl"
    _write_log(log, ["How do I renew my passport?"] * 5)
    report = corpus_gap_report(log, SNAPSHOT, min_distinct=2)
    # five identical asks are one distinct question, so the concept is below a floor of 2
    assert report.questions_analyzed == 1
    assert _terms(report) == []


def test_dedup_ignores_case_and_punctuation(tmp_path):
    log = tmp_path / "ask.jsonl"
    _write_log(
        log,
        ["How do I renew my passport?", "HOW DO I RENEW MY PASSPORT", "how do i renew passport"],
    )
    assert corpus_gap_report(log, SNAPSHOT, min_distinct=1).questions_analyzed == 1


def test_missing_log_is_reported_as_missing_not_as_no_gaps(tmp_path, capsys):
    report = corpus_gap_report(tmp_path / "nope.jsonl", SNAPSHOT, min_distinct=2)
    assert report.questions_analyzed == 0
    assert report.log_found is False  # distinguishable from a log with no gaps
    assert _terms(report) == []

    code = main(["--log", str(tmp_path / "nope.jsonl"), "--snapshot", str(SNAPSHOT)])
    out = capsys.readouterr().out
    assert code == 2  # not 0: the operator's path was wrong
    assert "NOT FOUND" in out


def test_skipped_log_lines_are_counted_not_silently_dropped(tmp_path):
    log = tmp_path / "ask.jsonl"
    log.write_text(
        "not json\n"
        + json.dumps({"ts": 1, "kind": "x"})  # missing question
        + "\n"
        + json.dumps({"ts": 2, "question": 42})  # not a string
        + "\n"
        + json.dumps({"ts": 3, "question": {"nested": "passport renew"}})  # not a string
        + "\n"
        + json.dumps([1, 2, 3])  # valid JSON, not a record
        + "\n"
        + json.dumps({"ts": 4, "question": "How do I renew my passport?", "kind": "x"})
        + "\n",
        encoding="utf-8",
    )
    report = corpus_gap_report(log, SNAPSHOT, min_distinct=1)
    assert report.questions_analyzed == 1
    # not-json, no question, question=42, question={...}, a bare list = 5 skips
    assert report.lines_skipped == 5
    # the repr of the nested dict must never be mined for concepts
    assert "nested" not in _terms(report)


def test_undecodable_log_bytes_are_skipped_not_raised(tmp_path):
    """Best-effort has to mean best-effort: a log rewritten as UTF-16 by a shell
    redirect used to raise UnicodeDecodeError at the operator."""
    log = tmp_path / "ask.jsonl"
    body = json.dumps({"ts": 1, "question": "How do I renew my passport?"}) + "\n"
    log.write_bytes(body.encode("utf-16-le"))
    report = corpus_gap_report(log, SNAPSHOT, min_distinct=1)
    assert report.questions_analyzed == 0
    assert report.lines_skipped >= 1  # and it says it skipped something


def test_report_names_its_own_inputs(tmp_path):
    """The claim is that the report reflects the CURRENT corpus. A reader can
    only check that if the report says which corpus, and when it was fetched."""
    log = tmp_path / "ask.jsonl"
    _write_log(log, GAP_QUESTIONS)
    report = corpus_gap_report(log, SNAPSHOT, min_distinct=2)
    assert report.log_path == str(log)
    assert report.snapshot_path == str(SNAPSHOT)
    assert report.snapshot_fetched  # non-empty date from the snapshot itself


def test_refusal_counters_add_up(tmp_path):
    log = tmp_path / "ask.jsonl"
    _write_log(log, GAP_QUESTIONS)
    r = corpus_gap_report(log, SNAPSHOT, min_distinct=2)
    assert r.answered + r.routed + r.refused == r.questions_analyzed
    assert r.refusals_with_concepts + r.refusals_without_concepts == r.refused
    assert r.refusals_no_overlap <= r.refused
    assert r.refused > 0 and r.refusals_with_concepts > 0  # non-vacuous


def test_an_all_refused_log_never_reads_as_no_backlog(tmp_path, capsys):
    """A log where every question was refused must not print as if there were
    nothing to do."""
    log = tmp_path / "ask.jsonl"
    _write_log(log, GAP_QUESTIONS[:3])
    code = main(["--log", str(log), "--snapshot", str(SNAPSHOT), "--min-distinct", "2"])
    out = capsys.readouterr().out
    assert code == 0
    assert "refused                 : 3" in out
    assert "passport" in out


def test_deterministic_across_runs(tmp_path):
    log = tmp_path / "ask.jsonl"
    _write_log(log, GAP_QUESTIONS)
    assert corpus_gap_report(log, SNAPSHOT, min_distinct=2) == corpus_gap_report(
        log, SNAPSHOT, min_distinct=2
    )


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
    assert any(c["term"] == "passport" for c in payload["no_overlap"]["listed"])
    # the machine record carries the pre-cap total, so truncation is detectable
    assert payload["no_overlap"]["total"] == len(payload["no_overlap"]["listed"])


def test_missing_snapshot_explains_itself_instead_of_a_traceback(tmp_path, capsys):
    log = tmp_path / "ask.jsonl"
    _write_log(log, GAP_QUESTIONS)
    with pytest.raises(SystemExit) as exit_info:
        main(["--log", str(log), "--snapshot", str(tmp_path / "nope.json")])
    assert exit_info.value.code == 3
    message = capsys.readouterr().err
    assert "corpus snapshot" in message
    assert "pistis.corpus.refresh" in message  # tells the operator what to run


def test_top_cap_never_silently_truncates(tmp_path, capsys):
    log = tmp_path / "ask.jsonl"
    _write_log(log, GAP_QUESTIONS)

    full = corpus_gap_report(log, SNAPSHOT, min_distinct=2)
    capped = corpus_gap_report(log, SNAPSHOT, min_distinct=2, top=1)

    assert len(full.no_overlap.listed) >= 2  # the fixture genuinely has >1 gap
    assert full.no_overlap.total == len(full.no_overlap.listed)  # uncapped: total == listed
    assert len(capped.no_overlap.listed) == 1
    assert capped.no_overlap.listed[0].term == "passport"  # the cap keeps the top-ranked
    # the cap shrinks the LISTING, never the reported truth
    assert capped.no_overlap.total == full.no_overlap.total
    assert capped.no_overlap.suppressed == full.no_overlap.suppressed

    code = main(
        ["--log", str(log), "--snapshot", str(SNAPSHOT), "--min-distinct", "2", "--top", "1"]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert f"and {full.no_overlap.total - 1} more" in out  # truncation is visible


def test_top_zero_discloses_the_withheld_count(tmp_path, capsys):
    log = tmp_path / "ask.jsonl"
    _write_log(log, GAP_QUESTIONS)
    total = corpus_gap_report(log, SNAPSHOT, min_distinct=2).no_overlap.total
    assert total >= 2  # non-vacuity guard

    report = corpus_gap_report(log, SNAPSHOT, min_distinct=2, top=0)
    assert report.no_overlap.listed == ()
    assert report.no_overlap.total == total  # an empty listing is not "no gaps"

    code = main(
        ["--log", str(log), "--snapshot", str(SNAPSHOT), "--min-distinct", "2", "--top", "0"]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert f"list {total}" in out


def test_all_flag_overrides_the_cap(tmp_path, capsys):
    log = tmp_path / "ask.jsonl"
    _write_log(log, GAP_QUESTIONS)
    full = corpus_gap_report(log, SNAPSHOT, min_distinct=2)
    assert full.no_overlap.total >= 2  # non-vacuity guard

    code = main(
        [
            "--log", str(log), "--snapshot", str(SNAPSHOT),
            "--min-distinct", "2", "--top", "1", "--all", "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert len(payload["no_overlap"]["listed"]) == full.no_overlap.total  # nothing withheld
    assert {c["term"] for c in payload["no_overlap"]["listed"]} == {
        c.term for c in full.no_overlap.listed
    }


def test_negative_top_is_rejected_rather_than_reverse_slicing(tmp_path):
    log = tmp_path / "ask.jsonl"
    _write_log(log, GAP_QUESTIONS)
    # a negative slice would silently DROP the highest-ranked gaps — refuse instead
    with pytest.raises(ValueError):
        corpus_gap_report(log, SNAPSHOT, min_distinct=2, top=-1)
    with pytest.raises(SystemExit):
        main(["--log", str(log), "--snapshot", str(SNAPSHOT), "--top", "-1"])
