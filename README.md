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
