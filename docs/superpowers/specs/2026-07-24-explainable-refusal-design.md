# Explainable Refusal — design

**Date:** 2026-07-24
**Status:** implemented (server `332f20b`, web `8b2696e`, docs `1718b59`,
adversarial-review fixes `6d06b99`)

## Problem

Finance Answer Engine proves its *answers* claim-by-claim (trust report + freshness), but its
*refusals* are opaque: every abstain collapses to one generic sentence — "The
sources Finance Answer Engine trusts do not cover this well enough to answer reliably." For a
product whose thesis is **"refusal is a feature, not a failure mode,"** that is
the biggest gap in the story: the refusal cannot show its working, so a user
cannot tell *why* Finance Answer Engine declined or *what* it would need to answer.

## Goal

Make a refusal prove itself the way an answer does — deterministically, keylessly,
and without weakening the honesty posture. A refusal should say **which gate
stage fired**, **how the answerability signals scored against their thresholds**,
and **which specific concepts no trusted source covers** — in the user's own words.

## Non-goals

- No change to the answer path, the gate thresholds, or the faithfulness verifier.
- No LLM / embeddings / network — the diagnostic is pure, deterministic Python.
- No corpus disclosure: a refusal reports only the *user's own* query terms that
  are uncovered, plus the gate's own scores — never corpus internals.

## Design

### Model (`models.py`)
- `SignalCheck(name, value, threshold, passed)` — one answerability signal vs its bar.
- `AbstainStage = "no_source" | "weak_coverage" | "no_groundable_statement" | "empty_question"`.
- `AbstentionReport(stage, explanation, signals=(), uncovered_terms=())` — the
  refusal proving itself, symmetric with `TrustReport`.
- `Abstention.report: AbstentionReport | None = None` — optional and additive, so
  existing constructors and the API serializer (`asdict`) are unaffected.

### Retrieval (`bm25.py`)
- `uncovered_terms(query, hits, top_n=4)` — the query's own words whose *every*
  expanded/folded token is absent from the union of the top passages, ordered by
  IDF weight (rarest, most telling gap first) then alphabetically for determinism.
  A word is flagged only when wholly uncovered, so a partial match (e.g. "tax"
  present, "capital"/"gains" absent) is never wrongly flagged.
- Shared helpers `_passage_vocab` (text + title) and `_query_words` (raw word →
  content tokens); `coverage()` refactored onto `_passage_vocab` so the coverage
  signal and the uncovered list are computed over exactly the same vocabulary.

### Gate (`gate.py`)
`GateDecision` gains `report`. `decide()` builds it in each refusal branch:
- `no_source` — no hits; explanation names the uncovered concepts.
- `weak_coverage` — hits, but a signal fell short; carries both `SignalCheck`s
  and the uncovered concepts.
- `no_groundable_statement` — signals passed but no sentence was citable.
The existing `reason` strings are left byte-for-byte unchanged (backward compat);
the richer prose lives in `report.explanation`.

### Engine (`answer.py`)
Empty question → `empty_question` stage; gate refusal → carries `decision.report`.

### Eval (`eval.py`)
New first-class metric **refusals explained** (`abstentions_explained /
abstentions`) folded into `PASS`. A silent refusal is now a regression, exactly
like an ungrounded claim.

### Web (`RefusalCard.tsx`, `types.ts`, `styles.css`)
When a report is present its explanation supersedes the generic one-liner; a
`RefusalDiagnostics` panel shows uncovered-concept chips and per-signal meters
(value / threshold, pass/fail), reusing the trust/freshness chip language.

## Safety argument

The change touches only paths that already return non-answers. It adds no way to
*emit* a claim, and does not read or alter the thresholds, the sentence-emission
rule, or the faithfulness verifier. Therefore it cannot convert a refusal into an
answer — verified end-to-end: an answer response carries no `report` key at all.

## Verification

- Server: 165 → **185** pytest green (new coverage in bm25/gate/engine/api/eval,
  including the three refusal stages and the signal value/pass invariant).
- Honesty eval: `PASS`, **refusals explained 4/4** over the golden set.
- Web: 15 → **17** vitest green; `tsc` + `vite build` clean; refusal state axe-clean.
- End-to-end over real HTTP (uvicorn + JSON): `no_source` and `weak_coverage`
  refusals serialize their report; an answer carries none.

## Adversarial review

An 11-agent, four-lens review (correctness, honesty-posture, web/a11y,
test-quality), each finding independently verified. The **honesty-posture lens
found nothing** — the additive-safety invariant held under attack. Seven
findings were confirmed and all fixed (`6d06b99`): one real display bug (a
`SignalCheck` showed `round(value)` while deriving `passed` from the raw score,
so a 0.599 coverage could render as "0.6 / 0.6 needed" yet be marked failed —
now the shown value can never contradict its marker), one cosmetic web nit
(empty diagnostics container on a stopword-only refusal), and five test-coverage
gaps (the `no_groundable_statement` stage and both-signals-passed path were
untested; the `_phrase_terms` overflow, the signal invariant, and a
self-fulfilling uncovered-terms test were all strengthened).
