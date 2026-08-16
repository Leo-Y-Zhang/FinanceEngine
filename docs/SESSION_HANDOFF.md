# SESSION_HANDOFF — FinanceEngine

**Updated:** 2026-08-03 (session 11: repo renamed Pistis -> FinanceAnswerEngine,
Python package `pistis` -> `finance_engine`; four design documents added
under `docs/`. The rename exposed a real defect in the dependency-audit gate -
see "Session 11" below. Nothing else changed; the engine is untouched.)

---

## Session 11 (2026-08-03) — rename hygiene and the design documents

**The rename.** GitHub repo and git remote were already `FinanceAnswerEngine`;
this session made the tree agree with them. `server/pistis/` ->
`server/finance_engine/` (a plain directory rename plus import rewrites -
the package is imported only by this repo, so nothing external breaks), the
distribution name in `pyproject.toml`, the npm package name, the CI commands,
every doc, and the user-facing product name in prose and UI strings. The dated
sections below still describe the same code; only the name has changed.

**A defect the rename exposed - the dependency audit was auditing a stranger.**
`pip-audit --strict` audits every distribution installed in the environment,
including this project, which is installed editable. It passed under the old name
only because an unrelated package called `pistis` exists on PyPI, so the gate was
resolving the local project against someone else's releases and reporting the
result as ours. `finance-engine` is not on PyPI, so the step failed
immediately after the rename - which is the correct behaviour finally showing up.
The audit now freezes the third-party dependencies and audits those:

    pip freeze --exclude-editable > audit-requirements.txt
    pip-audit --strict -r audit-requirements.txt

`--strict` is kept; only the local project is excluded, which is what the step
always meant. `--skip-editable` does not work here: under `--strict` a skipped
distribution is itself a failure.

**Two knock-on fixes, both caused by the longer name:** one line in `gate.py`
crossed the 100-character ruff limit and was wrapped (the emitted string is
byte-identical), and the `.wordmark` letter-spacing was cut from 0.35em to
0.18em with a clamped font-size, because a 21-character three-word name at the
old tracking ran wider than the masthead and wrapped to three lines on a phone.

**The design documents.** `docs/PRD.md`, `docs/TDD.md`, `docs/APP_FLOW.md` and
`docs/DESIGN_BRIEF.md`, written retrospectively against the code as built and
marked `built`. They are descriptive, not a plan; the project remains parked.

**Gate after the rename (local, all green):** ruff clean · **283 pytest**, 95.21%
coverage (floor 90%) · `pip-audit --strict -r audit-requirements.txt` clean ·
honesty eval **PASS** (21/21, 33/33 grounded, refusals explained 4/4) · web
`tsc` clean, **17 vitest** green, build clean, `npm audit` 0 vulnerabilities.
`python -m finance_engine.bench --validate` was NOT run: it needs the live
`data/corpus/snapshot.json`, which is gitignored and requires a network fetch.

---

## ▶ PROJECT STATUS — COMPLETE AND PARKED (2026-07-27)

**Nothing is in flight. Everything is committed and pushed.** Read this block
before anything else; the dated sections below are a historical record and some
of their statements were true only on the day they were written.

| | |
|---|---|
| Repo | `Leo-Y-Zhang/FinanceEngine` (private), local `C:\dev\FinanceAnswerEngine` |
| State | working tree clean, `main` == `origin/main` |
| Server | **284 pytest**, ruff clean, **95% coverage** (floor 90%), `pip-audit` clean |
| Web | **17 vitest** (incl. axe), `tsc` clean, build clean, `npm audit` 0 vulns |
| Honesty eval | **PASS** on fixture *and* live corpus (21/21, 42/42 grounded) |
| Benchmark | 131 labels valid · false answers **12.0%** · false refusals **3.7%** · routing 18/18 |

**CURRENT GATES (these supersede the "Gates in force" list at the bottom):**
- **Build-only.** No deploy, no launch, no monetisation, no real users.
- **Pushing to GitHub is NORMAL and expected.** The "ON HOLD" note further down
  was a one-off instruction from 2026-07-21 and is long expired.
- **The lawyer gate does not block development.** User decided 2026-07-27 that
  there will be no launch or monetisation, so it does not apply. It returns in
  full the moment anyone wants to make this public or take money for it.
- Anonymity: noreply commit identity, no personal identifiers.
- Corpus: OGL/official sources only; no scraping around WAFs.

**IF RESUMED, the honest options** (none is outstanding work — the project is
finished as a private build):
1. Give the benchmark a **quality** dimension. It currently scores answer-or-refuse
   *state* only, and that blind spot is what hid the nav-chrome defect.
