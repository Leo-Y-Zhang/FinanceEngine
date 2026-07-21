# SESSION_HANDOFF — Pistis

**Updated:** 2026-07-21 (session 2: fixed two gaps flagged by the compliance
review — GDPR privacy notice + retention, and classifier hardening pass 2)

## Session 2 (2026-07-21) — this session's changes (local commits only)

User asked for two gaps from `docs/compliance-review-2026-07-21.md` to be
fixed directly (not just flagged for a lawyer). Both done, tested, not
pushed (push still on hold). Full addendum with details is appended to the
bottom of `docs/compliance-review-2026-07-21.md` itself — summary here:

1. **Finding #8 (no GDPR privacy notice) — closed.** Added a real, linked
   privacy notice page: `web/src/components/PrivacyNotice.tsx`, reachable
   at the `#/privacy` hash route (minimal hand-rolled routing in `App.tsx`,
   no new dependency) and linked directly from the disclaimer banner —
   covers what's logged, why, lawful basis (legitimate interests — accurate
   for this pre-launch build), retention (30 days), user rights, and a
   placeholder contact ("the site operator", no invented email/company).
   Added the retention mechanism that didn't exist before:
   `server/pistis/privacy/retention.py` (`purge_expired`), wired into
   `create_app()` to run at server startup, also runnable standalone
   (`python -m pistis.privacy.retention`). New tests:
   `server/tests/test_retention.py` (6 tests) + 1 startup-integration test
   in `test_api.py` + `web/src/__tests__/PrivacyNotice.test.tsx` (3 tests,
   incl. axe) + 2 new cases in `App.test.tsx`.
2. **Finding #1 (classifier false-negative tail) — narrowed, not closed
   (not closable by construction; documented as such).** Adversarial
   hardening pass 2 in `server/pistis/engine/classifier.py`: 5 new
   paraphrase categories covered — third-person/on-behalf-of framing
   ("my friend wants to know if she should..."), hypothetical
   self-insertion ("if you were me...", "in my shoes..."), informal/slang
   framing ("the move", "no-brainer", "good shout"), ESL-style polite
   requests ("please suggest me...", "kindly advise..."), and broadened
   comparative adjectives (smarter/safer/wiser). Each new fixture was
   verified against the *pre-hardening* patterns first to confirm it was a
   genuine escape, not a re-labelled existing catch. Red-team suite grew
   27/13 → 44/17 (17 new positive, 4 new boundary-probe negative), all
   green. The compliance-doc addendum is explicit that a residual,
   irreducible gap remains by design of the regex approach — a future
   small classifier model is the suggested durable fix, not in scope here.
3. **Full suite green after both changes**: 137 pytest (was 109) + 12
   vitest (was 7).

---

*(Session 1, same date, earlier — prior changes below)*

## State (local commits only — NOT pushed; see "Push status" below)
- MVP BUILT AND VERIFIED END-TO-END: extractive gate-first engine over a
  LIVE corpus (46 docs fetched to date / 1,590 passages from GOV.UK, HMRC,
  FCA), FastAPI surface, React claim-ledger UI.
- Live smoke (prior session): 24/24, then 37/37, golden questions produce
  the correct state (answer / routing / abstain).
- Calibration hardened on real data: IDF-weighted BEST-SINGLE-PASSAGE
  coverage, plural fold, figure-bearing claim boost. Thresholds in
  `engine/gate.py`.
