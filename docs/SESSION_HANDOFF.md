# SESSION_HANDOFF — Pistis

**Updated:** 2026-07-24 (session 6: corpus-gap report — the refusals turned into
a keyless, privacy-safe corpus-expansion backlog; all green, pushed)

## Session 6 (2026-07-24) — Corpus-gap report (refusals as a roadmap)

User directive: proceed on the open items but keep everything **free/keyless**,
skip the lawyer gate, and drop the paid-API-key LLM composer. Honest call on the
composer: a real composer's value is LLM fluency (needs a paid Anthropic key —
no free API tier; local models are blocked on this locked-down box), and a
*keyless* composer could only re-arrange source text, risking connective prose
that implies unsourced relationships — exactly what this extractive product
avoids. So the composer was **deliberately not built** (would be low-value
make-work), and the MVP-scope decision is treated as user-approved (private
build). Delivered the one genuinely valuable keyless item instead.

**What shipped:** `server/pistis/gaps.py` + `python -m pistis.gaps` — replays the
local ask-log through the engine, aggregates each abstention's `uncovered_terms`,
and ranks the concepts users most ask about that no trusted source covers = a
corpus-expansion backlog. **Privacy by construction:** aggregate-only (raw
questions never leave the function; no question field on the report), a
**k-anonymity floor** (`--min-distinct`, default 2) withholds any concept in
fewer than N distinct questions, bare numbers/amounts dropped, deterministic +
offline. Re-asks against the *current* corpus, so a filled gap stops appearing.
`GapReport`/`GapConcept` dataclasses; `--json` for a machine record; sibling to
`eval.py` (eval proves the promise, gaps turns refusals into a roadmap).

**Verification:** server **185 -> 194 pytest** green (9 new in `test_gaps.py`
covering ranking, the floor, dedup, numeric filtering, the no-leak privacy
invariant, malformed-line tolerance, missing-log, and the CLI). Keyless/offline;
web untouched (this is an ops/analytics CLI, deliberately not a public surface).
Reviewed manually + via the 9 targeted tests (incl. the no-leak privacy
invariant, the floor crossing, dedup, numeric filtering); the full multi-agent
adversarial review was deferred (context budget) — worth running on resume.

---

## Session 5 (2026-07-24) — Explainable Refusal

Standout feature completing the thesis's other half: Pistis already *proved its
answers* (trust report + freshness); now it *proves its refusals* too. Built
autonomously under the standing directive; pushed to GreenPandaTech/Pistis,
each increment green. Design spec:
`docs/superpowers/specs/2026-07-24-explainable-refusal-design.md`.

**What shipped (commits on main):**
1. `feat:` explainable-refusal server layer — `332f20b`. Every refusal carries
   an `AbstentionReport` (models.py: `SignalCheck` + `AbstentionReport`,
   `Abstention.report` optional/additive): the gate stage that fired
   (`no_source` / `weak_coverage` / `no_groundable_statement` /
   `empty_question`), each answerability signal vs its threshold, and the
   specific query terms no trusted source covers. `bm25.py` gains
   `Bm25Index.uncovered_terms` (query words whose every token is absent from the
   top passages, rarest-first) with shared `_passage_vocab`/`_query_words`
   helpers; `coverage()` refactored onto the same vocab. Gate builds the report
   in all three refusal branches (existing `reason` strings unchanged). `eval.py`
   adds **refusals-explained** as a first-class honesty metric folded into PASS.
2. `feat:` explainable-refusal web UI — `8b2696e`. `RefusalCard` shows the
   report explanation as the specific reason plus uncovered-concept chips and
   per-signal meters (value/threshold, pass/fail) in the trust/freshness chip
   language; `types.ts` mirrors the shapes.
3. `docs:` README section + design spec + this handoff.
4. `fix:` adversarial-review fixes — `6d06b99`. An 11-agent four-lens review
   (correctness / honesty-posture / web-a11y / test-quality), each finding
   verified. **Honesty-posture lens found nothing** (the additive-safety
   invariant held under attack). 7 confirmed findings all fixed: one real
   display bug (a SignalCheck showed `round(value)` while deriving `passed` from
   the raw score, so a 0.599 coverage could render "0.6 / 0.6 needed" yet marked
   failed — the shown value can now never contradict its marker), one web nit
   (empty diagnostics container on a stopword-only refusal), five test-coverage
   gaps closed (the untested `no_groundable_statement` stage + both-signals path;
   `_phrase_terms` overflow; the signal invariant; a self-fulfilling test).

**Safety property (verified):** strictly additive — touches only the refusal
paths, never answer emission, the thresholds, or the faithfulness verifier, so
it cannot turn a refusal into an answer. Confirmed end-to-end: an answer
response carries no `report` key at all.

**Verification:** server **165 -> 185 pytest** green; honesty eval **PASS,
refusals explained 4/4**; web **15 -> 17 vitest** green; `tsc` + `vite build`
clean; **END-TO-END over real HTTP** (uvicorn + JSON on the fixture snapshot):
`no_source` and `weak_coverage` refusals serialise their report, an answer
carries none. Pistis GitHub Actions are disabled; pushes are safe (not an
auto-deploy repo).

**Next options (unchanged, all still gated / need a human decision):** MVP-scope
sign-off, lawyer sign-off (FCA reuse #6), the Claude-composer build (needs an
API key), the MoneyHelper partnership. New optional idea: run `uncovered_terms`
telemetry over the ask log to surface the most-requested *uncovered* concepts —
a keyless, privacy-safe backlog of what to add to the corpus next.

