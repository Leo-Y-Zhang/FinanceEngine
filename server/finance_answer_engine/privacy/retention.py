"""Retention/purge logic for the local question log (`logs/ask.jsonl`).

Compliance context: `docs/compliance-review-2026-07-21.md` finding #8 flagged
that `logs/ask.jsonl` (every question, its outcome kind, and a timestamp —
see `finance_answer_engine.api.app.log_outcome`) had no defined retention or purge policy.
The user-facing privacy notice (`web/src/components/PrivacyNotice.tsx`)
promises a 30-day retention period; this module is what actually enforces
it. `create_app()` calls `purge_expired()` once at startup so the promise
holds without needing a separate cron job or scheduler for this pre-launch,
single-machine build. For manual/scheduled use there is also a CLI entry
point: `python -m finance_answer_engine.privacy.retention`.
"""

from __future__ import annotations

import json
import time
import warnings
from pathlib import Path

RETENTION_DAYS = 30
RETENTION_SECONDS = RETENTION_DAYS * 24 * 60 * 60


def purge_expired(
    log_path: Path,
    retention_seconds: float = RETENTION_SECONDS,
    now: float | None = None,
) -> int:
    """Rewrite ``log_path`` keeping only entries newer than the retention window.

    Returns the number of entries removed. A missing or empty file is a
    no-op. Lines that cannot be parsed as a JSON object with a numeric
    ``ts`` field are treated as expired (dropped) rather than raising —
    this is a best-effort hygiene pass over an append-only log, not a
    strict schema validator.
    """
    if not log_path.exists():
        return 0

    now = time.time() if now is None else now
    cutoff = now - retention_seconds

    try:
        text = log_path.read_text(encoding="utf-8-sig")
    except (UnicodeDecodeError, OSError) as exc:
        # This pass runs at server startup, so raising here would stop the
        # service starting at all over one corrupt byte in a local log. Warn
        # loudly and change nothing: rewriting a file we could not fully read
        # would be the worse failure, since the lines we could not decode are
        # exactly the ones we would silently drop.
        warnings.warn(
            f"ask-log retention skipped: cannot read {log_path}: {exc}",
            RuntimeWarning,
            stacklevel=2,
        )
        return 0

    kept: list[str] = []
    removed = 0
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            ts = float(record["ts"])
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            removed += 1
            continue
        if ts >= cutoff:
            kept.append(line)
        else:
            removed += 1

    if removed:
        log_path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")

    return removed


def purge_expired_default() -> int:
    """Purge the default `logs/ask.jsonl` path used by the running app."""
    from finance_answer_engine.api.app import DEFAULT_LOG

    return purge_expired(DEFAULT_LOG)


if __name__ == "__main__":
    removed_count = purge_expired_default()
    plural = "y" if removed_count == 1 else "ies"
    print(f"Purged {removed_count} log entr{plural} older than {RETENTION_DAYS} days.")
