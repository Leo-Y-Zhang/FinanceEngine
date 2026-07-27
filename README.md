# Pistis

A trust-first, UK-first personal-finance **answer engine** defined by a
**default-deny honesty gate**: it answers only when it can attach a named,
dated, per-claim citation from a UK-authoritative source — otherwise it says
so plainly and routes you to proper guidance.

> **Pistis provides information and guidance, not regulated financial advice
> or a personal recommendation. It does not consider your individual
> circumstances. For advice tailored to you, speak to an FCA-authorised
> adviser.**

## Why this exists

UK adults use AI for money questions at scale, but the top stated fears are
inaccuracy and privacy. General LLMs cite fluently yet unreliably and almost
never abstain. Pistis inverts the posture: **the default is not to answer** —
the system earns the right to answer, claim by claim, from a curated corpus of
UK-authoritative sources (GOV.UK/HMRC, FCA, MoneyHelper/Pension Wise).
Refusal is a feature, not a failure mode.

## Architecture (MVP)

```
question ──► advice-boundary classifier ──► routing event (guidance boundary)
   │                                          ▲
   ▼                                          │ blocked / personal-rec shaped
retrieval (BM25 over curated corpus)          │
   ▼                                          │
grounding gate — per-claim support check ─────┤
   ▼ (passes both gates)                      │ ungroundable → ABSTAIN + route
answer card: claims, each with named + dated citation, confidence tier
```

- **Extractive core, LLM-optional.** Answers are assembled from what the
  sources support, not model parametric memory. An LLM composer can slot in
  behind `providers/`, but its output must pass the *same* grounding gate.
- **Corpus** is a manifest-driven snapshot of official/open sources
  (GOV.UK Content API under the Open Government Licence v3.0, plus curated
  FCA / MoneyHelper pages), with per-document fetch dates surfaced in every
  citation.
- **Guidance, never advice.** A rule-based advice-boundary classifier blocks
  personal-recommendation-shaped questions/outputs and converts them into
  routing events (MoneyHelper + FCA-authorised adviser), per the FSMA / Art 53
  RAO bright line.

## Proving the claims — faithfulness layer

Every answer carries a **trust report** that proves, claim by claim, that what
Pistis asserts is grounded in the source it cites — the literal expression of
the project's thesis, *software that proves its own claims*.

- **Faithfulness verifier** (`server/pistis/engine/faithfulness.py`) — a
  deterministic, keyless check that grounds each claim's text against the exact
  source passage it was drawn from, returning a verdict (`grounded` / `partial`
  / `unsupported`), a score, and the char **span** of the backing text. It runs
  as an **emission guard** in the grounding gate: a statement that is not
  grounded in its passage is never emitted as a claim (same posture as the
  overlap threshold), which also guards any future LLM composer.
- **Trust report on every answer** — the `/ask` answer includes a
  `trust_report` (`grounded / total`, `all_grounded`, and a per-claim verdict
  with its source span). `AnswerCard` enforces this structurally: an answer
  whose report is not fully grounded cannot be constructed. The web claim-ledger
  surfaces it as a per-claim "grounded in source" chip and an overall
  "N of N statements grounded in their cited source" summary.
- **Reproducible honesty eval** — quantifies the promise over a golden set:

  ```bash
  cd server && python -m pistis.eval        # human-readable report
  python -m pistis.eval --json              # machine-readable record
  ```

  Reports answerability accuracy (answer/abstain/route vs expected), citation
  completeness, and the headline faithfulness metric — every asserted claim
  grounded, zero unsupported. Deterministic and network-free over the committed
  fixture corpus (point `--snapshot` at the live corpus for production).
  Design: `docs/superpowers/specs/2026-07-23-provenance-faithfulness-design.md`.

### Freshness — is the source still current?

Faithfulness proves a claim is *in* its source; freshness asks whether that
source is still current. A deterministic, keyless check
(`server/pistis/engine/freshness.py`) flags any claim that names a **past UK
tax year** (finance figures are tax-year-bound) or comes from an aged snapshot,
assessed against a reference date (today in production, pinned in tests). Every
answer carries a `freshness` report; the ledger shows a
"2024-25 tax year — check current figure" chip per claim and, when anything is
stale, an answer-level caveat. On the live corpus today this reads *current*
with zero false positives — and the same 2026-27 figure will auto-flag next
April.

