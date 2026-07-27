"""Corpus-gap report — refusals aggregated into a keyless, privacy-safe backlog.

Each test here pins a property an adversarial review found could break. Where a
property is about something being ABSENT from the output, the test carries a
positive control that makes the term appear, so the assertion cannot pass
vacuously — that is exactly how the previous privacy tests died.
"""

import json
from dataclasses import asdict
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
    return {c.term for c in report.no_shared_term.listed} | {
        c.term for c in report.partial_match.listed
    }


def _total(report):
    return report.no_shared_term.total + report.partial_match.total


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

    ranked = [(c.term, c.questions) for c in report.no_shared_term.listed]
    assert ranked[0] == ("passport", 3)  # most-requested gap leads
    assert ("weather", 2) in ranked
    assert all(c.questions >= 2 for c in report.no_shared_term.listed)  # floor holds

    # Fixture-independent invariants (a hard-coded count would break on any
    # corpus change with no hint why).
    base = corpus_gap_report(log, SNAPSHOT, min_distinct=1)
    suppressed = report.no_shared_term.suppressed + report.partial_match.suppressed
    assert suppressed == _total(base) - _total(report)  # nothing falls below a floor of 1
    assert 1 <= report.refusals_with_concepts <= report.questions_analyzed


def test_a_concept_is_counted_once_not_split_across_its_spellings(tmp_path):
    """The report's whole purpose is finding the MOST-requested gap. Keyed on
    the user's own wording, one concept asked about twice split into two entries
    of one question each, both fell below the floor, and the top gap was
    reported as nothing at all."""
    log = tmp_path / "ask.jsonl"
    _write_log(
        log,
        ["How do I renew my passport?", "Do I need passports to travel abroad?"],
    )
    report = corpus_gap_report(log, SNAPSHOT, min_distinct=2)

    listed = {c.term: c.questions for c in report.no_shared_term.listed}
    assert listed.get("passport") == 2  # one concept, two questions
    assert "passports" not in listed  # not a second concept


def test_a_concept_is_filed_in_one_section_with_its_whole_count(tmp_path):
    """Demand is counted once across every refusal that named a concept; only
    the SECTION is decided by where it mostly appeared. Counting per section
    would split the count again and re-create the fragmentation above."""
    log = tmp_path / "ask.jsonl"
    _write_log(log, GAP_QUESTIONS)
    report = corpus_gap_report(log, SNAPSHOT, min_distinct=2)

    absent = {c.term for c in report.no_shared_term.listed}
    partial = {c.term for c in report.partial_match.listed}
    assert not (absent & partial)  # a concept is filed in exactly one section
    assert {c.questions for c in report.no_shared_term.listed if c.term == "passport"} == {3}


def test_answerable_and_routing_questions_contribute_no_gap(tmp_path):
    log = tmp_path / "ask.jsonl"
    _write_log(log, ["How does a Lifetime ISA work?", "Which ISA should I open?"])
    report = corpus_gap_report(log, SNAPSHOT, min_distinct=1)
    assert _terms(report) == set()
    assert (report.answered, report.routed, report.refused) == (1, 1, 0)


def test_reporting_floor_suppresses_rare_concepts(tmp_path):
    log = tmp_path / "ask.jsonl"
    _write_log(log, GAP_QUESTIONS)
    at2 = _terms(corpus_gap_report(log, SNAPSHOT, min_distinct=2))
    at3 = _terms(corpus_gap_report(log, SNAPSHOT, min_distinct=3))
    assert at3 <= at2  # raising the floor can only shrink the reported set
    assert "weather" in at2 and "weather" not in at3  # weather is in exactly 2 questions
    assert "passport" in at3  # passport is in 3, so it survives the higher floor


def test_the_shipped_default_floor_is_the_one_that_withholds(tmp_path, capsys):
    """Every other test passes min_distinct explicitly, so the value a flagless
    run actually uses was pinned by nothing: lowering it 2 -> 1 kept the whole
    suite green while the default report began listing a proper noun that
    appeared in exactly one question."""
    assert DEFAULT_MIN_DISTINCT == 2
    log = tmp_path / "ask.jsonl"
    _write_log(log, GAP_QUESTIONS)

    report = corpus_gap_report(log, SNAPSHOT)  # NO min_distinct
    assert report.min_distinct == 2
    assert report.privacy_floor_active is True
    assert "manchester" not in _terms(report)  # named by one question only
    assert all(c.questions >= 2 for c in report.no_shared_term.listed)

    main(["--log", str(log), "--snapshot", str(SNAPSHOT)])  # NO --min-distinct
    assert ">= 2 distinct questions" in capsys.readouterr().out