2. The residual **6 false answers** — a structural limit of a lexical gate, not a
   bug. Needs a question-type signal, measured on questions from the real
   ask-log rather than authored ones.
3. **Do NOT re-open**: gate threshold nudging (session 8 + 10), a stemmer
   (session 8), phrase-level retrieval (session 10). Each was built or measured
   and declined for a written reason.

---

## Session 10 (2026-07-27) — the relevance guard: grounded is not relevant

Session 9's benchmark said 12 of 50 should-refuse questions were answered, every
one perfectly grounded, and the faithfulness verifier caught none. This session
found out why and fixed it. Commit `e3676ad`.

**The diagnosis, which took two wrong hypotheses to reach.** First guess was that
sentence-level overlap should be IDF-weighted like `coverage` already is. The
data killed it: "How much is statutory sick pay?" matches *all three* of its
query terms in the offending sentence — a list of earnings types that happens to
include "statutory sick pay". Lexical overlap, weighted or not, cannot tell
*about X* from *mentions X in passing*.

Second guess was to key relevance on the question's single rarest term. The data
killed that too, and instructively: in the live corpus **"each" has a higher IDF
than "isa"**, so that rule puts "How much can I pay into an ISA each year?"
entirely on a function word. This is the same defect class as session 8's `am`
stopword bug — and it *cannot* be fixed by widening `STOPWORDS`, because session
8 already measured that dropping high-frequency words shifts BM25 globally and
regressed real answers.

**What shipped.** A third signal, independent of the other two.
`Bm25Index.topic_share(query, doc_id)` measures the share of a question's
IDF-weighted meaning that a document is actually **about**, where `is_about` =
titled for the term, or using it across enough distinct passages to be a subject
rather than an aside. The gate drops off-topic hits *before* claim selection
(`_on_topic`), so the guard can only ever REMOVE material — it cannot turn a
refusal into an answer, and a test pins that.

Two things it had to get right:
- **IDF-weighted share, not the rarest term** (above). A single junk token cannot
  hijack the measure because it only contributes its own weight to the denominator.
- **Aboutness relative to document length.** A fixed passage count is meaningless
  across sizes: live documents run to a median of 32 passages, but 3 of 53 hold
  only two, and in a two-passage document one passage IS half the subject. The
  absolute rule broke **12 tests on the fixture corpus** (every fixture doc has
  exactly 2 passages) — the design telling on itself before it reached anything
  real. Now `min(ABOUTNESS_PASSAGES, ceil(passages/2))`.

Refusals get their own **`off_topic`** stage rather than reusing
`no_groundable_statement`. That distinction is not cosmetic: the latter means a
source IS on topic but holds no quotable sentence, and reusing it would have
given the user a confidently wrong account of why FinanceEngine declined. Mirrored in
`web/src/types.ts`.

**Measured on the live 53-doc corpus — the whole point of having the benchmark:**

    false answers  : 12 of 50 (24.0%)  ->  6 of 50 (12.0%)
    false refusals :  4 of 81 ( 4.9%)  ->  4 of 81 ( 4.9%)   UNCHANGED
    answer->answer : 77                ->  77                UNCHANGED

The 6 answers removed were *exactly* the 6 false ones. `MIN_TOP_SCORE` and
`MIN_COVERAGE` were **not touched** — this is a new orthogonal signal, not a
recalibration, which is why session 8's re-certification rule is not violated.

**What remains, honestly.** 6 false answers, all still `near_miss`. Their limit
is structural, not a tuning gap: asked for the Universal Credit standard
allowance, the corpus genuinely *is* about Universal Credit — it just never
states award rates. Topical aboutness cannot separate "covers the subject" from
"covers the specific fact asked for", and no threshold on this signal will. That
needs a different idea (question-type vs passage-shape matching), and it should
be measured on the benchmark before it is believed.

### A reflexive pronoun could veto a correct source

Chasing the *cost* side afterwards found one more, and it is session 8's `am` bug
a third time. **"How do I protect myself from financial scams?" was REFUSED**
against the FCA scam-protection page — the strongest hit in the entire corpus.
Coverage came to **0.5962 against a 0.6 threshold**, and the single uncovered
term was **"myself"**. The explainable-refusal card then told the user that no
trusted source covers "myself".

The stoplist already held every other pronoun form (`me my you your he she him
her they them theirs`) and had simply missed the reflexives. Adding
`myself/yourself/himself/herself/itself/ourselves/yourselves/themselves`
completes that list on its own logic rather than widening policy — and the
regression test carries a positive control on small content words, because
session 8 measured that a *broader* stoplist shifts BM25 globally and regressed
real answers. **False refusals 4 -> 3 of 81 (4.9% -> 3.7%), false answers
unchanged at 6.**

