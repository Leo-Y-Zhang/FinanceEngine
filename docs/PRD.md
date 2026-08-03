# Finance Answer Engine — record of a build

Written 2026-08-03 against the code as it stands, not before it. The project was
built between 2026-07-21 and 2026-07-27 and is parked; this is written down
because the reasoning is the interesting part, and because a build with no stated
scope cannot be judged against one.

[TDD](TDD.md) · [App Flow](APP_FLOW.md) · [Design Brief](DESIGN_BRIEF.md)

## The failure is not ignorance, it is not abstaining

Somebody asks a general-purpose chatbot "how much can I put in an ISA this
year?" and gets a confident number with no source, no date, and no way to tell
whether it is this tax year's figure or last year's. UK personal finance is
almost entirely tax-year-bound, so a stale answer and a wrong answer look
identical.

The failure that matters is not that the model does not know. It is that **it
does not abstain**: it answers everything at the same apparent confidence, and
the reader cannot separate the answers it has grounds for from the ones it does
not.

The market research behind this build (`product-spec.md` §1) records the adoption
side of the same problem: UK adults use AI for money questions at scale, and
inaccuracy and privacy are the two most-cited concerns. This project is a
response to the first.

## Two numbers, including the bad one

On the live 53-document corpus, measured 2026-07-27: **false answers 6/50
(12.0%), false refusals 3/81 (3.7%)**.

Both are published, both are separately measured, and the first one is not good.
It is here rather than in an appendix because a product whose whole claim is
honest abstention cannot report only the flattering half of its own evaluation.

A false refusal is treated as roughly five times cheaper than a false answer in
the benchmark's cost model, which is why the defaults point at refusal and why
the advice classifier runs before retrieval rather than after.

`python -m finance_answer_engine.eval` reproduces both figures from a committed
fixture corpus. The whole engine is deterministic, offline and keyless — no model
API, no network at query time, no secret to leak.

## Requirements

**Must**

- Extractive answers only. Claims are verbatim sentences from the corpus, never
  generated prose.
- Per-claim citation with organisation, title, URL, fetch date and — where the
  source declares one — last-updated date.
- Default-deny gate: abstention is the resting state, and an answer is earned.
- Advice-boundary classifier ahead of retrieval, failing towards routing.
- A visible disclaimer on every response object, not only in the UI chrome.
- Sources restricted to a curated manifest of UK-authoritative publishers.

**Should**

- Freshness signalling, because a faithful quote of a past tax year is still
  wrong for today.
- A reproducible honesty evaluation, so the promises are measured rather than
  asserted.
- An answerability benchmark that scores the *gate* rather than the answers.
- A corpus-gap report, so refusals become a backlog.

## The regulatory line, and why the engine sits on the wrong side of it

Under FSMA s21 and Art 53 RAO, a communication presented as suitable for a
particular person, about a specific investment, is regulated advice. Giving it
without FCA authorisation is a criminal offence. The classifier exists to keep
this engine on the wrong side of that line **on purpose**.

"Targeted support" (FCA PS25/22) — suggesting a course of action to a segment of
similar consumers — needs its own FCA permission, and is out of scope until and
unless authorised, which is not happening.

Anyone who ever wants to launch or monetise this reopens the compliance gate in
full, and a qualified solicitor's sign-off is required first. Nothing in
`compliance-review-2026-07-21.md` substitutes for that; it is a non-lawyer triage
written to give a real one a head start.

## Also out of scope

**Whoever is asking.** No accounts, no sessions, no personalisation, and no
memory of who asked what.

**A composer.** No language model writes any part of an answer. The option was
considered seriously and dropped, for the reason set out in the rejections
table below.

**Arithmetic.** It quotes; it never calculates. The engine never adds up a
user's numbers. If a source states a
figure it may be quoted; if the figure has to be derived, the engine abstains.
Worked examples inside sources are detected and downgraded to `uncertain`,
because an illustration presented as a rule is exactly the defect this product
exists to avoid.

**Answer quality.** The benchmark scores answer-or-refuse *state*, not whether
the answer is any good. That blind spot is real and is written into the README —
it is how a navigation-chrome defect went unnoticed for a session.

**Deployment.** No hosting, no domain, no public surface, no monetisation.

## Marks of done

Each is checkable by running a command in this repo, and all currently hold.

- [x] **No claim is ever emitted without a named, dated, linked citation.** Not a
      policy but a constructor invariant: `AnswerCard.__post_init__` raises if
      any claim lacks `citation.url` or `citation.fetched_at`.
- [x] **No claim is ever emitted that is not textually grounded in the passage it
      was drawn from.** Enforced twice — as an emission guard in the gate, and
      again as a construction-time invariant on `AnswerCard`.
- [x] **A refusal explains itself as thoroughly as an answer does**: which gate
      stage fired, each answerability signal against its threshold, and the
      specific concepts no source covers.
- [x] **Personal-recommendation-shaped questions are never answered.** They are
      converted into routing events, measured at 18/18 on the benchmark's
      advice-boundary set.