def test_disabling_the_floor_is_announced_not_silent(tmp_path, capsys):
    log = tmp_path / "ask.jsonl"
    _write_log(log, GAP_QUESTIONS)
    report = corpus_gap_report(log, SNAPSHOT, min_distinct=1)
    assert report.privacy_floor_active is False

    main(["--log", str(log), "--snapshot", str(SNAPSHOT), "--min-distinct", "1"])
    assert "the floor is OFF" in capsys.readouterr().out
    with pytest.raises(SystemExit):  # a negative floor is nonsense, not a setting
        main(["--log", str(log), "--snapshot", str(SNAPSHOT), "--min-distinct", "-5"])


@pytest.mark.parametrize(
    "banned, questions",
    [
        ("999999", ["Is 999999 really taxable income?", "Does 999999 count as taxable income?"]),
        ("£45k", ["Is £45k really taxable income?", "Do I owe tax on £45k really?"]),
        ("40k", ["Do I pay tax on a 40k salary?", "Is 40k a higher rate salary?"]),
        (
            "qq123456c",
            ["Do I pay tax on income linked to QQ123456C?", "Is QQ123456C exempt from gains?"],
        ),
        (
            "sw1a",
            ["Do I pay council tax at SW1A 1AA?", "Is SW1A 1AA in a higher council band?"],
        ),
        (
            "gb82west12345698765432",
            ["Is GB82WEST12345698765432 a valid account?", "Does GB82WEST12345698765432 work?"],
        ),
    ],
)
def test_amount_and_identifier_shapes_are_never_reported(tmp_path, banned, questions):
    """'Has a letter in it' is no test at all: NI numbers, postcodes and IBANs
    all contain letters, and 45k is an amount, not a topic."""
    log = tmp_path / "ask.jsonl"
    _write_log(log, questions)
    report = corpus_gap_report(log, SNAPSHOT, min_distinct=1)
    assert report.refusals_with_concepts >= 1  # the abstain path really ran
    assert _terms(report)  # non-vacuity: something WAS reported
    assert banned.lower() not in _terms(report)
    assert "1aa" not in _terms(report)


def test_short_letter_led_codes_survive_the_identifier_filter(tmp_path):
    """The positive control: a blanket ban on digits would delete p60, sa302 and
    ir35 — the most actionable class of UK-finance gap there is — which would be
    a worse defect than the one being fixed."""
    log = tmp_path / "ask.jsonl"
    _write_log(
        log,
        [
            "Do I need form P60 and IR35 advice for a passport claim?",
            "Where does form P60 go, and does IR35 apply to a claim?",
        ],
    )
    assert {"p60", "ir35"} <= _terms(corpus_gap_report(log, SNAPSHOT, min_distinct=2))


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
            "does the  Hildegarde Ravensworth qualify !",
        ],
    )
    report = corpus_gap_report(log, SNAPSHOT, min_distinct=2)
    assert report.questions_analyzed == 1  # one question, typed three ways
    assert report.asks_read == 3  # and it says how many asks that was
    assert "hildegarde" not in _terms(report)
    assert "ravensworth" not in _terms(report)

    # positive control: two GENUINELY different questions do cross the floor, so
    # the assertions above test the floor rather than a tautology.
    _write_log(
        log,
        [
            "Does Hildegarde Ravensworth qualify",
            "What relief can Hildegarde Ravensworth claim on a pension",
        ],
    )
    assert "hildegarde" in _terms(corpus_gap_report(log, SNAPSHOT, min_distinct=2))


def test_report_carries_no_question_text(tmp_path):
    """The old version of this test asserted no space in a term — true by
    construction of the tokenizer, so it passed with the entire privacy layer
    deleted. Assert over the SERIALISED surface instead, which is what a leak
    would actually travel through."""
    log = tmp_path / "ask.jsonl"
    _write_log(log, GAP_QUESTIONS)
    report = corpus_gap_report(log, SNAPSHOT, min_distinct=2)
    payload = asdict(report)
    blob = json.dumps(payload).lower()

    assert _terms(report)  # non-vacuity
    for section in ("no_shared_term", "partial_match"):
        for concept in payload[section]["listed"]:
            # kills a leak mutant that adds an example_question field
            assert set(concept) == {"term", "questions"}
    for question in GAP_QUESTIONS:
        assert question.lower() not in blob
        words = question.lower().split()
        for i in range(max(0, len(words) - 3)):
            assert " ".join(words[i : i + 4]) not in blob  # no 4-word window either