- **This session's changes (all local-commit only, see below):**
  1. **MVP scope decision (design doc §1) — reviewed by an automated
     compliance pass** (`docs/compliance-review-2026-07-21.md`). The shape-A
     decision itself (gate-first, extractive-core, LLM-optional) was already
     made autonomously in the prior session under standing autonomy
     directives and is reversible; this session added an informal,
     non-lawyer compliance triage of that decision and the live product.
     **This is NOT a substitute for the required qualified-solicitor
     sign-off** (still gated, see queue) — it's a head start for that
     review, and the scope decision itself still needs your own read/OK.
  2. **Compliance review doc added**: `docs/compliance-review-2026-07-21.md`.
     Covers FCA perimeter (Art 53 RAO / s21 FSMA), content licensing
     (OGL/FCA/MoneyHelper), UK GDPR, disclaimer prominence, and
     accessibility beyond axe. Top 3 findings for a real lawyer: (1) FCA
     copyright terms may require written permission for Pistis's
     verbatim-extraction pattern — genuine judgement call, not code; (2) the
     rule-based advice-boundary classifier has an inherent, unbounded
     false-negative tail — sound architecture, but "how much red-team
     coverage is enough" is a lawyer/product call; (3) no UK GDPR privacy
     notice yet for the local question log (low risk today since it's
     undeployed and gitignored, but needed before any real launch).
     One real bug found and **fixed** in-session: the manifest was silently
     defaulting *every* source's licence label to "OGL v3.0," including FCA
     HTML entries which are not OGL — fixed in `corpus/manifest.py`
     (`_default_licence()`), with new regression tests.
  3. **MoneyHelper manifest decision made.** Quick check found MoneyHelper
     does run a free content-partnership programme for republishing its
     guidance (`moneyhelper.org.uk/en/about-us/partnerships/overview`) —
     genuinely worth pursuing later, but that's a build task, not something
     to wire up unilaterally (flagged in the queue below). No free API/data
     feed was found. Since there's still no licensed fetch path and the
     "no scraping around WAFs" gate stands, the 21 MoneyHelper-hosted
     entries (20 org=MoneyHelper + 1 org=PensionWise, all on
     moneyhelper.org.uk) were moved out of the live `entries` array in
     `corpus/manifest.json` into a new `excluded` array (status +
     reason preserved, so the curation work isn't lost — see
     `manifest.load_excluded()`). `entries` is now 48 (was 69). Nothing
     else referenced the removed entries; 109 pytest + 7 vitest all green
     after the change.
  4. **Dependabot re-checked** via `gh api .../dependabot/alerts`
     (read-only): all 5 alerts (esbuild, vite x3, vitest) show
     `state: fixed`, 0 currently open. The prior session's vitest-4 bump
     did clear them — confirmed, not just assumed.
- Corpus notes: 2 GOV.UK calculator pages have no prose body (correctly
  skipped, pre-existing).

## Push status
**Pushing to GitHub is ON HOLD per current user instruction** (recent
free-tier limit) — this session's changes are **local commits only**.
Nothing in this session was pushed to GreenPandaTech/Pistis. Push when
the user says so.

## Exact next step
- NONE IN FLIGHT. Session 2's work (privacy notice + retention purge +
  classifier hardening pass 2) is committed locally, not pushed. Next
  session = user-directed (see queue) — most likely either a real lawyer's
  pass informed by `docs/compliance-review-2026-07-21.md` (now including
  the 2026-07-21 addendum), or continuing to build (e.g. MoneyHelper
  partnership integration, staleness policy, disclaimer visual prominence).

## Needs-you queue
1. Give your own read/OK on the MVP scope decision (design doc §1 — shape
   A, extractive/LLM-optional). Reversible; the automated compliance pass
   above is a head start, not your sign-off.
2. Compliance/lawyer sign-off before any launch/monetisation (standing
   gate) — start from `docs/compliance-review-2026-07-21.md`; top item for
   the lawyer is the FCA content-reuse question (finding #6 in that doc).
3. Claude-composer mode (optional): needs an API key via credential
   handoff. Note: `pistis/providers/` is currently an empty directory —
   this mode isn't stubbed yet, it's a from-scratch build.
4. MoneyHelper content: a free partnership/republishing programme appears
   to exist (`moneyhelper.org.uk/en/about-us/partnerships/overview`) —
   worth a build session to integrate properly (terms, attribution,
   possible NC restriction on downloadable material vs. any future
   monetisation) rather than the current WAF-blocked dead end. 21 entries
   are parked in `manifest.json`'s `excluded` array pending this.
5. ~~Confirm GitHub Dependabot alerts cleared~~ DONE this session — 0 open.
6. Decide on disclaimer visual prominence (compliance doc finding #9) and
   a staleness policy for old corpus snapshots (finding #10) — product
   calls, not legal ones, but worth deciding before launch.

## Gates in force
- Build-only: NO deploy, NO launch, NO monetisation.
- Anonymity: GreenPandaTech noreply identity; no personal identifiers.
- Corpus content: OGL/official sources only; no scraping around WAFs.
- Push-to-GitHub: ON HOLD per current user instruction (see "Push status").

## How to run
- Snapshot: `server/.venv/Scripts/python -m pistis.corpus.refresh`
- API: `server/.venv/Scripts/python -m uvicorn --factory pistis.api.app:create_app --port 8000`
  (also purges expired `logs/ask.jsonl` entries on startup — see
  `pistis/privacy/retention.py`)
- UI: `cd web && npm run dev` (proxies /api -> :8000); privacy notice at
  `#/privacy` or via the link in the disclaimer banner
- Tests: `server/.venv/Scripts/python -m pytest` · `cd web && npm test`
- Manual log purge (optional — startup already does this):
  `server/.venv/Scripts/python -m pistis.privacy.retention`
