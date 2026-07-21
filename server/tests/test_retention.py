"""Tests for the ask-log retention/purge policy (compliance-review finding #8).

The privacy notice promises a 30-day retention period for `logs/ask.jsonl`
entries; this suite covers the enforcement mechanism.
"""

import json
import time
from pathlib import Path

from pistis.privacy.retention import RETENTION_DAYS, RETENTION_SECONDS, purge_expired


def _write(log_path: Path, records: list[dict]) -> None:
    text = "\n".join(json.dumps(r) for r in records)
    log_path.write_text(text + ("\n" if records else ""), encoding="utf-8")


def test_missing_file_is_a_noop(tmp_path):
    assert purge_expired(tmp_path / "nope.jsonl") == 0


def test_keeps_entries_within_the_retention_window(tmp_path):
    log = tmp_path / "ask.jsonl"
    now = time.time()
    _write(log, [{"ts": now - 60, "question": "recent", "kind": "answer"}])

    removed = purge_expired(log, now=now)

    assert removed == 0
    assert "recent" in log.read_text(encoding="utf-8")


def test_removes_entries_older_than_the_retention_window(tmp_path):
    log = tmp_path / "ask.jsonl"
    now = time.time()
    old = {"ts": now - RETENTION_SECONDS - 3600, "question": "stale", "kind": "answer"}
    fresh = {"ts": now - 3600, "question": "fresh", "kind": "answer"}
    _write(log, [old, fresh])

    removed = purge_expired(log, now=now)

    assert removed == 1
    remaining = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(remaining) == 1
    assert "fresh" in remaining[0]
    assert "stale" not in log.read_text(encoding="utf-8")


def test_purging_everything_leaves_an_empty_file_not_a_missing_one(tmp_path):
    log = tmp_path / "ask.jsonl"
    now = time.time()
    _write(log, [{"ts": now - RETENTION_SECONDS - 1, "question": "old", "kind": "answer"}])

    removed = purge_expired(log, now=now)

    assert removed == 1
    assert log.exists()
    assert log.read_text(encoding="utf-8") == ""


def test_malformed_lines_are_dropped_not_fatal(tmp_path):
    log = tmp_path / "ask.jsonl"
    now = time.time()
    log.write_text(
        "not json at all\n"
        + json.dumps({"ts": now - 60, "question": "ok", "kind": "answer"})
        + "\n"
        + json.dumps({"question": "missing ts field", "kind": "answer"})
        + "\n",
        encoding="utf-8",
    )

    removed = purge_expired(log, now=now)

    assert removed == 2
    remaining = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(remaining) == 1
    assert "ok" in remaining[0]


def test_retention_period_is_short_as_promised_in_the_privacy_notice():
    # The privacy notice promises "30 days" — keep the two in sync.
    assert RETENTION_DAYS == 30
    assert RETENTION_SECONDS == 30 * 24 * 60 * 60