## Explaining the refusal — proving a refusal, not just an answer

Pistis's thesis is that **refusal is a feature, not a failure mode** — but a
refusal is only credible if it can show its working, the way an answer does. So
every refusal now carries an **abstention report**, symmetric with the trust
report on an answer:

- **The gate stage that fired** — `no_source` (nothing retrieved),
  `weak_coverage` (retrieved, but the answerability signals fell short),
  `no_groundable_statement` (matched well, but no single sentence was citable),
  or `empty_question`.
- **Each answerability signal against its threshold** — retrieval strength and
  source coverage, with the value, the bar, and pass/fail, so you can see *how
  close* it was rather than a black-box "not enough".
- **The specific concepts no trusted source covers** —
  `Bm25Index.uncovered_terms` returns the query's own words whose every token is
  absent from the top passages (rarest-first). A `passport` question refuses
  with *"No trusted source covers: passport, renew"*, not a generic shrug.

It is **keyless and deterministic**, and strictly additive: it enriches only
the refusal paths, never answer emission, the thresholds, or the faithfulness
verifier — so it can never turn a refusal into an answer. The web
`RefusalCard` surfaces it as uncovered-concept chips and per-signal meters, and
the honesty eval now scores **refusals explained** as a first-class metric
folded into `PASS`: a silent refusal is a regression, exactly like an
ungrounded claim. Design:
`docs/superpowers/specs/2026-07-24-explainable-refusal-design.md`.

## Corpus-gap report — refusals as a roadmap

If refusal is a feature, the refusals are also a signal: they say which concepts
people ask about that no trusted source in the corpus covers. `pistis.gaps`
turns that into a **keyless backlog** — replay the local ask-log through the
engine, aggregate the `uncovered_terms` of each abstention, and rank them.

```bash
cd server && python -m pistis.gaps            # ranked corpus-gap report
python -m pistis.gaps --min-distinct 3        # raise the repetition floor (default 2)
python -m pistis.gaps --top 50                # list more per section (default 25)
python -m pistis.gaps --all                   # no cap at all
python -m pistis.gaps --json                  # machine-readable record
```

**Absent from the corpus is not the same as belongs in the corpus.** Nothing in
the engine classifies topical scope, so the report cannot tell a real gap from a
question Pistis correctly refused as out of scope — it reports evidence and says
so, leaving the triage to a human. Two sections report only what was measured:
**no source shared any term** (every token absent from the whole corpus — the
strongest evidence of absence the system can produce) and **partial match**
(sources matched but fell short). They are listed apart so neither crowds the
other out of the ranking; the division is by evidence, not a scope judgement.
Concepts are keyed the way the index matches them, so a gap cannot hide by
fragmenting across its spellings ("passport" / "passports"), and nothing is
capped silently — each section always reports its full pre-cap total.

On privacy, precisely. The output is per-concept frequencies with no question
field, and a **repetition floor** withholds any concept recurring across fewer
than `--min-distinct` distinct questions. That is **not k-anonymity and not
anonymity over people**: the ask-log records no user or session identity, so N
distinct questions may all come from one person, and raising the floor does not
change that. What the floor does do is stop a *cosmetic* retype counting twice —
"distinct" is measured on a question's content tokens, so case, punctuation,
stopwords and word order cannot manufacture a second question. Treat the report
as **trusted-single-operator output**: it is a stdout-only ops CLI behind no API
or web surface, and anyone who can write to the ask-log can increment the
floor's counter. Amount- and identifier-shaped tokens are dropped (bare numbers,
`£45k`, `20k`, NI-number shapes, long alphanumeric mixtures, and both halves of
any full postcode), while short letter-led codes like `p60`, `sa302` and `ir35`
are deliberately kept — they are real corpus concepts, and a blanket ban on
digits would be a worse defect than the one it fixes. This is best-effort
scrubbing, not a guarantee. It is deterministic and offline, and it names its
own inputs (log, snapshot, snapshot date) so a reader can check what it read.
Because it re-asks against the *current* corpus, a gap you have since filled
simply stops appearing — the backlog stays honest.

## Answerability benchmark — measuring the gate, not asserting it

