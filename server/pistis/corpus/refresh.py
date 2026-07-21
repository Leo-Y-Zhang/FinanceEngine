"""Snapshot the corpus: `python -m pistis.corpus.refresh`.

Fetches every manifest entry and writes data/corpus/snapshot.json at the
repo root. Failures are reported and skipped — a partial corpus with honest
dates beats no corpus, and the gate abstains over what is missing.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from pistis.corpus.fetch import fetch_entry_text
from pistis.corpus.manifest import load_manifest
from pistis.corpus.store import Document, save_snapshot

SNAPSHOT_PATH = Path(__file__).parents[3] / "data" / "corpus" / "snapshot.json"

MIN_TEXT_CHARS = 300  # shorter than this ⇒ extraction failed, not a source


def refresh(snapshot_path: Path = SNAPSHOT_PATH) -> int:
    entries = load_manifest()
    today = date.today().isoformat()
    documents: list[Document] = []
    failures: list[str] = []

    for i, entry in enumerate(entries, 1):
        try:
            text, last_updated = fetch_entry_text(entry.kind, entry.locator)
            if len(text) < MIN_TEXT_CHARS:
                raise ValueError(f"extracted only {len(text)} chars")
            documents.append(
                Document(
                    doc_id=entry.id,
                    title=entry.title,
                    org=entry.org,
                    url=entry.url,
                    fetched_at=today,
                    last_updated=last_updated,
                    text=text,
                )
            )
            print(f"[{i}/{len(entries)}] ok    {entry.id} ({len(text)} chars)")
        except Exception as exc:  # noqa: BLE001 — report and continue
            failures.append(f"{entry.id}: {exc}")
            print(f"[{i}/{len(entries)}] FAIL  {entry.id}: {exc}")

    if not documents:
        print("No documents fetched; snapshot not written.")
        return 1

    save_snapshot(snapshot_path, documents)
    print(
        f"\nSnapshot: {len(documents)} documents -> {snapshot_path}"
        + (f"\nFailures ({len(failures)}):\n  " + "\n  ".join(failures) if failures else "")
    )
    return 0


if __name__ == "__main__":
    sys.exit(refresh())