## Who it is for, honestly

A UK adult with a specific, factual money question — an allowance, a rate, a
threshold, a deadline — who wants the answer *and* the source, and who would
rather be told "I cannot verify that" than be given a plausible number.

Not for anyone asking what they personally should do. That is regulated advice.

And the honest version of the audience: this is a private, build-only portfolio
project. It has never been deployed, has no users, and the owner decided on
2026-07-27 that there will be no launch and no monetisation. Its real reader is
an engineer or an admissions tutor looking at whether the thing does what it
says.

## What the log holds

The only personal data in play is the free text of the question, appended to a
local JSONL log (`logs/ask.jsonl`) with a timestamp and the outcome kind.
Nothing else: no account, no cookie, no session id, no IP at application level.
Questions are free text, so they *can* carry personal and occasionally
special-category data — "I'm 45 with a £30,000 SIPP and a heart condition" — even
though nothing ever asks for it. That is stated plainly in the user-facing
privacy notice rather than buried.

Only whoever can read the filesystem of the machine running the server can see
it. The log is gitignored and has never been committed. No remote sink, no
analytics, no third party.

There is no access-control model to revoke, because there are no accounts and no
multi-user surface. That is a real answer rather than an evasion: the system is
single-operator by construction. The nearest equivalent question — what if
someone wants their question deleted — is answered by the 30-day automatic purge
in `privacy/retention.py`, run at every server startup, plus the erasure right
described in the notice. The honest limitation is recorded there too: with no
identifiers in the log, an individual entry can only be found from the
approximate question text and time.

One privacy decision is worth recording *as* a decision. Adding a per-session id
to the ask log was proposed and **rejected**: a linkable identifier sitting next
to free-text financial questions is a net privacy regression, and the analysis it
would have enabled was not worth it.

The corpus-gap report is the one aggregate output, and its claims are
deliberately narrow. It publishes per-concept frequencies with no question text,
behind a repetition floor. It is **not k-anonymity and not anonymity over
people** — the log holds no identity, so N distinct questions may all be one
person. Amount- and identifier-shaped tokens (bare numbers, `£45k`, NI-number
shapes, both halves of a full postcode) are dropped, while short letter-led codes
like `p60` and `ir35` are deliberately kept because they are real corpus
concepts. Best-effort scrubbing, described as best-effort.

## Built or measured, then dropped

Each was built or measured before being dropped. None should be reopened without
reading the reason.

| Alternative | Why it was dropped |
|---|---|
| **LLM composer behind `providers/`** | The value of a composer is fluency, which needs a paid API key. A *keyless* composer could only re-arrange source sentences, and connective prose implies relationships the sources never asserted — precisely the failure an extractive product exists to avoid. The faithfulness verifier was still built as the guard a composer would need, so the slot stays open. |
| **`snowballstemmer` for morphology** | Correct and properly confluent, and still declined. The gate thresholds were calibrated against *this* tokenizer, so stemming needs re-derivation rather than a bump. Worse, it widened the false-match surface in the dangerous direction: `listed→list`, `building→build` let generic corpus text satisfy coverage. Measured upside was about 3 more answers in 80. |
| **Hand-rolled inflection rules** | Rejected as incorrect, not merely inelegant. Not confluent (`earnings→earning` but `earning→earn`, so the two stop matching) and inconsistent (`housing→hous`, `house→house`). It measured *well* on the surface, which is exactly the trap. |
| **Phrase-level retrieval (three variants, measured)** | The best variant removed 2 of 6 false answers but destroyed a correct, well-sourced answer about children's savings tax, and bigram adjacency generalises worse than topical aboutness across paraphrase — which 131 *authored* questions can never reveal. |
| **Nudging `MIN_TOP_SCORE` / `MIN_COVERAGE`** | Calibrated on real data against this tokenizer. Moving them needs re-derivation plus a golden set well beyond 21 questions. Twice proposed, twice declined; the relevance guard was added as an orthogonal third signal instead, which is why it did not violate the re-certification rule. |
| **A wider stopword list** | Measured, and it regressed real answers: dropping high-frequency words from the *documents* shifts BM25 globally and buried the passage answering "auto enrolment". Only words that cannot be a UK-finance concept are stopped. |
| **A per-session id in the ask log** | Net privacy regression, as above. |
| **A scope classifier over `AbstentionReport.stage`** | Measured: `stage` does not discriminate topical scope. The gap report says so rather than inferring it. |
| **MoneyHelper corpus entries** | 21 curated entries sit in the manifest's `excluded` array with their reasons. There is no licensed fetch path and the standing rule is no scraping around WAFs. A partnership programme appears to exist; that is a content decision, not code. |

## What would reopen this

Nothing is blocking and nothing is in flight.

Would a question-type signal separate "covers the subject" from "covers the
specific fact asked for"? That is the structural limit behind the residual six
false answers, and it must be measured on questions drawn from a real ask log
rather than authored ones.

Does the benchmark need a quality dimension? It scores state only, and that blind
spot has already hidden one real defect.
