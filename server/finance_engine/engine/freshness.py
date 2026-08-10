"""Deterministic source-staleness assessment.

Faithfulness answers "is this claim in the source?"; freshness answers "is the
source still current?". UK personal finance is tax-year-bound, so a claim that
names a *past* tax year (last year's ISA allowance, say) is faithful to its
source yet potentially out of date — this flags it rather than presenting it as
fresh. Also flags claims from an aged snapshot.

Pure and deterministic: the caller passes a reference date (production uses
today; tests pin it), so there is no hidden clock.
"""

from __future__ import annotations

import re
from datetime import date

from finance_engine.models import Citation, Freshness

# UK tax year runs 6 April Y -> 5 April Y+1.
_TAX_YEAR_START_MONTH_DAY = (4, 6)

# Snapshot-age tiers (days since the source was fetched).
AGING_DAYS = 180
STALE_DAYS = 365

# "2026 to 2027", "2026/27", "2026/2027", "2026-27", "2026–27".
_TAX_YEAR = re.compile(r"\b(20\d{2})\s*(?:to|/|-|–|—)\s*(?:20)?\d{2}\b")

# "6 April 2026 to 5 April 2027" -- GOV.UK's own canonical way of writing a tax
# year, and the form most likely to appear in the very sources this engine is
# built to quote. The short pattern above cannot match it: after "to" it needs
# two digits and finds "5 April", so the whole span reads as no tax year at all
# and a claim about a PAST year is presented as current. Tried first because it
# is the more specific shape.
_TAX_YEAR_LONG = re.compile(
    r"\b\d{1,2}\s+April\s+(20\d{2})\s*(?:to|-|–|—)\s*\d{1,2}\s+April\s+20\d{2}\b",
    re.IGNORECASE,
)


def current_tax_year_start(reference_date: date) -> int:
    """The calendar year in which the current UK tax year began."""
    if (reference_date.month, reference_date.day) >= _TAX_YEAR_START_MONTH_DAY:
        return reference_date.year
    return reference_date.year - 1


def _detect_tax_year_start(text: str) -> int | None:
    match = _TAX_YEAR_LONG.search(text) or _TAX_YEAR.search(text)
    return int(match.group(1)) if match else None


def _parse_iso_date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value[:10]) if value else None
    except (ValueError, TypeError):
        return None


def assess(claim_text: str, citation: Citation, reference_date: date) -> Freshness:
    fetched = _parse_iso_date(citation.fetched_at)
    age_days = max((reference_date - fetched).days, 0) if fetched else 0

    tax_year_start = _detect_tax_year_start(claim_text)
    tax_year_label: str | None = None
    tax_year_current: bool | None = None
    if tax_year_start is not None:
        tax_year_label = f"{tax_year_start}-{str(tax_year_start + 1)[-2:]}"
        tax_year_current = tax_year_start >= current_tax_year_start(reference_date)

    if tax_year_current is False or age_days > STALE_DAYS:
        verdict = "stale"
    elif age_days > AGING_DAYS:
        verdict = "aging"
    else:
        verdict = "current"

    return Freshness(
        verdict=verdict,
        snapshot_age_days=age_days,
        tax_year=tax_year_label,
        tax_year_current=tax_year_current,
    )
