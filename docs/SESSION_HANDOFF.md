# SESSION_HANDOFF — Pistis

**Updated:** 2026-07-21 (session: MVP build — engine + corpus + UI shipped)

## State (all pushed to GreenPandaTech/Pistis, private)
- MVP BUILT AND VERIFIED END-TO-END: extractive gate-first engine over a
  LIVE corpus (46 docs / 1,590 passages from GOV.UK, HMRC, FCA), FastAPI
  surface, React claim-ledger UI. 86 pytest + 6 vitest (incl. axe) green.
- Live smoke: 24/24 golden questions produce the correct state
  (answer / routing / abstain). Screenshots of all three states captured
  via CDP against the real running stack.
- Calibration hardened on real data: IDF-weighted BEST-SINGLE-PASSAGE
  coverage (union coverage was exploitable by scattered incidental terms),
  plural fold, figure-bearing claim boost. Thresholds in `engine/gate.py`.
- npm audit: 0 vulnerabilities (vitest 4 bump). Dependabot alerts on GitHub
  were raised pre-fix — VERIFY they clear on rescan.
- Corpus notes: MoneyHelper (21 pages) is 403-walled (WAF) — entries stay in
  the manifest but unfetched; licensed/approved feed is the legit path.
  2 GOV.UK calculator pages have no prose body (correctly skipped).

## Exact next step
- Adversarial review workflow (run `wf_d4b042e5-b55`) was in flight at
  session end — read its confirmed findings, fix, push. Then task list
  items remaining from `docs/plans/2026-07-21-mvp-implementation-plan.md`:
  all 12 tasks done except final review-fix loop.

## Needs-you queue
1. Review the MVP scope decision (design doc §1 — shape A, extractive
   LLM-optional). Reversible.
2. Compliance/lawyer sign-off before any launch/monetisation (standing gate).
3. Claude-composer mode (optional): needs an API key via credential handoff.
4. MoneyHelper content: pursue licensed access, or drop from manifest.
5. Confirm GitHub Dependabot alerts cleared after the vitest-4 fix.

## Gates in force
- Build-only: NO deploy, NO launch, NO monetisation.
- Anonymity: GreenPandaTech noreply identity; no personal identifiers.
- Corpus content: OGL/official sources only; no scraping around WAFs.

## How to run
- Snapshot: `server/.venv/Scripts/python -m pistis.corpus.refresh`
- API: `server/.venv/Scripts/python -m uvicorn --factory pistis.api.app:create_app --port 8000`
- UI: `cd web && npm run dev` (proxies /api -> :8000)
- Tests: `server/.venv/Scripts/python -m pytest` · `cd web && npm test`