---

## Session 4 (2026-07-24) — compliance close-out (autonomous, non-legal)

Swept the open compliance-review findings and closed the two that were
closable without a lawyer or product-owner decision. Nothing legal/product
was pre-empted; the FCA content-reuse (#6), GDPR (#8), disclaimer-prominence
(#9), and manual-a11y (#11/#12) items still need their respective reviewers.

- **Finding #5 (OGL acknowledgement only in README) — closed.** Added a
  permanent OGL v3.0 acknowledgement + source-copyright line to the live UI
  footer (`web/src/App.tsx` + `.site-footer` CSS), with a new `App.test.tsx`
  case and existing axe coverage. Web suite 14 → **15 vitest** green; `tsc` +
  `vite build` clean.
- **Finding #3 (spec `providers/` path does not exist) — closed.** Marked
  spec §2.4 "Implementation status: NOT BUILT" and corrected §2.3's phantom
  `composer.py` reference to the real `engine/answer.py`. No code built —
  `providers/` intentionally still absent (extractive-only MVP).
- **Finding #10 (staleness policy)** was already delivered by the 2026-07-23
  freshness layer — noted here for the record.
- **Dependabot re-verified**: `gh api .../dependabot/alerts` → 5 alerts, all
  `state: fixed`, **0 open**. Server baseline re-run: **165 pytest** green.

Still open for you (unchanged, all need a human decision — see queue below):
MVP-scope sign-off, lawyer sign-off (FCA reuse #6 is the top item), the
Claude-composer build (needs an API key), and the MoneyHelper partnership.

---

## Session 3 (2026-07-23) — Provenance & Faithfulness Layer

Standout feature making the thesis *software that proves its own claims*
literal, visible, and measurable. Built autonomously (owner offline, under the
standing autonomous-work directive); pushed to GreenPandaTech/Pistis, each
increment green. Design spec:
`docs/superpowers/specs/2026-07-23-provenance-faithfulness-design.md`.

**What shipped (commits on main):**
1. `docs:` design spec — `5b9a0cf`.
2. `feat:` per-claim faithfulness verifier + trust report — `68d93dc`.
   `engine/faithfulness.py` grounds each claim's text against its source
   passage (verdict + score + char span). The gate now EMITS ONLY GROUNDED
   claims (new emission guard). `AnswerCard` gains an optional `trust_report`
   plus a strengthened invariant — an ungrounded claim cannot be constructed.
   `models.py` adds `ClaimVerdict` / `TrustReport`; the API surfaces it via
   `asdict` (additive, no schema break, existing tests unaffected).
3. `feat:` reproducible honesty-eval CLI `python -m pistis.eval` — `0fe08ff`.
   Over `server/tests/fixtures/golden.json` (21 questions): 100% answerability,
   41/41 claims grounded, 0 unsupported → PASS. Deterministic + offline;
   `--snapshot` to evaluate the live corpus; `--json` for a machine record.
4. `feat:` web trust-report UI — `72df5e9`. Per-claim "grounded in source" chip
   + overall "N of N statements grounded in their cited source" summary in the
   claim ledger; `web/src/types.ts` mirrors the new shapes; matching CSS.
5. `docs:` README + this handoff — `47f007f`.
6. `feat:` **source-staleness policy** — `fbf215a`. `engine/freshness.py` — a
   keyless, deterministic check that flags a claim naming a PAST UK tax year
   (finance is tax-year-bound) or from an aged snapshot, against a reference
   date (today in prod, pinned in tests). `models.py` adds `Freshness` /
   `FreshnessReport`; `Engine.ask(question, reference_date=None)` attaches a
   `freshness` report to every answer; API auto-serialises it.
7. `feat:` web freshness UI — `87b308d`. Per-claim past-tax-year / aged-source
   chip + a stale-answer caveat.

**Live-corpus production honesty number (2026-07-23):** rebuilt the live
snapshot (`python -m pistis.corpus.refresh` → 46 docs, gitignored) and ran
`python -m pistis.eval --snapshot ...` → **21/21 answerability, 42/42 claims
grounded, 0 unsupported → PASS** on real GOV.UK/HMRC/FCA data. End-to-end over
real HTTP confirmed both layers: an answer returns `trust_report` (6/6 grounded)
+ `freshness` (overall current, tax-year 2026-27 detected + recognised current,
0 false positives). LLM composer left for later — it needs an ANTHROPIC_API_KEY
via the credential-handoff process (the faithfulness verifier already guards its
output). Add via `providers/` when the key is supplied.

**Verification:** server **165 pytest** (was 137) + web **14 vitest** (was 12),
all green; web `tsc` + `vite build` clean; **END-TO-END over real HTTP**
(uvicorn + curl on the fixture snapshot): an answer returns `trust_report` with
per-claim grounded verdicts + source spans, while routing/abstain carry none.
Pistis GitHub Actions are disabled (no CI trigger); pushes are safe (not an
auto-deploy repo).

**Next options:** run the eval against the live corpus for a production honesty
number; add the LLM composer behind `providers/` (the verifier already guards
its output); staleness policy; MoneyHelper partnership integration.

---
*(Sessions 2 and 1 below — unchanged.)*

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