def test_deduplicates_repeated_questions(tmp_path):
    log = tmp_path / "ask.jsonl"
    _write_log(log, ["How do I renew my passport?"] * 5)
    report = corpus_gap_report(log, SNAPSHOT, min_distinct=2)
    # five identical asks are one distinct question, so it is below a floor of 2
    assert (report.asks_read, report.questions_analyzed) == (5, 1)
    assert _terms(report) == set()


def test_dedup_ignores_case_punctuation_and_word_order(tmp_path):
    log = tmp_path / "ask.jsonl"
    _write_log(
        log,
        ["How do I renew my passport?", "HOW DO I RENEW MY PASSPORT", "passport renew"],
    )
    assert corpus_gap_report(log, SNAPSHOT, min_distinct=1).questions_analyzed == 1


def test_missing_log_is_reported_as_missing_not_as_no_gaps(tmp_path, capsys):
    report = corpus_gap_report(tmp_path / "nope.jsonl", SNAPSHOT, min_distinct=2)
    assert report.questions_analyzed == 0
    assert report.log_found is False  # distinguishable from a log with no gaps
    assert _terms(report) == set()

    code = main(["--log", str(tmp_path / "nope.jsonl"), "--snapshot", str(SNAPSHOT)])
    assert code == 2  # not 0: the operator's path was wrong
    assert "NOT FOUND" in capsys.readouterr().out


def test_skipped_log_lines_are_counted_and_never_mined(tmp_path):
    log = tmp_path / "ask.jsonl"
    log.write_text(
        "not json\n"
        + json.dumps({"ts": 1, "kind": "x"})  # missing question
        + "\n"
        + json.dumps({"ts": 2, "question": None})  # null: str() made this "none"
        + "\n"
        + json.dumps({"ts": 3, "question": 42})  # not a string
        + "\n"
        + json.dumps({"ts": 4, "question": {"text": "How do I renew my passport?"}})
        + "\n"
        + json.dumps([1, 2, 3])  # valid JSON, not a record
        + "\n"
        + json.dumps({"ts": 5, "question": "How do I renew my passport?", "kind": "x"})
        + "\n",
        encoding="utf-8",
    )
    report = corpus_gap_report(log, SNAPSHOT, min_distinct=1)
    # not-json, no question, null, 42, nested object, bare list = 6 skips
    assert (report.questions_analyzed, report.asks_read, report.lines_skipped) == (1, 1, 6)
    # a coerced repr would have leaked the JSON key and a phantom concept
    assert "text" not in _terms(report)
    assert "none" not in _terms(report)


def test_a_byte_order_mark_does_not_swallow_the_first_record(tmp_path):
    plain = tmp_path / "plain.jsonl"
    bommed = tmp_path / "bom.jsonl"
    _write_log(plain, GAP_QUESTIONS)
    bommed.write_bytes(b"\xef\xbb\xbf" + plain.read_bytes())
    with_bom = corpus_gap_report(bommed, SNAPSHOT, min_distinct=2)
    assert with_bom.lines_skipped == 0
    assert with_bom.questions_analyzed == corpus_gap_report(
        plain, SNAPSHOT, min_distinct=2
    ).questions_analyzed


def test_an_undecodable_log_fails_loudly_rather_than_reporting_nothing(tmp_path):
    """Decoding with replacement characters was worse than useless: a mangled
    latin-1 record still parses as JSON and would be silently accepted with
    corrupted text feeding the counts, and a UTF-16 log reported zero questions
    at status 0 — the silent false negative this file exists to avoid."""
    log = tmp_path / "ask.jsonl"
    log.write_bytes(
        (json.dumps({"ts": 1, "question": "How do I renew my passport?"}) + "\n").encode(
            "utf-16-le"
        )
    )
    with pytest.raises(ValueError, match="not one carried a usable question"):
        corpus_gap_report(log, SNAPSHOT, min_distinct=1)
    with pytest.raises(SystemExit):
        main(["--log", str(log), "--snapshot", str(SNAPSHOT)])

    # a genuinely undecodable byte sequence is refused at the decode step
    log.write_bytes(b'{"ts": 1, "question": "caf\xe9 pension"}\n')
    with pytest.raises(ValueError, match="not valid UTF-8"):
        corpus_gap_report(log, SNAPSHOT, min_distinct=1)


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
    assert r.refused > 0 and r.refusals_with_concepts > 0  # non-vacuous


def test_refusals_with_no_term_signal_are_disclosed(tmp_path, capsys):
    """A refusal that names no term is invisible to the backlog. Saying nothing
    about it let an all-refused log read as a clean bill of health."""
    log = tmp_path / "ask.jsonl"
    _write_log(log, ["???", "the"])
    report = corpus_gap_report(log, SNAPSHOT, min_distinct=2)
    assert (report.refused, report.refusals_with_concepts) == (2, 0)
    assert report.refusals_without_concepts == 2

    main(["--log", str(log), "--snapshot", str(SNAPSHOT), "--min-distinct", "2"])
    assert "NOT represented here" in capsys.readouterr().out


