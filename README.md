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
