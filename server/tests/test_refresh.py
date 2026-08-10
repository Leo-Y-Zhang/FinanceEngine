"""Corpus refresh — the step that can silently destroy the corpus.

No network here: `fetch_entry_text` is stubbed, so these pin the orchestration
rather than the fetching. The properties that matter are about what happens when
sources go WRONG, because that is when this code decides whether the snapshot
on disk survives.
"""

import json

import pytest

from finance_engine.corpus import refresh as refresh_mod
from finance_engine.corpus.refresh import MIN_TEXT_CHARS, refresh
from finance_engine.models import ManifestEntry, SourceOrg

PROSE = "A sentence about the ISA allowance. " * 20  # comfortably over the floor


def _entry(entry_id: str) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        domain="savings_isas",
        title=f"Title {entry_id}",
        org=SourceOrg.GOVUK,
        kind="govuk",
        locator=f"/{entry_id}",
        why="test fixture",
    )


@pytest.fixture
def manifest(monkeypatch):
    def _install(entries):
        monkeypatch.setattr(refresh_mod, "load_manifest", lambda: entries)

    return _install


def _install_fetch(monkeypatch, results):
    """results: {locator: (text, last_updated)} or an Exception to raise."""

    def fake(kind, locator):
        outcome = results[locator]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(refresh_mod, "fetch_entry_text", fake)


def test_a_total_fetch_failure_does_not_overwrite_the_existing_snapshot(
    tmp_path, monkeypatch, manifest, capsys
):
    """The one that really matters.

    If every source fails — the box is offline, a host blocks the fetch — the
    corpus already on disk must survive untouched. Writing an empty snapshot
    would destroy the corpus and leave a product that abstains on everything
    while looking like it ran fine.
    """
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text('{"documents": ["precious"]}', encoding="utf-8")

    manifest([_entry("a"), _entry("b")])
    _install_fetch(monkeypatch, {"/a": RuntimeError("offline"), "/b": RuntimeError("403")})

    code = refresh(snapshot)

    assert code == 1
    assert snapshot.read_text(encoding="utf-8") == '{"documents": ["precious"]}'
    assert "not written" in capsys.readouterr().out


def test_one_bad_source_does_not_lose_the_good_ones(tmp_path, monkeypatch, manifest, capsys):
    """A partial corpus with honest dates beats no corpus — the gate abstains
    over whatever is missing."""
    snapshot = tmp_path / "snapshot.json"
    manifest([_entry("good"), _entry("bad"), _entry("also-good")])
    _install_fetch(
        monkeypatch,
        {
            "/good": (PROSE, "2026-07-01"),
            "/bad": RuntimeError("boom"),
            "/also-good": (PROSE, None),
        },
    )

    code = refresh(snapshot)
    written = json.loads(snapshot.read_text(encoding="utf-8"))

    assert code == 0
    assert {d["doc_id"] for d in written["documents"]} == {"good", "also-good"}
    # The failure is reported, not swallowed: a silent skip would let the corpus
    # quietly shrink over successive refreshes.
    out = capsys.readouterr().out
    assert "bad" in out and "boom" in out


def test_a_prose_less_page_counts_as_a_failure_not_a_source(
    tmp_path, monkeypatch, manifest, capsys
):
    """The guard that catches GOV.UK calculator pages.

    They return 200 with almost no body text. Without a floor they would enter
    the corpus as near-empty documents, and an empty document is worse than an
    absent one — it can be retrieved and cited while saying nothing.
    """
    snapshot = tmp_path / "snapshot.json"
    manifest([_entry("calculator"), _entry("real")])
    _install_fetch(
        monkeypatch,
        {"/calculator": ("x" * (MIN_TEXT_CHARS - 1), None), "/real": (PROSE, None)},
    )

    code = refresh(snapshot)
    written = json.loads(snapshot.read_text(encoding="utf-8"))

    assert code == 0
    assert {d["doc_id"] for d in written["documents"]} == {"real"}
    assert "extracted only" in capsys.readouterr().out


def test_every_document_is_stamped_with_the_fetch_date(tmp_path, monkeypatch, manifest):
    """Citations are dated, so the date has to come from the run that fetched."""
    snapshot = tmp_path / "snapshot.json"
    manifest([_entry("a")])
    _install_fetch(monkeypatch, {"/a": (PROSE, "2026-04-06")})

    refresh(snapshot)
    doc = json.loads(snapshot.read_text(encoding="utf-8"))["documents"][0]

    assert doc["fetched_at"]
    assert doc["last_updated"] == "2026-04-06"
    assert doc["url"] == "https://www.gov.uk/a"