def test_the_human_report_carries_its_own_caveats(tmp_path, capsys):
    log = tmp_path / "ask.jsonl"
    _write_log(log, GAP_QUESTIONS)
    main(["--log", str(log), "--snapshot", str(SNAPSHOT), "--min-distinct", "2"])
    out = capsys.readouterr().out
    assert "cannot tell them apart" in out  # gap vs correct out-of-scope refusal
    assert "Repeat asks of the same wording count once" in out


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
    assert any(c["term"] == "passport" for c in payload["no_shared_term"]["listed"])
    # the machine record carries the pre-cap total, so truncation is detectable
    assert payload["no_shared_term"]["total"] == len(payload["no_shared_term"]["listed"])


def test_missing_snapshot_explains_itself_instead_of_a_traceback(tmp_path, capsys):
    log = tmp_path / "ask.jsonl"
    _write_log(log, GAP_QUESTIONS)
    with pytest.raises(SystemExit) as exit_info:
        main(["--log", str(log), "--snapshot", str(tmp_path / "nope.json")])
    assert exit_info.value.code == 3
    assert "pistis.corpus.refresh" in capsys.readouterr().err  # says what to run


def test_top_cap_never_silently_truncates(tmp_path, capsys):
    log = tmp_path / "ask.jsonl"
    _write_log(log, GAP_QUESTIONS)

    full = corpus_gap_report(log, SNAPSHOT, min_distinct=2)
    capped = corpus_gap_report(log, SNAPSHOT, min_distinct=2, top=1)

    assert len(full.no_shared_term.listed) >= 2  # the fixture genuinely has >1 gap
    assert full.no_shared_term.total == len(full.no_shared_term.listed)  # uncapped
    assert len(capped.no_shared_term.listed) == 1
    assert capped.no_shared_term.listed[0].term == "passport"  # cap keeps the top-ranked
    # the cap shrinks the LISTING, never the reported truth
    assert capped.no_shared_term.total == full.no_shared_term.total
    assert capped.no_shared_term.suppressed == full.no_shared_term.suppressed

    code = main(
        ["--log", str(log), "--snapshot", str(SNAPSHOT), "--min-distinct", "2", "--top", "1"]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert f"and {full.no_shared_term.total - 1} more" in out  # truncation is visible


def test_top_zero_discloses_the_withheld_count(tmp_path, capsys):
    log = tmp_path / "ask.jsonl"
    _write_log(log, GAP_QUESTIONS)
    total = corpus_gap_report(log, SNAPSHOT, min_distinct=2).no_shared_term.total
    assert total >= 2  # non-vacuity guard

    report = corpus_gap_report(log, SNAPSHOT, min_distinct=2, top=0)
    assert report.no_shared_term.listed == ()
    assert report.no_shared_term.total == total  # an empty listing is not "no gaps"

    main(["--log", str(log), "--snapshot", str(SNAPSHOT), "--min-distinct", "2", "--top", "0"])
    assert f"list {total}" in capsys.readouterr().out


def test_all_flag_lists_strictly_more_than_the_cap(tmp_path, capsys):
    log = tmp_path / "ask.jsonl"
    _write_log(log, GAP_QUESTIONS)
    full = corpus_gap_report(log, SNAPSHOT, min_distinct=2)
    assert full.no_shared_term.total >= 2  # non-vacuity guard

    args = ["--log", str(log), "--snapshot", str(SNAPSHOT), "--min-distinct", "2", "--json"]
    main([*args, "--top", "1"])
    capped = json.loads(capsys.readouterr().out)["no_shared_term"]["listed"]
    main([*args, "--top", "1", "--all"])
    everything = json.loads(capsys.readouterr().out)["no_shared_term"]["listed"]

    assert len(everything) > len(capped)  # pins what --all is named for
    assert len(everything) == full.no_shared_term.total  # nothing withheld
    assert {c["term"] for c in everything} == {c.term for c in full.no_shared_term.listed}


def test_negative_top_is_rejected_rather_than_reverse_slicing(tmp_path):
    log = tmp_path / "ask.jsonl"
    _write_log(log, GAP_QUESTIONS)
    # a negative slice would silently DROP the highest-ranked gaps — refuse instead
    with pytest.raises(ValueError):
        corpus_gap_report(log, SNAPSHOT, min_distinct=2, top=-1)
    with pytest.raises(SystemExit):
        main(["--log", str(log), "--snapshot", str(SNAPSHOT), "--top", "-1"])
