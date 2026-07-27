# SESSION_HANDOFF — Pistis

**Updated:** 2026-07-27 (session 9: finished the in-flight answerability
benchmark - it found three defects in its own validator, one false label, and a
live advice-boundary escape; all green, pushed)

## Session 9 (2026-07-27) — the answerability benchmark, finished and run in anger

**Picked up work left uncommitted when the previous session ended.** The working
tree held `server/pistis/bench.py` plus `tests/fixtures/bench_build.py` and
`bench.json` — written, but never run, never tested, and never committed. It is
now all three. Commits `6976d62` (benchmark) and `2aed2f0` (the escape it found).

**What it is.** `pistis.eval` proves every *emitted* claim is grounded. It never
measured the **gate**, which is where the product's central claim lives.
`python -m pistis.bench` scores 131 labelled questions and reports the two
failures separately — never averaged into one accuracy figure, because that
would hide a serious failure inside a mild one — under a stated 5x cost model,
broken down by difficulty. No label comes from Pistis's output; each is derived
from the corpus or the question's form, and `--validate` re-checks every one
against the current corpus so labels cannot rot as it grows. The CLI **refuses
to score** against labels known to be broken.

### Running `--validate` for the first time found six problems — and three were the validator's own

1. **Aboutness counted MENTIONS while its name and docstring both said
   PASSAGES.** One passage about visa *scams* says "visa" three times, which is
   not the corpus knowing how to apply for a spouse visa. Now counts distinct
   passages — which is exactly what the docstring's own measurement had said
   separates incidental terms (1-2 passages) from real coverage (FSCS: a title
   AND 5 passages). The code simply never implemented what it described.
2. **Probes matched whole words only**, so "bill" did not match "bills" and
   "categor" did not match "categories" — three perfectly true labels reported as
   broken. Now word-START prefix matching, which keeps the anchor that stops
   "roth" matching inside "growth" while letting morphology through. False alarms
   are not free: a validator that cries wolf every time the corpus grows is one
   the operator learns to skip, which costs exactly the protection it exists for.
3. **A run that answered nothing reported 100% grounded.** 0 of 0 is an absent
   measurement, not a perfect score. Reports `n/a` now. Same class of bug session
   7 fixed in `gaps.py`; it had been reintroduced here.

