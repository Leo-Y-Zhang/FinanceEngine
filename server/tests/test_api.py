from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pistis.api.app import create_app

FIXTURE_SNAPSHOT = Path(__file__).parent / "fixtures" / "snapshot.json"


@pytest.fixture()
def client(tmp_path):
    app = create_app(snapshot_path=FIXTURE_SNAPSHOT, log_path=tmp_path / "ask.jsonl")
    return TestClient(app)


def test_missing_snapshot_fails_loudly(tmp_path):
    with pytest.raises(FileNotFoundError, match="corpus.refresh"):
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


def test_ask_routing_event(client):
    body = client.post("/ask", json={"question": "Which ISA should I open?"}).json()
    assert body["kind"] == "routing"
    assert body["routing"]["links"]


def test_ask_abstention(client):
    body = client.post("/ask", json={"question": "How do I renew my passport?"}).json()
    assert body["kind"] == "abstain"
    assert body["routing"]["links"]


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
