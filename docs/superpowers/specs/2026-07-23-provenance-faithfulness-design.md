# Design — Provenance & Faithfulness Layer

**Date:** 2026-07-23
**Status:** Approved (self-approved under the owner's standing autonomous-work
directive; owner was offline for the build. Reversible; additive-only.)
**Scope:** One cohesive feature that makes Finance Answer Engine's core promise — *every claim
is grounded in an official source; nothing is asserted that a cited source does
not support* — **explicit, enforced, visible, and measurable.** This is the
literal expression of the portfolio thesis "software that proves its own claims."

## Motivation

Today Finance Answer Engine emits each answer claim as a **verbatim sentence** extracted from a
single source passage (`gate.py:_sentence_claims`), and provenance attaches via
`Citation.from_passage` — which **drops the passage text and id**, keeping only
doc-level metadata. So the grounding of a claim is *structurally true today* but
**unproven and invisible**: there is no artifact that demonstrates a claim is
backed by its source, no guard that would stop an *ungrounded* claim (e.g. from
the planned optional LLM composer, which `README` requires to "pass the same
gate"), and no reproducible measurement of the honesty promise.

This feature closes that gap with three tightly-related parts.

## Component 1 — Deterministic faithfulness verifier (`engine/faithfulness.py`)

A pure, keyless, network-free function (mirrors the pure-function style of
`gate.py`/`bm25.py`):

```
verify(claim_text, passage_text) -> Grounding
```

`Grounding` (new frozen dataclass in `models.py`):
- `verdict: Literal["grounded", "partial", "unsupported"]`
- `score: float`  — 0..1 grounding score
- `passage_id: str`  — the source passage the claim was checked against
- `span: tuple[int, int] | None`  — (start, end) char offsets of the matched
  text **within the source passage**, when a contiguous match is found

Algorithm (deterministic, extractive-appropriate):
1. **Substring/containment fast path** — normalise whitespace and case; if the
   claim text is a contiguous substring of the passage, `verdict="grounded"`,
   `score=1.0`, `span=(start, end)` of the match. (This is the current reality
   for every gate-emitted claim, so it must be exact and cheap.)
2. **Token-overlap fallback** — otherwise reuse `bm25.tokenize()` (identical
   token model: lowercase, stopword-drop, plural-fold, synonym-expand) and
   compute `grounded_fraction = |claim_tokens ∩ passage_tokens| / |claim_tokens|`.
   `>= 0.85` → `grounded` (paraphrase within source vocabulary); `>= 0.5` →
   `partial`; else `unsupported`. `span=None` for the fallback.
3. Empty claim or empty passage → `unsupported`, `score=0.0`.

Thresholds live at the top of the module as named constants (like `gate.py`).

**Why it earns its keep even though claims are verbatim today:** it is the
*enforcement mechanism and the evidence*. It (a) guards the emission path so an
ungrounded claim can never ship, (b) yields the exact source span the UI shows,
(c) is the metric the honesty-eval reports.

## Component 2 — Per-answer Trust Report (surfaced end-to-end)

New frozen dataclasses in `models.py`:
- `ClaimVerdict{ verdict, score, passage_id, span }` — one per emitted claim,
  in claim order.
- `TrustReport{ verdicts: tuple[ClaimVerdict, ...], grounded: int, total: int,
  all_grounded: bool }` — the per-answer summary.

`AnswerCard` gains **one optional field with a default**:
`trust_report: TrustReport | None = None` (placed after `claims`, before
`disclaimer`). Additive + defaulted, so:
- `AnswerCard.__post_init__` still validates only `claims` (unchanged path); it
  is **strengthened** to *also* assert, *when a `trust_report` is present*, that
  `all_grounded` is true — an ungrounded claim in a shipped answer becomes a
  construction-time error (defence in depth behind the gate filter).
- `asdict(response)` in `POST /ask` serialises the nested report automatically —
  **no API-schema code change**, and existing tests assert only on present keys,
  never the absence of extra keys, so they keep passing.

**Enforcement in the gate:** `_sentence_claims` computes `verify(sentence,
passage.text)` at claim-construction (where the passage is still in scope) and
**drops any sentence whose verdict is not `grounded`** (a new emission filter,
same posture as `MIN_SENTENCE_OVERLAP`). It threads the per-claim `Grounding`
out so `Engine.ask` can assemble the `TrustReport` on the `AnswerCard`. Net
effect: **the engine cannot emit an answer containing an ungrounded claim.**

**Frontend:** add the optional `trust_report`/`ClaimVerdict` types to
`web/src/types.ts` (hand-maintained mirror), and render in
`AnswerLedger.tsx`'s `Receipt`: a per-claim "✓ grounded in source" chip
(with the score/span available on hover/title), plus an overall trust line in
`AnswerLedger` ("N of N claims grounded in their cited source"). The frontend
already tolerates extra fields; the field is optional so refusals/old shapes are
unaffected.

## Component 3 — Reproducible honesty-eval CLI (`finance_answer_engine/eval.py`)

`python -m finance_answer_engine.eval [--snapshot PATH] [--json]` — mirrors the existing
`python -m …` module pattern (`corpus/refresh.py`, `privacy/retention.py`).
Loads a snapshot → `Bm25Index` → `Engine`, runs a **shared golden set** and
reports metrics:
- **Faithfulness (the core promise):** across every `AnswerCard`, every claim's
  `verdict == "grounded"` → `grounded_rate` (target 100%), `unsupported` count
  (target 0).
- **Citation completeness:** every claim carries a dated `https://` citation.
- **Answerability accuracy:** answer / abstain / route matches the expected
  label per golden question.
Human-readable table by default; `--json` for a machine record. Deterministic
over the committed fixture snapshot (`server/tests/fixtures/snapshot.json`) — no
network — so it runs in CI/tests too.

**Golden set:** promote the question lists currently embedded in `test_gate.py`
and `test_classifier.py` into a shared `server/tests/fixtures/golden.json`
(`{question, expect: "answer"|"abstain"|"route"}`), consumed by BOTH the eval
and the existing tests (single source of truth; no behaviour change to the
tests — they read the same data they assert on now).

## Testing plan (TDD)

New/changed tests, all offline over the fixture snapshot:
- `test_faithfulness.py` — grounded (verbatim substring, exact span), partial,
  unsupported, empty, and a synthetic paraphrase; span offsets correct.
- `test_gate.py` — every emitted claim now has `verdict=="grounded"`; a
  synthetic ungrounded sentence is filtered out; existing answerable/abstain
  behaviour unchanged.
- `models` — `AnswerCard` with an all-grounded `TrustReport` constructs; one
  containing an `unsupported` verdict raises.
- `test_api.py` — `/ask` answer response now includes `trust_report` with
  `all_grounded true`; refusals unchanged.
- `test_eval.py` — the eval runs headless over the fixture, asserts
  `grounded_rate == 1.0`, `unsupported == 0`, and answerability accuracy == 1.0.
- Web: `AnswerLedger.test.tsx` — renders the grounded chips + overall trust line
  from a stubbed answer; a11y (axe) preserved; refusal path unchanged.

Gate: full suite stays green (137 pytest + 12 vitest baseline) and grows.

## Non-goals (YAGNI)

- No LLM composer (the verifier is designed to guard it later, but building it
  is out of scope).
- No new corpus sources / no network in the feature path.
- No change to gate thresholds, classifier, routing, privacy, or the response
  union shape (only an additive optional field).

## Rollout

Server first (verifier → models → gate wiring → eval), each increment green and
committed+pushed under the anonymous identity; then web; then docs
(`README` "Trust report" section + `SESSION_HANDOFF`). Finance Answer Engine is not an
auto-deploy repo, so pushes are safe.
