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
            licence=e.get("licence", "OGL v3.0"),
        )
        for e in raw["entries"]
    ]
    _validate(entries)
    return entries


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