The other three were labels, adjudicated by reading the corpus: visa and Rent a
Room stay `abstain` (both were heuristic false positives), while **salary
sacrifice was genuinely mislabelled** — the corpus explains it across two
passages ("you give up part of your salary and your employer pays this straight
into your pension"), below the 3-passage floor, so the automatic check passed it
and a human read caught it. Relabelled to `answer` and *recorded as such* in
`bench_build.py`, because a benchmark that drops its own inconvenient findings is
worthless. That limit is now written into the honest-limitations section: a clean
`--validate` means "no label has rotted", not "every label is right".

### The measurement, including the part that is unflattering

    Questions 131 · snapshot 2026-07-27 (53 docs)
    False answers   : 12 of 50  (24.0%)   <-- the failure that matters
    False refusals  :  4 of 81  ( 4.9%)
    Advice routing  : 18/18      Answers fully grounded: 89/89

**All 12 false answers are in the adversarial `near_miss` class, and every one
is perfectly grounded.** Of the 24 near-miss questions it should refuse, it
answers **12 — exactly half**. Asked "How is cryptocurrency taxed?" it returns a
correctly-cited, faithfully-extracted claim about *inheritance-tax taper relief*.
Asked for the Bank of England base rate it returns a tracker-mortgage passage
that mentions the base rate without ever stating it.

The important finding is not the number, it is *what the number proves*: the
faithfulness verifier caught **none** of these (`of those, ungrounded: 0`),
because **grounded is not the same property as relevant**. The verifier checks a
claim against the passage it came from; it never asks whether that passage
answers the question asked. The second line of defence does not cover this
failure mode at all, and now there is evidence rather than an assumption.

### An advice-boundary escape, found and closed (`2aed2f0`)

The benchmark caught a real one on its first run: **"Is a Lifetime ISA worth it
for me?" was ANSWERED** while "is *it* worth it for me" routed — the `worth-it`
rule recognised only a pronoun subject, so the identical ask about a named
product slipped through. This is the FCA-perimeter classifier failing at exactly
what it exists for, and it is a concrete instance of the "irreducible
false-negative tail" the compliance doc describes in the abstract. Fixed with one
alternative (bare "worth it"). Five red-team positives added, each verified
against the pre-fix pattern set first to confirm a genuine escape not caught by
another rule; four negative boundary probes added alongside, because "worth"
*without* "it" is a valuation question ("how much is my pension pot worth?") that
must stay answerable. Classifier suite 63 -> 72.

### Exact next step — and what NOT to do

**Do not nudge the gate thresholds to chase the 24%.** Session 8 settled the
principle for the stemmer and it applies here with more force: `MIN_TOP_SCORE` /
`MIN_COVERAGE` were calibrated against this tokenizer on real data, and moving
them needs re-derivation plus a golden set well beyond 21 questions — a project,
not a bump. What changed is that the instrument now exists: any such attempt is
measured against `python -m pistis.bench` before and after, and must move false
answers down *without* trading it for false refusals (currently 4.9%, the number
to protect). The near-miss class is the target; the rest is already strong.

The more interesting lead the benchmark opens: a relevance check is a *different*
guard from a faithfulness check, and the product currently has only the latter.

**Verification:** server **221 -> 260 pytest** green (30 new in `test_bench.py`,
9 new red-team fixtures); all 131 labels validate against the live 53-document
corpus; `python -m pistis.eval --snapshot ../data/corpus/snapshot.json` still
**PASS**. Pushed to GreenPandaTech/Pistis.

---

## Session 8 (2026-07-27) — the gap report used in anger, and a stemmer evaluated then declined

**Used the corpus-gap report for the first time properly.** It had never been run
on anything real — the local ask-log holds 5 questions, so it reported nothing.
Against an 80-question realistic set (`--log`, so the privacy-relevant real log
stays untouched) it earned its keep twice.

1. **It found an engine bug.** `am` was missing from `STOPWORDS`. Measured on the
   live corpus, `idf("am") = 6.966` — *identical to* `idf("vat")`, a concept the
   corpus genuinely lacked. So a function word dragged IDF-weighted coverage down
   as hard as a real gap, falsely refusing two questions, and then explained the
   refusal with the word "am". Fixed in `9ab5fec`. Worth reading how: a first,
   broader stoplist (`than/then/any/all/no/not/only/most`…) **measurably regressed**
   "auto enrolment" from answered to refused, because dropping high-frequency
   words from the *documents* shifts BM25 globally and buried the passage that
   answers it. Narrowed to only what the evidence justified.
2. **Corpus 46 → 53 documents** (`9838f39`), closing the gaps it ranked: VAT
   registration + rates, IR35, inheritance tax, council tax, warm home discount,
   energy-bills help. Each page was verified *before* adding —
   `/vat-registration` does not resolve, and `/council-tax-bands` has a
   ZERO-length body (the transaction-page trap behind the two standing refresh
   failures). Result on the same 80 questions: **59 answered / 19 refused → 67 /
   11**, every new answer fully grounded, and the report then showed **nothing
   above the floor** — the filled gap dropped off by itself, as designed.

### A stemmer: built, measured, and DECLINED (deliberate — do not "finish" this)

The one honest remainder was morphology: the light plural fold maps `bands→band`
but not `banding→band`, so "how does council tax banding work" refused against a
corpus that covers council tax bands.

Both options were actually tried and measured, not guessed at:

* **Hand-rolled inflection rules** (plural + `ing`/`ed` + `ies`) — rejected as
  *incorrect*. They are not confluent: `earnings→earning` (via the plural rule)
  while `earning→earn`, so the two stop matching each other; and they produce
  non-words inconsistently (`housing→hous` but `house→house`). It did measure
  well on the surface (67 → 70 answered, eval PASS) which is exactly the trap —
  it answered 3 more of *my own* 80 questions while carrying a known defect.
* **`snowballstemmer`** (BSD-3, pure Python) — correct and properly confluent
  (`banding/bands/band → band`, `earnings/earning/earn → earn`). Still declined,
  for two reasons that are about this product specifically:
  1. **The gate's thresholds were calibrated against THIS tokenizer** (the 24/24
     then 37/37 golden work, and the union-vs-best-passage coverage bug found on
     real data). Stemming changes every IDF and BM25 score, so it needs
     re-certification of `MIN_TOP_SCORE`/`MIN_COVERAGE`, not merely a green eval —
     21 goldens cannot demonstrate that.
  2. **It widens the false-match surface in the dangerous direction.** Stemming
     made `listed→list` and `building→build`, which flipped
     `test_no_source_refusal_summarises_overflow_terms` from `no_source` to
     `weak_coverage` — the solar-panels query started matching generic corpus
     text. For a default-deny product, coverage satisfied by generic stems is
     worse than a false refusal, and `bm25.py`'s own header commits to
     pure-python scoring "which the gate's calibration tests rely on".

