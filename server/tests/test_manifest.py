import json

import pytest

from finance_engine.corpus.manifest import load_excluded, load_manifest


def write_manifest(tmp_path, entries):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({"entries": entries}), encoding="utf-8")
    return p


BASE = {
    "id": "tax-income-tax",
    "domain": "tax",
    "title": "Income Tax rates",
    "org": "HMRC",
    "kind": "govuk",
    "locator": "/income-tax-rates",
    "why": "primary source for rates",
}


def test_loads_valid_manifest(tmp_path):
    entries = load_manifest(write_manifest(tmp_path, [BASE]))
    assert entries[0].id == "tax-income-tax"
    assert entries[0].licence == "OGL v3.0"


def test_rejects_duplicate_ids(tmp_path):
    dup = dict(BASE, locator="/other-path")
    with pytest.raises(ValueError, match="duplicate manifest id"):
        load_manifest(write_manifest(tmp_path, [BASE, dup]))


def test_rejects_duplicate_locators(tmp_path):
    dup = dict(BASE, id="tax-other")
    with pytest.raises(ValueError, match="duplicate manifest locator"):
        load_manifest(write_manifest(tmp_path, [BASE, dup]))


def test_rejects_govuk_kind_with_fca_org(tmp_path):
    bad = dict(BASE, org="FCA")
    with pytest.raises(ValueError, match="govuk kind requires"):
        load_manifest(write_manifest(tmp_path, [bad]))


def test_rejects_html_host_outside_allowlist(tmp_path):
    bad = dict(
        BASE, org="FCA", kind="html",
        locator="https://www.moneysavingexpert.com/banking/",
    )
    with pytest.raises(ValueError, match="allowed host list"):
        load_manifest(write_manifest(tmp_path, [bad]))


def test_fca_html_entries_are_not_defaulted_to_ogl(tmp_path):
    # FCA/MoneyHelper pages are fetched as kind=="html" and are NOT under the
    # Open Government Licence — only the GOV.UK Content API (kind=="govuk")
    # is. Regression guard for a real mislabelling bug found in compliance
    # review: every entry was silently defaulting to "OGL v3.0".
    fca = dict(
        BASE, id="tax-fca-note", org="FCA", kind="html",
        locator="https://www.fca.org.uk/consumers/protect-yourself-scams",
    )
    entries = load_manifest(write_manifest(tmp_path, [fca]))
    assert "OGL" not in entries[0].licence
    assert "FCA" in entries[0].licence


def test_moneyhelper_html_entries_are_not_defaulted_to_ogl(tmp_path):
    mh = dict(
        BASE, id="tax-mh-note", org="MoneyHelper", kind="html",
        locator="https://www.moneyhelper.org.uk/en/savings/types-of-savings/cash-isas",
    )
    entries = load_manifest(write_manifest(tmp_path, [mh]))
    assert "OGL" not in entries[0].licence
    assert "MoneyHelper" in entries[0].licence


def test_explicit_licence_is_respected(tmp_path):
    entries = load_manifest(write_manifest(tmp_path, [dict(BASE, licence="custom")]))
    assert entries[0].licence == "custom"


def test_load_excluded_returns_moneyhelper_waf_blocked_entries():
    excluded = load_excluded()
    assert len(excluded) == 21
    assert all("moneyhelper.org.uk" in e["locator"] for e in excluded)
    assert all(e["status"] == "excluded" for e in excluded)


def test_real_manifest_no_longer_lists_moneyhelper_as_fetchable():
    entries = load_manifest()
    live_moneyhelper = [e for e in entries if "moneyhelper.org.uk" in e.locator]
    assert live_moneyhelper == []