### It exposed a real corpus defect — NAVIGATION CHROME IS INDEXED AS CONTENT

Do not read that fix as a clean win. The scams question now *answers*, but from
a **link-menu block** on an FCA page, not prose:

    "Support available for mortgages as interest rates rise More information.
     Your rights with financial services Mortgage fraud Protect yourself from
     scams How to complain."

Both behaviours were bad — refusing while blaming the word "myself", or
answering with navigation chrome — and they are two separate defects. The
stopword fix is right on its own terms; the chrome was always there and the fix
merely surfaced it. **The extraction step is keeping related-links blocks as
passages.** The honest fix is at extraction time in `corpus/`, not a
claim-level filter (a run of link labels is hard to tell from a legitimate
GOV.UK list without deleting real content, and getting that wrong is worse).
It needs a re-fetch to verify, which is a live network operation.

**LIMIT OF THE INSTRUMENT, now written down:** the benchmark scores
**answer-or-refuse state, not answer quality**, so it counted that nav-chrome
response as *correct*. Every number in it should be read with that caveat. A
quality dimension would need a different label type (does the answer contain the
specific fact asked for?) and is the natural next extension.

### Nav chrome: FIXED at extraction (`1c6de4a`)

The defect above is closed. A tag-only skip missed link blocks that do not live
in a `<nav>`: FCA pages carry related-links lists as plain `<div>`/`<ul>` in the
body. Page `<title>` was being extracted too, brand suffix and all, so
"Protect yourself from scams | FCA." was offered as a citable claim while every
Passage already carries the real title separately. Also fixed a nesting bug —
the skip counted depth across *different* tag names, so a nested `<div>` could
close a skipped block early and let chrome back in mid-block.

**The marker list is one entry long, and that is the point.** The first draft had
ten plausible-sounding markers. Measured against the live pages, `sidebar` alone
cut the FCA scam-protection page from **7,400 characters to 210** (the FCA layout
wraps its main content in a sidebar-named container) and most of the rest changed
nothing at all. Only `related-` does the job. The comment in `fetch.py` says to
extend the list only with a before/after character count on the real page.

**Re-fetched and verified surgical:** 53 documents before and after, none lost,
**only 7 documents changed and every one an FCA page** (1-3.5% each, 1,453 chars
of 441,914 total). No GOV.UK or HMRC document changed at all. All 131 labels
still validate; benchmark unchanged.

### Phrase-level retrieval: MEASURED and DECLINED (deliberate — do not "finish" this)

