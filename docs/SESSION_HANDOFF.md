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
- NONE IN FLIGHT. Adversarial review (17 agents) DONE: 12 confirmed findings
  ALL FIXED and pushed (93a7278) — incl. 4 real advice-boundary escapes now
  in the red-team suite, coverage-poisoning fix, worked-example capping,
  log untracking. 104 pytest + 7 vitest green; 37/37 live goldens.
  All 12 plan tasks complete. Next session = user-directed (see queue).

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