**If it is ever taken on, it is a project, not a bump:** add the dependency (or
vendor it, with the BSD-3 notice), re-derive the gate thresholds against the
stemmed index, extend the golden set well beyond 21, and re-run the live-corpus
eval — the `--log` harness plus a canary list of must-answer/must-refuse questions
is the right instrument. The measured upside to weigh against that: ~3 more
answers in 80.

`_fold`'s docstring now points here so the next reader does not re-litigate it.

---

## Session 7 (2026-07-27) — corpus-gap report: deferred review run and closed

Session 6 left one open item: the full multi-agent adversarial review of
`gaps.py` was deferred at 99% context. It has now been run and every confirmed
finding is fixed.

**First, the working tree was broken.** An in-flight edit had added
`total_gap_concepts` to `GapReport` without passing it, so all 9 gaps tests
failed. It was aimed at a real defect — `--top` silently truncated the listing
with nothing saying the backlog was longer — and that fix was completed:
`total`/`--all`/negative-`--top` guard, disclosure in both human and JSON output
(`7a7242d`, 194 -> 198 pytest).

**The review**: 13 agents, six lenses (privacy, correctness, honesty,
robustness, test-quality, integration), each lens's findings then put to an
adversarial verifier told to refute them. 36 findings, 3 refuted, the rest
confirmed or narrowed, collapsing to ~8 root causes. Fixed in `843aa21` +
`d7c0172` (the second applies the review synthesis, which corrected three things
the first had shipped — see that commit message):

- **The ranking omitted the most-requested concept.** Concepts were keyed on the
  user's own wording, so one gap fragmented across its spellings: "passport" in
  one question and "passports" in another scored 1 each, both fell below a floor
  of 2, and the top gap printed as *nothing at all*. Now keyed on `tokenize` —
  the same fold/expansion retrieval uses — counted once across every refusal
  that named it, and displayed as the normalised token rather than the user's
  wording.
- **The floor was defeatable by one person retyping.** Distinctness was keyed on
  raw lowercased text, so a trailing "?" or an inserted stopword made a second
  "distinct question" and published a rare proper noun only one person had ever
  typed. Distinctness is now the question's content-token set.
- **`_is_concept` published identifiers.** "Has a letter in it" passes NI
  numbers, postcodes and IBANs, and "50k" is an amount. Now rejects £-prefixed,
  digit-leading, NI-shaped and long alphanumeric tokens, plus both halves of any
  full postcode typed in a question — while deliberately KEEPING short
  letter-led codes (`p45`, `sa302`, `ir35`), because a blanket digit ban deletes
  the most actionable class of UK-finance gap there is.
- **The claims were overstated.** It is not k-anonymity: the ask-log has no user
  identity, so N distinct questions may all be one person, and raising the floor
  does not change that. The docstring/README now say exactly that, drop the
  "never surfaced" absolutes, drop the actively misleading "raise the floor
  before any multi-user deployment", and state the trusted-single-operator
  posture. A "money questions people ask" line was false of the tool's own
  example output (top rows: passport, weather) and is gone.
- **Two sections, by evidence, not scope.** A zero-hit refusal means every token
  is absent from the whole corpus — the *strongest* evidence of absence, not
  noise — so it is reported, not filtered. But it is listed apart from partial
  matches so neither crowds the other out of the ranking, with an explicit
  caveat that the report cannot tell a real gap from a correct out-of-scope
  refusal. Deliberately NOT built: a scope classifier from `AbstentionReport.
  stage` — measured, `stage` does not discriminate scope.