The remaining 6 false answers are word-sense failures on multi-word concepts
("credit report" -> a scam-*report* passage; "trading allowance" -> "Online
trading scams"). The obvious fix is phrase awareness, so it was built and
measured rather than argued about. Three variants, on the 131-question set:

| variant | false answers | new false refusals |
|---|---|---|
| A: answering doc must contain some query bigram | 6 -> 4 | **+3** |
| B: refuse if a query bigram is absent corpus-wide | 6 -> 6 | +2 |
| C: require it only when the bigram is a real corpus phrase | 6 -> 4 | +1 |

C is the best of them and by the written 5x cost model it "wins" (24 vs 33). It
is still declined, for two reasons:

1. **What it breaks is not an artifact.** The answer it removes — "Is interest on
   my child's savings taxable?" — is currently *correct and well-sourced*: "The
   parent will have to pay tax on all the interest if it's above their own
   Personal Savings Allowance", from exactly the document the label names.
   Trading a right answer about a real question for two junk ones is not the
   trade the cost model was written to authorise.
2. **It would generalise badly, and the benchmark cannot see that.** These are
   131 *authored* questions, not a sample of real traffic — the build script says
   so itself. Bigram adjacency is brittle across paraphrase in a way topical
   aboutness is not, so a rule that costs 1 of 81 in-sample will cost more
   out-of-sample, and the benchmark would never show it.

If it is ever revisited, the honest instrument is not a bigram set but a
question-type signal (does the passage state the *kind* of fact being asked
for — a rate, a threshold, a deadline?), measured on a question set drawn from
the real ask-log rather than authored.

**Verification:** server **260 -> 272 pytest** green; honesty eval **PASS on both
fixture and live corpus** (21/21 answerability, 42/42 grounded live); web **17
vitest** green + `tsc` clean. Pushed.

**Final measured state of the gate (live 53-doc corpus):**

    false answers  : 6 of 50 (12.0%)   was 12 of 50 (24.0%) at session start
    false refusals : 3 of 81 ( 3.7%)   was  4 of 81 ( 4.9%)
    advice routing : 18/18             was 17/18
    grounded       : 84/84

Both failure rates went DOWN together, which is the part worth noting: the two
usually trade against each other.

---

**Session 9 header (previous):** 2026-07-27 — finished the in-flight answerability
benchmark; it found three defects in its own validator, one false label, and a
live advice-boundary escape; all green, pushed.

## Session 9 (2026-07-27) — the answerability benchmark, finished and run in anger

**Picked up work left uncommitted when the previous session ended.** The working
tree held `server/finance_engine/bench.py` plus `tests/fixtures/bench_build.py` and
`bench.json` — written, but never run, never tested, and never committed. It is
now all three. Commits `6976d62` (benchmark) and `2aed2f0` (the escape it found).

**What it is.** `finance_engine.eval` proves every *emitted* claim is grounded. It never
measured the **gate**, which is where the product's central claim lives.
`python -m finance_engine.bench` scores 131 labelled questions and reports the two
failures separately — never averaged into one accuracy figure, because that
would hide a serious failure inside a mild one — under a stated 5x cost model,
broken down by difficulty. No label comes from FinanceEngine's output; each is derived
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
measured against `python -m finance_engine.bench` before and after, and must move false
answers down *without* trading it for false refusals (currently 4.9%, the number
to protect). The near-miss class is the target; the rest is already strong.

The more interesting lead the benchmark opens: a relevance check is a *different*
guard from a faithfulness check, and the product currently has only the latter.

**Verification:** server **221 -> 260 pytest** green (30 new in `test_bench.py`,
9 new red-team fixtures); all 131 labels validate against the live 53-document
corpus; `python -m finance_engine.eval --snapshot ../data/corpus/snapshot.json` still
**PASS**. Pushed to Leo-Y-Zhang/FinanceEngine.

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
(`python -m finance_engine.corpus.refresh` -> **46 documents**; the 2 failures are the
known prose-less GOV.UK calculator pages, pre-existing) and evaluated against the
real GOV.UK/HMRC/FCA data rather than the fixture:

    python -m finance_engine.eval --snapshot ../data/corpus/snapshot.json
    21/21 answerability · 42/42 claims grounded · 0 unsupported
    citations complete · refusals explained 4/4 · RESULT: PASS

`python -m finance_engine.gaps` re-run on that fresh corpus prints
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

**What shipped:** `server/finance_engine/gaps.py` + `python -m finance_engine.gaps` — replays the
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

Standout feature completing the thesis's other half: FinanceEngine already *proved its
answers* (trust report + freshness); now it *proves its refusals* too. Built
autonomously under the standing directive; pushed to Leo-Y-Zhang/FinanceEngine,
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
carries none. FinanceEngine GitHub Actions are disabled; pushes are safe (not an
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
standing autonomous-work directive); pushed to Leo-Y-Zhang/FinanceEngine, each
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
3. `feat:` reproducible honesty-eval CLI `python -m finance_engine.eval` — `0fe08ff`.
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
snapshot (`python -m finance_engine.corpus.refresh` → 46 docs, gitignored) and ran
`python -m finance_engine.eval --snapshot ...` → **21/21 answerability, 42/42 claims
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
FinanceEngine GitHub Actions are disabled (no CI trigger); pushes are safe (not an
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
   `server/finance_engine/privacy/retention.py` (`purge_expired`), wired into
   `create_app()` to run at server startup, also runnable standalone
   (`python -m finance_engine.privacy.retention`). New tests:
   `server/tests/test_retention.py` (6 tests) + 1 startup-integration test
   in `test_api.py` + `web/src/__tests__/PrivacyNotice.test.tsx` (3 tests,
   incl. axe) + 2 new cases in `App.test.tsx`.
2. **Finding #1 (classifier false-negative tail) — narrowed, not closed
   (not closable by construction; documented as such).** Adversarial
   hardening pass 2 in `server/finance_engine/engine/classifier.py`: 5 new
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
     copyright terms may require written permission for FinanceEngine's
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

## Push status — EXPIRED, see PROJECT STATUS at the top
> **Historical.** This hold was a one-off instruction on 2026-07-21 and no longer
> applies. Everything through session 10 is committed AND pushed; the tree is
> clean and `main` matches `origin/main`. Pushing is normal.

**Pushing to GitHub is ON HOLD per current user instruction** (recent
free-tier limit) — this session's changes are **local commits only**.
Nothing in this session was pushed to Leo-Y-Zhang/FinanceEngine. Push when
the user says so.

## Exact next step — SUPERSEDED, see PROJECT STATUS at the top
> **Historical (2026-07-21).** Nothing is in flight as of session 10.

- NONE IN FLIGHT. Session 2's work (privacy notice + retention purge +
  classifier hardening pass 2) is committed locally, not pushed. Next
  session = user-directed (see queue) — most likely either a real lawyer's
  pass informed by `docs/compliance-review-2026-07-21.md` (now including
  the 2026-07-21 addendum), or continuing to build (e.g. MoneyHelper
  partnership integration, staleness policy, disclaimer visual prominence).

## Needs-you queue — ALL CLOSED as of 2026-07-27; nothing is pending

1. ~~Read/OK on the MVP scope decision~~ **CLOSED** — user approved proceeding
   on it as a private build (2026-07-24). Do not re-open.
2. ~~Compliance/lawyer sign-off~~ **DOES NOT APPLY** — user decided 2026-07-27
   there will be **no launch and no monetisation**, so the gate is not blocking
   anything. `docs/compliance-review-2026-07-21.md` is retained as the starting
   point if that ever changes; the gate returns in full at that moment.
3. ~~Claude-composer mode~~ **DROPPED by user** (2026-07-24) — everything stays
   free/keyless. A keyless "composer" was deliberately NOT built: it could only
   re-arrange source text and risk connective prose implying unsourced
   relationships, which is precisely what this extractive product exists to
   avoid. Do not revive it without the user asking.
4. MoneyHelper content — **OPTIONAL, not blocking.** A free
   partnership/republishing programme appears to exist
   (`moneyhelper.org.uk/en/about-us/partnerships/overview`); 21 entries are
   parked in `manifest.json`'s `excluded` array. This is a **content decision,
   not code** — the engine works without them. Only worth doing if someone wants
   the corpus wider.
5. ~~Confirm GitHub Dependabot alerts cleared~~ **DONE** — 0 open.
6. ~~Disclaimer visual prominence (finding #9)~~ **MOOT** with no launch — it is
   a pre-launch presentation call and the disclaimer is already shown.
   ~~Staleness policy (finding #10)~~ **DELIVERED** by the 2026-07-23 freshness
   layer (`engine/freshness.py`).

## Gates in force — SUPERSEDED, see PROJECT STATUS at the top
> **Historical (2026-07-21).** The push hold below has expired. The build-only,
> anonymity and corpus gates all still stand.

- Build-only: NO deploy, NO launch, NO monetisation.
- Anonymity: noreply commit identity; no personal identifiers.
- Corpus content: OGL/official sources only; no scraping around WAFs.
- ~~Push-to-GitHub: ON HOLD~~ — expired 2026-07-21; pushing is normal.

## How to run
- Snapshot: `server/.venv/Scripts/python -m finance_engine.corpus.refresh`
- API: `server/.venv/Scripts/python -m uvicorn --factory finance_engine.api.app:create_app --port 8000`
  (also purges expired `logs/ask.jsonl` entries on startup — see
  `finance_engine/privacy/retention.py`)
- UI: `cd web && npm run dev` (proxies /api -> :8000); privacy notice at
  `#/privacy` or via the link in the disclaimer banner
- Tests: `server/.venv/Scripts/python -m pytest` · `cd web && npm test`
- Full local gate (identical to CI, see `.github/workflows/ci.yml`): from
  `server/` — `python -m ruff check finance_engine tests`,
  `python -m pytest --cov=finance_engine --cov-report=term-missing` (floor 90%, currently
  95%), `pip freeze --exclude-editable > audit-requirements.txt` then
  `python -m pip_audit --strict -r audit-requirements.txt`,
  `python -m finance_engine.eval`; from `web/` —
  `npx tsc --noEmit`, `npm test -- --run`, `npm run build`, `npm audit`.
  Actions runs these on every push and is NOT billing-blocked any more (the old
  note here was stale; run 30820556169 went green 2026-08-03).
- Honesty eval: `server/.venv/Scripts/python -m finance_engine.eval --snapshot ../data/corpus/snapshot.json`
- Answerability benchmark (session 9): from `server/`,
  `.venv/Scripts/python -m finance_engine.bench --validate` to check the LABELS against
  the current corpus, then `-m finance_engine.bench --by-difficulty` to score the gate.
  Rebuild the dataset with `.venv/Scripts/python tests/fixtures/bench_build.py`
  after editing the labelling script — never hand-edit `bench.json` (a test
  pins it to the build script's output).
- Manual log purge (optional — startup already does this):
  `server/.venv/Scripts/python -m finance_engine.privacy.retention`
