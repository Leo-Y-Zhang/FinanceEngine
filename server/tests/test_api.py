import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from finance_engine.api.app import create_app
from finance_engine.privacy.retention import RETENTION_SECONDS

FIXTURE_SNAPSHOT = Path(__file__).parent / "fixtures" / "snapshot.json"


@pytest.fixture()
def client(tmp_path):
    app = create_app(snapshot_path=FIXTURE_SNAPSHOT, log_path=tmp_path / "ask.jsonl")
    return TestClient(app)


def test_missing_snapshot_fails_loudly(tmp_path):
    with pytest.raises(FileNotFoundError, match=r"corpus\.refresh"):
        create_app(snapshot_path=tmp_path / "nope.json", log_path=None)


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_corpus_status(client):
    status = client.get("/corpus/status").json()
    assert status["documents"] == 8
    assert status["passages"] > 8
    assert "GOVUK" in status["orgs"]


def test_ask_answer_card(client):
    body = client.post("/ask", json={"question": "How does a Lifetime ISA work?"}).json()
    assert body["kind"] == "answer"
    assert body["claims"]
    for claim in body["claims"]:
        assert claim["citation"]["url"].startswith("https://")
        assert claim["citation"]["fetched_at"]
    assert "not regulated financial advice" in body["disclaimer"]


def test_ask_answer_includes_trust_report(client):
    body = client.post("/ask", json={"question": "How does a Lifetime ISA work?"}).json()
    assert body["kind"] == "answer"
    tr = body["trust_report"]
    assert tr is not None
    assert tr["total"] == len(body["claims"])
    assert tr["grounded"] == tr["total"]
    assert tr["all_grounded"] is True
    assert len(tr["verdicts"]) == len(body["claims"])
    for v in tr["verdicts"]:
        assert v["verdict"] == "grounded"
        assert v["passage_id"]


def test_ask_answer_includes_freshness(client):
    body = client.post("/ask", json={"question": "How does a Lifetime ISA work?"}).json()
    assert body["kind"] == "answer"
    fr = body["freshness"]
    assert fr is not None
    assert len(fr["per_claim"]) == len(body["claims"])
    assert fr["overall"] in ("current", "aging", "stale")


def test_ask_routing_event(client):
    body = client.post("/ask", json={"question": "Which ISA should I open?"}).json()
    assert body["kind"] == "routing"
    assert body["routing"]["links"]


def test_ask_abstention(client):
    body = client.post("/ask", json={"question": "How do I renew my passport?"}).json()
    assert body["kind"] == "abstain"
    assert body["routing"]["links"]


def test_ask_abstention_includes_refusal_report(client):
    body = client.post("/ask", json={"question": "How do I renew my passport?"}).json()
    assert body["kind"] == "abstain"
    report = body["report"]
    assert report is not None
    assert report["stage"] in ("no_source", "weak_coverage")
    assert report["explanation"]
    assert "passport" in report["uncovered_terms"]


def test_ask_weak_coverage_serialises_signal_meters(client):
    body = client.post(
        "/ask", json={"question": "What is the weather forecast for Manchester?"}
    ).json()
    assert body["kind"] == "abstain"
    report = body["report"]
    assert report["stage"] == "weak_coverage"
    names = {s["name"] for s in report["signals"]}
    assert names == {"retrieval strength", "source coverage"}
    assert any(s["passed"] is False for s in report["signals"])


def test_ask_logs_outcomes(tmp_path):
    log = tmp_path / "ask.jsonl"
    client = TestClient(create_app(snapshot_path=FIXTURE_SNAPSHOT, log_path=log))
    client.post("/ask", json={"question": "What is the ISA allowance?"})
    client.post("/ask", json={"question": "Which ISA should I open?"})
    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2


def test_ask_validates_question_length(client):
    assert client.post("/ask", json={"question": ""}).status_code == 422
    assert client.post("/ask", json={"question": "x" * 501}).status_code == 422


def test_create_app_purges_expired_log_entries_on_startup(tmp_path):
    """Retention policy (privacy notice: 30 days) is enforced at startup."""
    log = tmp_path / "ask.jsonl"
    now = time.time()
    stale = {"ts": now - RETENTION_SECONDS - 3600, "question": "old question", "kind": "answer"}
    fresh = {"ts": now - 60, "question": "fresh question", "kind": "answer"}
    log.write_text(
        json.dumps(stale) + "\n" + json.dumps(fresh) + "\n",
        encoding="utf-8",
    )

    create_app(snapshot_path=FIXTURE_SNAPSHOT, log_path=log)

    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert "fresh question" in lines[0]
    assert "old question" not in log.read_text(encoding="utf-8")
