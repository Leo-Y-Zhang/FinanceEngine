import pytest

from finance_engine.models import (
    DISCLAIMER,
    AnswerCard,
    Citation,
    Claim,
    ManifestEntry,
    SourceOrg,
)


def make_claim(**overrides):
    citation = Citation(
        org=SourceOrg.GOVUK,
        title="Test",
        url=overrides.pop("url", "https://www.gov.uk/test"),
        fetched_at=overrides.pop("fetched_at", "2026-07-21"),
    )
    return Claim(text="A claim.", citation=citation, confidence="established")


def test_answer_card_requires_claims():
    with pytest.raises(ValueError, match="at least one claim"):
        AnswerCard(question="q", claims=())


def test_answer_card_rejects_undated_citation():
    with pytest.raises(ValueError, match="dated, linked citation"):
        AnswerCard(question="q", claims=(make_claim(fetched_at=""),))


def test_answer_card_rejects_unlinked_citation():
    with pytest.raises(ValueError, match="dated, linked citation"):
        AnswerCard(question="q", claims=(make_claim(url=""),))


def test_answer_card_carries_disclaimer():
    card = AnswerCard(question="q", claims=(make_claim(),))
    assert card.disclaimer == DISCLAIMER
    assert "not regulated financial advice" in card.disclaimer


def test_manifest_entry_govuk_locator_must_be_path():
    with pytest.raises(ValueError, match="content path"):
        ManifestEntry(
            id="x", domain="tax", title="T", org=SourceOrg.HMRC,
            kind="govuk", locator="https://www.gov.uk/x", why="w",
        )


def test_manifest_entry_html_locator_must_be_https():
    with pytest.raises(ValueError, match="https URL"):
        ManifestEntry(
            id="x", domain="tax", title="T", org=SourceOrg.FCA,
            kind="html", locator="/not-a-url", why="w",
        )


def test_manifest_entry_url_resolution():
    e = ManifestEntry(
        id="isa", domain="savings_isas", title="ISAs", org=SourceOrg.GOVUK,
        kind="govuk", locator="/individual-savings-accounts", why="w",
    )
    assert e.url == "https://www.gov.uk/individual-savings-accounts"
