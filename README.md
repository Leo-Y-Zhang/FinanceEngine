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

If refusal is a feature, the refusals are also a signal: they say exactly which
questions people bring that no trusted source yet covers. `pistis.gaps` turns
that into a **keyless, privacy-safe backlog** — replay the local ask-log through
the engine, aggregate the `uncovered_terms` of each abstention, and rank the
concepts users most want but the corpus is silent on.

```bash
cd server && python -m pistis.gaps        # ranked corpus-gap report
python -m pistis.gaps --all               # list every concept above the floor
python -m pistis.gaps --json              # machine-readable record
```

Two kinds of gap are reported **separately**, because they mean opposite things
to whoever curates the corpus. **Thin coverage** — trusted sources matched the
question but fell short — are the real expansion candidates. **No overlap** —
nothing in the corpus matched at all — are mostly just out of scope for a UK
personal-finance corpus (a passport question, a weather question), and a
zero-hit refusal names every content word rather than one missing concept, so
listing them together let off-topic noise outrank the genuine gaps. Concepts are
canonicalised the way the index matches them, so a gap cannot hide by
fragmenting across its spellings ("passport" / "passports").

Privacy is built in, not bolted on: the output is concept frequencies only (raw
questions never leave the function), and a **reporting floor** withholds any
concept appearing in fewer than `--min-distinct` distinct questions. Being
precise about what that floor does and does not give you: the ask-log records no
user identity, so it counts **distinct questions, not distinct people** — it is
not k-anonymity over users. To stop one person clearing the floor by merely
retyping, "distinct" is measured on a question's content tokens, so case,
punctuation, stopwords and word order cannot manufacture a second question.
Raise the floor before exposing the report to more than one person's questions.
Amounts and identifier shapes are withheld — a term containing a digit is
dropped unless it is a known UK tax-form code, so `50k`, a National Insurance
number, a postcode or an IBAN can never surface as a "concept". It is
deterministic and offline, and it names its own inputs (log, snapshot, snapshot
date) so a reader can check what it read. Because it re-asks against the
*current* corpus, a gap you have since filled simply stops appearing — the
backlog stays honest.

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
