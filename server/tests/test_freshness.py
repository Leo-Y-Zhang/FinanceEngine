"""Source-staleness: is the cited source still current?

A claim can be perfectly grounded yet name a past UK tax year, or come from an
aged snapshot. This suite pins the deterministic freshness assessment.
"""

from datetime import date

from pistis.engine.freshness import assess, current_tax_year_start
from pistis.models import Citation, Freshness, FreshnessReport, SourceOrg

# 1 September 2026 falls in the 2026-27 UK tax year (started 6 Apr 2026).
REF = date(2026, 9, 1)


def _cite(fetched_at: str = "2026-07-23") -> Citation:
    return Citation(
        org=SourceOrg.GOVUK, title="T", url="https://www.gov.uk/t",
        fetched_at=fetched_at, last_updated="2026-04-06",
    )


def test_current_tax_year_start_boundary():
    assert current_tax_year_start(date(2026, 4, 6)) == 2026
    assert current_tax_year_start(date(2026, 4, 5)) == 2025
    assert current_tax_year_start(date(2026, 12, 31)) == 2026
    assert current_tax_year_start(date(2026, 1, 1)) == 2025


def test_current_tax_year_claim_is_current():
    f = assess(
        "In the 2026 to 2027 tax year the ISA allowance is £20,000.",
        _cite("2026-09-01"), REF,
    )
    assert f.verdict == "current"
    assert f.tax_year == "2026-27"
    assert f.tax_year_current is True
    assert f.snapshot_age_days == 0


def test_past_tax_year_claim_is_stale():
    f = assess(
        "In the 2024 to 2025 tax year the ISA allowance was £20,000.", _cite(), REF
    )
    assert f.verdict == "stale"
    assert f.tax_year == "2024-25"
    assert f.tax_year_current is False


def test_future_tax_year_claim_is_not_stale():
    f = assess("From the 2027 to 2028 tax year the rules change.", _cite(), REF)
    assert f.tax_year == "2027-28"
    assert f.tax_year_current is True
    assert f.verdict == "current"


def test_slash_and_dash_tax_year_formats():
    assert assess("the 2024/25 allowance", _cite(), REF).tax_year == "2024-25"
    assert assess("the 2024-25 allowance", _cite(), REF).tax_year == "2024-25"
    assert assess("the 2024/2025 allowance", _cite(), REF).tax_year == "2024-25"


def test_currency_amount_is_not_mistaken_for_a_tax_year():
    f = assess("You can save up to £20,000 each year.", _cite("2026-09-01"), REF)
    assert f.tax_year is None
    assert f.verdict == "current"


def test_aged_snapshot_without_tax_year():
    aging = assess("Investment scams are hard to spot.", _cite("2026-01-01"), REF)
    assert aging.verdict == "aging"  # ~243 days old
    assert aging.tax_year is None
    stale = assess("Investment scams are hard to spot.", _cite("2024-01-01"), REF)
    assert stale.verdict == "stale"  # > 365 days old


def test_freshness_report_aggregation():
    r = FreshnessReport.from_items(
        [
            Freshness("current", 0),
            Freshness("stale", 0, "2024-25", False),
            Freshness("aging", 200),
        ]
    )
    assert r.overall == "stale"
    assert r.stale_count == 1
    assert len(r.per_claim) == 3

    assert (
        FreshnessReport.from_items(
            [Freshness("current", 0), Freshness("aging", 200)]
        ).overall
        == "aging"
    )
    assert FreshnessReport.from_items([]).overall == "current"


# --- engine integration ---

def test_answer_carries_freshness_report(engine):
    resp = engine.ask("What is the annual ISA allowance?", reference_date=REF)
    assert resp.kind == "answer"
    assert resp.freshness is not None
    assert len(resp.freshness.per_claim) == len(resp.claims)


def test_far_future_reference_makes_answer_stale_by_snapshot_age(engine):
    resp = engine.ask("What is the annual ISA allowance?", reference_date=date(2035, 1, 1))
    assert resp.kind == "answer"
    assert resp.freshness.overall == "stale"
