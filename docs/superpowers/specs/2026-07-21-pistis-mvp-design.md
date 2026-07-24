# Pistis MVP — Design (2026-07-21)

Parent spec: `Pistis - Product Spec.md` (iCloud Task Register, 2026-07-19).
That document defines the product thesis, competitive gap, and regulatory
guardrails. This document records the **MVP build-shape decision** and the
concrete design. Decision made autonomously in the 2026-07-21 session under
the user's standing autonomy directives; queued for user review.

## 1. The decision: gate-first, extractive-core, LLM-optional

Three build shapes were considered:

| Shape | Verdict |
|---|---|
| **A. Gate-first extractive core, LLM-optional** | **CHOSEN** |
| B. LLM-first RAG app (Claude in the loop from day one) | Rejected: needs an API key immediately (credential handoff blocks autonomous build), tests become non-deterministic, and the honesty gate degrades into prompt engineering — inheriting the exact citation-mismatch failure the product exists to kill. |
| C. Eval-harness only (no product surface) | Rejected: proves gate calibration scientifically but produces nothing demonstrable; weak venture/portfolio artifact. |

**Why A:** the product's two unoccupied positions (per-claim grounded
citation + default-deny abstention) are *properties of the gate, not of the
language model*. An extractive pipeline — retrieve, select only
source-supported claims, emit each with a named+dated citation, abstain below
threshold — proves both positions with **deterministic, testable behaviour**
and zero per-query cost. An LLM composer slots in later behind a provider
interface and must pass the *same* grounding verifier (spec §5: "the answer is
assembled from what the sources support, not the model's parametric memory").

## 2. Components

### 2.1 Corpus (`pistis/corpus`)
- **Manifest-driven** (`corpus/manifest.json` in-repo): each entry =
  `{id, domain, title, org, kind, locator, why, licence}`.
  - `kind: govuk` → fetched via the GOV.UK Content API
    (`https://www.gov.uk/api/content/<path>`) — official, structured JSON,
    **Open Government Licence v3.0** (clean legal reuse with attribution).
  - `kind: html` → curated FCA / MoneyHelper pages fetched as HTML and
    reduced to text (small, hand-picked set; cited-and-linked, not
    republished).
- **Snapshot store** (`data/corpus/*.json`, gitignored): normalised documents
  split into passages, each carrying `source_org, title, url, fetched_at,
  last_updated (when the source provides it)`. Test fixtures are frozen
  snapshot excerpts committed under `server/tests/fixtures`.
- Six domains from the spec: savings/ISAs, pensions, mortgages, tax,
  budgeting, scams/consumer-protection.

### 2.2 Retrieval (`pistis/index`)
- BM25 over passages (own small implementation — no heavyweight deps on this
  locked-down box), with domain filtering and simple UK-finance synonym
  expansion (e.g. "LISA" ↔ "Lifetime ISA"). Deterministic scoring.

### 2.3 Engine (`pistis/engine`) — the product
- **Advice-boundary classifier** (`classifier.py`): rule-based detection of
  personal-recommendation-shaped *questions* ("which should I pick", "what
  should I do", "best X for me", named products + suitability) → returns a
  **routing event**, never an answer. Patterns derived from spec §4
  (PERG 8.30B traps: implicit suitability, multi-factor narrowing).
- **Grounding gate** (`gate.py`): a candidate claim (a passage-derived
  sentence/extract) is emitted only if tied to a specific supporting passage
  above a support threshold. Whole-answer rule: if top-passage relevance or
  domain coverage is below threshold → **ABSTAIN** with an honest statement
  and routing (MoneyHelper + FCA-register links).
- **Answer assembly** (shipped in `engine/answer.py`, `Engine.ask` — there is
  no separate `composer.py`): assembles an **answer card**:
  ordered claims, each with `{text, citation{org,title,url,dates}, confidence}`.
  Confidence tiers per spec: `established` (single authoritative source,
  current), `depends` (rules with personal-circumstance branches — flagged,
  not resolved), `uncertain` (conflicting/stale sources).
- **Routing** (`routing.py`): the defer-to-adviser event: explains *why*
  regulated advice carries protections (FOS/FSCS), links MoneyHelper
  guidance + FCA Register.
- Both gates must pass — grounded AND guidance-only — before anything is shown
  (spec §5).

### 2.4 Providers (`pistis/providers`) — optional, off by default
> **Implementation status (as of 2026-07-23): NOT BUILT.** This subsection is
> aspirational design, not a description of shipped code. `pistis/providers/`
> does **not** exist (no package, no `base.py`/`extractive.py`/`claude.py`).
> The live MVP is 100% deterministic and extractive — there is no code path
> today by which an LLM could rephrase or generate answer text. Anyone
> reviewing the product (legal, compliance, security) should review the
> extractive engine only. The Claude composer remains a future build gated on
> an `ANTHROPIC_API_KEY` supplied via the credential-handoff flow; when added,
> it must pass the same `engine/faithfulness.py` grounding gate that already
> guards every emitted claim.
- `base.py` defines `Composer` protocol; `extractive.py` is the default.
- `claude.py` (Anthropic API) may *rephrase* grounded claims for fluency but
  every output sentence must re-verify against its cited passage (token-overlap
  entailment check in MVP); failing sentences fall back to the extractive
  form. Absent `ANTHROPIC_API_KEY`, the engine runs fully extractive.

### 2.5 API + UI
- **FastAPI** (`pistis/api/app.py`): `POST /ask` → `AnswerCard | Abstention |
  RoutingEvent` (discriminated union), `GET /corpus/status` (doc counts,
  fetch dates), `GET /health`. Runs read-only over the snapshot; logs every
  Q→outcome (spec §4F monitoring) to a local JSONL — no user accounts, no
  tracking (83% privacy fear → MVP collects nothing).
- **Web** (`web/`, React+Vite+TS): single screen — ask box, then an
  **answer card** (not a chat wall): claims with inline numbered citations,
  per-citation source badge (GOV.UK / HMRC / FCA / MoneyHelper) + fetched/updated
  dates, confidence tier chips, persistent guidance-not-advice banner,
  distinct honest **abstain** and **routing** states. Skeleton loading state.

## 3. Regulatory posture built in (from spec §4)
- Persistent disclaimer (exact spec wording) on every surface incl. API responses.
- Hard "NEVER" list enforced by classifier + composer templates: no "you
  should", no product/provider suitability, no personalised narrowing.
- Product-neutral: no affiliate/apply links anywhere (s21 perimeter).
- Red-team fixture suite: "what should I invest in?", "best ISA for me?",
  "I have £20k and two kids, which pension?", etc. → must ALL produce routing
  events, asserted in CI-grade tests.

## 4. Testing
- pytest; deterministic (frozen fixtures, no network in tests).
- Unit: manifest validation, passage split, BM25 ranking, classifier
  (positive + negative cases), gate thresholds (answer/abstain boundaries),
  composer citation integrity (every claim has ≥1 citation — structural
  invariant test), provider fallback.
- Red-team suite as above; plus "gate paradox" calibration test set:
  in-corpus questions must answer, out-of-corpus must abstain.
- Frontend: vitest component tests for the three response states; axe
  accessibility pass on the rendered card (standing quality gate).

## 5. Explicitly NOT in the MVP
Per parent spec §6: no product recommendations, no personalisation over user
data, no accounts, no monetisation, no deployment (build-only; deploy gate
applies), no proprietary-content ingestion (MSE/Which?), no targeted-support
features (FCA permission regime, live 6 Apr 2026).

## 6. Open items queued for the user
1. Review this MVP scope decision (shape A) — renameable/reversible.
2. Compliance/lawyer sign-off remains a hard gate before any launch or
   monetisation (research caveat, restated).
3. Whether to add the Claude-composer mode (needs an API key via the
   credential-handoff flow) after the extractive core is green.