- **Silent false negatives closed.** Refusals naming no term are counted and
  disclosed ("NOT represented here") instead of letting an all-refused log read
  as a clean bill of health; skipped log lines are counted; the report names its
  own inputs and the snapshot date; a missing log exits 2 rather than printing a
  clean empty report; a missing snapshot says how to build one instead of a
  28-line traceback; a log with lines but not one usable question is refused
  outright (UTF-16 ASCII is technically valid UTF-8, so strict decoding alone
  cannot catch it); `--min-distinct` below 2 prints a loud floor-is-OFF warning.
- **`privacy/retention.py` had the same unguarded read**, and it runs at server
  startup — one corrupt byte in a local log would have stopped the service
  starting. Now warns and changes nothing rather than raising or silently
  rewriting a file it could not fully read.
- **Tests rewritten.** The old privacy test asserted a tokenizer tautology that
  passed with the entire privacy layer deleted, and the bare-numbers test was
  vacuous. Every absence assertion now carries a positive control, the serialised
  field surface is pinned (killing leak mutants that add a question field), and
  the shipped default floor is exercised.

**Explicitly NOT done** (each rejected with a measured reason, do not re-open
without reading it): a per-session id in the ask-log (a new linkable identifier
next to free-text questions = net privacy regression); excluding `no_source`
refusals (would gut the highest-confidence gap signal); `errors="replace"` on the
log read (silently accepts corrupted text); making the floor count asks (would
publish one person's single wording).

**Verification:** server **198 -> 219 pytest** green; web **17 vitest** green,
`tsc` + `vite build` clean, `npm audit` 0 vulns.

**Live-corpus production run (2026-07-27):** rebuilt the snapshot
(`python -m pistis.corpus.refresh` -> **46 documents**; the 2 failures are the
known prose-less GOV.UK calculator pages, pre-existing) and evaluated against the
real GOV.UK/HMRC/FCA data rather than the fixture:

    python -m pistis.eval --snapshot ../data/corpus/snapshot.json
    21/21 answerability · 42/42 claims grounded · 0 unsupported
    citations complete · refusals explained 4/4 · RESULT: PASS

`python -m pistis.gaps` re-run on that fresh corpus prints
`Snapshot fetched : 2026-07-27` — the provenance line added this session doing
exactly its job, letting a reader confirm the backlog reflects today's corpus
rather than a stale one.

---

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

**Verification (as of session 6):** server **185 -> 194 pytest** green (9 new in `test_gaps.py`
covering ranking, the floor, dedup, numeric filtering, the no-leak privacy
invariant, malformed-line tolerance, missing-log, and the CLI). Keyless/offline;
web untouched (this is an ops/analytics CLI, deliberately not a public surface).
Reviewed manually + via the 9 targeted tests (incl. the no-leak privacy
invariant, the floor crossing, dedup, numeric filtering); the full multi-agent
adversarial review was deferred (context budget) — worth running on resume.

> **SUPERSEDED BY SESSION 7 — read that section instead.** The deferred review
> has now been run, and it falsified several claims made in this section. The
> floor is **not** k-anonymity (it counts distinct questions, and the ask-log
> holds no user identity); "bare numbers/amounts dropped" did not stop NI
> numbers, postcodes, IBANs or "50k"; the "no-leak privacy invariant" test
> credited above asserted a tokenizer tautology that passed with the whole
> privacy layer deleted; and the ranking omitted the most-requested concept
> because concepts were keyed on the user's own wording. All fixed in session 7.

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
- Honesty eval: `server/.venv/Scripts/python -m pistis.eval --snapshot ../data/corpus/snapshot.json`
- Answerability benchmark (session 9): from `server/`,
  `.venv/Scripts/python -m pistis.bench --validate` to check the LABELS against
  the current corpus, then `-m pistis.bench --by-difficulty` to score the gate.
  Rebuild the dataset with `.venv/Scripts/python tests/fixtures/bench_build.py`
  after editing the labelling script — never hand-edit `bench.json` (a test
  pins it to the build script's output).
- Manual log purge (optional — startup already does this):
  `server/.venv/Scripts/python -m pistis.privacy.retention`