The faithfulness eval proves every emitted claim is grounded. It never measured
the **gate**, which is where the central claim lives. `pistis.bench` scores 131
labelled questions and reports the two failures **separately**, because a single
accuracy figure would average a serious failure against a mild one:

```bash
cd server && python -m pistis.bench --validate      # check the LABELS, not the engine
python -m pistis.bench                              # score the engine
python -m pistis.bench --by-difficulty              # plain / paraphrase / abbreviation / near_miss
python -m pistis.bench --json                       # machine-readable record
```

**No label comes from Pistis's output** — that would measure nothing. Each is
derived from the corpus or from the question's form, and each is falsifiable: an
`answer` label names a supporting document and a probe term that document must
contain; an `abstain` label names a concept the corpus must be silent on; a
`route` label names the phrase that makes the question a request for advice.
`--validate` re-checks every one against the current corpus, so labels cannot
silently rot as it grows, and the CLI **refuses to score** against labels known
to be broken. The protocol and its stated limits live next to the data in
`tests/fixtures/bench_build.py`.

**The result, on the 53-document live corpus (2026-07-27) — including the part
that is unflattering:**

| | before the relevance guard | now |
|---|---|---|
| False answers (answered when it should not have) | 12 of 50 — 24.0% | **6 of 50 — 12.0%** |
| False refusals (refused when it could have answered) | 4 of 81 — 4.9% | **4 of 81 — 4.9%** |
| Advice-boundary routing | 17/18 | **18/18** |
| Answers fully grounded | 89/89 | **83/83** |

Both numbers come from the same run, and the second column cost nothing on the
first: **no genuine answer was lost** closing half the false answers.

**What the benchmark found.** Every false answer sat in the adversarial
`near_miss` class — finance-shaped questions *adjacent* to the corpus — and
**every one was perfectly grounded**. Asked "How is cryptocurrency taxed?", the
engine returned a correctly-cited claim about *inheritance-tax taper relief*.
Asked "How much is statutory sick pay?", a passage listing SSP among types of
earnings. The faithfulness verifier objected to none of them, and it was right
not to: the claims really were supported by the passages they came from.
**Grounded is not the same property as relevant** — and the engine had a check
for the first and none for the second.

**The relevance guard** (`Bm25Index.topic_share`) is that missing check, and a
third signal independent of the other two. Retrieval strength and coverage ask
whether the question's *words* are present; faithfulness asks whether a claim is
supported by its source passage; this asks whether the document is *about the
subject raised* — titled for it, or using it across enough distinct passages to
be a subject rather than an aside. Off-topic sources are dropped before claim
selection, so the guard can only ever **remove** material and can never turn a
refusal into an answer. Such refusals carry their own `off_topic` stage rather
than borrowing another one's explanation.

Two details it had to get right, both settled by measurement rather than taste.
It weights by **share of IDF meaning, not the single rarest term** — in this
corpus "each" is a *rarer* token than "isa", so a rarest-word rule would hang
"How much can I pay into an ISA each year?" on a function word. And aboutness is
**relative to document length**, because live documents run to a median of 32
passages while some hold two, and in a two-passage document one passage is half
the subject. `MIN_TOP_SCORE` and `MIN_COVERAGE` were not touched.

**What remains.** 6 false answers, all still `near_miss`. The honest limit of a
lexical measure is visible in them: asked for the Universal Credit standard
allowance, the corpus genuinely *is* about Universal Credit — it just never
states the award rates. Topical aboutness cannot tell "covers the subject" from
"covers the specific fact asked for", and no amount of tuning this signal will.

The benchmark also caught a live advice-boundary escape on its first run, where
"is a Lifetime ISA **worth it for me**" was answered while "is **it** worth it
for me" routed, because the rule recognised only a pronoun subject.

## Layout

| Path | What |
|---|---|
| `server/` | Python engine + FastAPI API (`pistis/`) and tests |
| `web/` | React + Vite + TypeScript answer-card UI |
| `data/` | Corpus snapshots (gitignored; rebuild via `pistis.corpus`) |
| `docs/` | Design spec, implementation plan, session handoff |

## Licence & content

Code is proprietary (private). Corpus content from GOV.UK is used under the
[Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/)
with attribution in every citation. No proprietary content (MSE, Which?) is
ingested.
