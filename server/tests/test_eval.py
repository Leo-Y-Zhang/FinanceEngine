"""The honesty eval must pass over the fixture corpus — the core promise held."""

from pathlib import Path

from pistis.eval import main, run_eval

FIXTURES = Path(__file__).parent / "fixtures"


def test_honesty_eval_passes_over_fixtures():
    r = run_eval(FIXTURES / "snapshot.json", FIXTURES / "golden.json")
    assert r.questions > 0
    # every golden question lands in its expected state
    assert r.answerability_accuracy == 1.0, r.mismatches
    # answers actually assert claims, and every one is grounded (the promise)
    assert r.total_claims > 0
    assert r.grounded_rate == 1.0
    assert r.unsupported_claims == 0
    assert r.citations_complete
    assert r.passed


def test_eval_scores_every_refusal_as_explained():
    # Symmetric with the faithfulness promise: over the golden set, every
    # abstention must carry an explanation, and that is part of PASS.
    r = run_eval(FIXTURES / "snapshot.json", FIXTURES / "golden.json")
    assert r.abstentions > 0
    assert r.abstentions_explained == r.abstentions
    assert r.passed


def test_eval_cli_exits_zero_and_reports_pass(capsys):
    code = main(
        [
            "--snapshot", str(FIXTURES / "snapshot.json"),
            "--golden", str(FIXTURES / "golden.json"),
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "PASS" in out
    assert "Unsupported claims     : 0" in out


def test_eval_cli_json(capsys):
    code = main(
        [
            "--snapshot", str(FIXTURES / "snapshot.json"),
            "--golden", str(FIXTURES / "golden.json"),
            "--json",
        ]
    )
    import json

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["passed"] is True
    assert payload["grounded_rate"] == 1.0
