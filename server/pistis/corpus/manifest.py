"""Load and validate the corpus manifest.

The manifest is the single declaration of what Pistis is allowed to ground
on. Anything not in it does not exist as far as the engine is concerned.
"""

from __future__ import annotations

import json
from pathlib import Path

from pistis.models import ManifestEntry, SourceOrg

MANIFEST_PATH = Path(__file__).with_name("manifest.json")

ALLOWED_HTML_HOSTS = (
    "https://www.fca.org.uk/",
    "https://www.moneyhelper.org.uk/",
)


def load_manifest(path: Path | None = None) -> list[ManifestEntry]:
    raw = json.loads((path or MANIFEST_PATH).read_text(encoding="utf-8"))
    entries = [
        ManifestEntry(
            id=e["id"],
            domain=e["domain"],
            title=e["title"],
            org=SourceOrg(e["org"]),
            kind=e["kind"],
            locator=e["locator"],
            why=e["why"],
            licence=e.get("licence") or _default_licence(e["kind"], SourceOrg(e["org"])),
        )
        for e in raw["entries"]
    ]
    _validate(entries)
    return entries


def load_excluded(path: Path | None = None) -> list[dict]:
    """Manifest entries that are curated but deliberately NOT loaded into the
    corpus — e.g. WAF-blocked with no licensed/partnered fetch path yet. Kept
    for provenance (why they were picked, why they're excluded) rather than
    deleted outright. Not validated as ManifestEntry: some may not have a
    resolvable fetch policy. See docs/compliance-review-2026-07-21.md.
    """
    raw = json.loads((path or MANIFEST_PATH).read_text(encoding="utf-8"))
    return raw.get("excluded", [])


def _default_licence(kind: str, org: SourceOrg) -> str:
    """Best-effort licence label when an entry doesn't set one explicitly.

    Only the GOV.UK Content API (kind == "govuk", i.e. GOVUK/HMRC) is under
    the Open Government Licence v3.0. FCA and MoneyHelper pages are fetched
    as `kind == "html"` and are NOT OGL — they carry their own, more
    restrictive copyright/reuse terms. Do not widen this default without
    re-checking the source's actual terms (see compliance review).
    """
    if kind == "govuk":
        return "OGL v3.0"
    if org in (SourceOrg.MONEYHELPER, SourceOrg.PENSIONWISE):
        return (
            "MoneyHelper/MaPS copyright — non-commercial reuse only "
            "(CC BY-NC-ND 2.0 UK for downloads; partnership terms apply to "
            "republished guidance); verify before any commercial use, see "
            "moneyhelper.org.uk/en/about-us/terms-and-conditions"
        )
    if org == SourceOrg.FCA:
        return (
            "FCA copyright — personal/internal use and short incidental "
            "extracts with acknowledgement only; redistribution, data feeds "
            "or reproduction on another site require the FCA's prior "
            "written permission, see fca.org.uk/panels/legal"
        )
    return "unknown — verify licence terms before reuse"


def _validate(entries: list[ManifestEntry]) -> None:
    seen_ids: set[str] = set()
    seen_locators: set[str] = set()
    for e in entries:
        if e.id in seen_ids:
            raise ValueError(f"duplicate manifest id: {e.id}")
        if e.locator in seen_locators:
            raise ValueError(f"duplicate manifest locator: {e.locator}")
        seen_ids.add(e.id)
        seen_locators.add(e.locator)
        if e.kind == "govuk" and e.org not in (SourceOrg.GOVUK, SourceOrg.HMRC):
            raise ValueError(f"{e.id}: govuk kind requires GOVUK/HMRC org")
        if e.kind == "html" and not e.locator.startswith(ALLOWED_HTML_HOSTS):
            raise ValueError(
                f"{e.id}: html locator outside the allowed host list: {e.locator}"
            )
