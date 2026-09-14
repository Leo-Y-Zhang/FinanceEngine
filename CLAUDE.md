# FinanceEngine

A trust-first, UK-first personal-finance answer engine built around a
default-deny "honesty gate": it answers a question only when it can attach a
named, dated, per-claim citation from a curated UK-authoritative corpus
(GOV.UK/HMRC, FCA, MoneyHelper/Pension Wise) — otherwise it abstains and
routes to guidance rather than guessing. The architecture is
classifier → BM25 retrieval over the curated corpus → a per-claim grounding
gate → an answer card of cited claims, or an explicit abstain. It is an
extractive core (LLM-optional; any future LLM composer must pass the same
grounding gate) with a Python FastAPI server (`server/`) and a React +
TypeScript web client (`web/`). This is information/guidance, not regulated
financial advice.

## Directory layout

- `server/finance_engine/` — `engine/` (classifier, grounding/gate logic),
  `index/` (BM25), `corpus/` (manifest-driven source snapshot + refresh),
  `api/` (FastAPI app), `privacy/`.
- `server/tests/` — unit tests plus `server/tests/fixtures/bench_build.py`.
- `web/src/` — React app; `web/src/components/`, `web/src/__tests__/`
  (includes axe accessibility assertions).
- `docs/` — architecture/handoff docs.

## Install

```
cd server && python3.12 -m venv .venv && .venv/bin/pip install -e '.[dev]'
cd web && npm ci
```
(`npm install` works too if the lockfile isn't pristine; CI uses `npm ci`.)

## Lint / format / typecheck

Server (ruff; config in `server/pyproject.toml`, `line-length = 100`,
`target-version = "py312"`, explicit `select` list `E,W,F,I,UP,B,C4,SIM,ISC,RUF`
with deliberate per-rule and per-file ignores — see the pyproject comments):
```
cd server && .venv/bin/ruff check finance_engine tests
```
Web (TypeScript, no separate lint script beyond typecheck):
```
cd web && npx tsc --noEmit
```

## Test

Server (pytest with a coverage floor):
```
cd server && .venv/bin/pytest --cov=finance_engine --cov-report=term-missing
```
288 tests, ~95% coverage observed; floor is `fail_under = 90` in
`[tool.coverage.report]` (a floor, not a target — the network fetch path is
deliberately excluded from the unit suite). Fastest useful subset — one
file, e.g.:
```
.venv/bin/pytest server/tests/test_engine.py -q
```
Web (vitest, includes axe a11y checks):
```
cd web && npm test -- --run
```
Fastest useful subset:
```
cd web && npx vitest run src/__tests__/App.test.tsx
```
Full web gate also includes `npx tsc --noEmit` and `npm run build` (vite
production build) — both should stay clean per CI.

## Verification gate (source of truth)

Two purpose-built checks beyond pytest/vitest are what this repo treats as
its real claims:
- `python -m finance_engine.eval` — the honesty-gate promise, run over the
  committed fixture corpus (no network needed): reproduces to
  21/21 answerability, 33/33 claims grounded, 0 unsupported, `RESULT: PASS`.
- `python -m finance_engine.bench --validate` — benchmark labels vs. the live
  corpus; needs a network fetch (`finance_engine.corpus.refresh`) not present
  in a clean clone, so it is skipped in this environment.
CI runs `ruff check`, pytest+coverage, and `python -m finance_engine.eval` for
the server; `tsc --noEmit`, `npm test -- --run`, and `npm run build` for web —
these are the same commands documented in the README, by design.

## Environment caveats (from audit)

- `finance_engine.bench --validate` requires network access to refresh the
  live corpus snapshot; it is gitignored and not available offline. Skip it
  unless network is confirmed.
- Coverage floor (90%) is intentionally below the observed ~95% so ordinary
  churn doesn't trip it while a genuine regression would.
- No Windows-only or GPU-specific code paths.

## CI / conventions

- `ci.yml` has three jobs: `server` (ruff, pytest+coverage, `pip-audit
  --strict` against a frozen non-editable requirements freeze, then the
  fixture-corpus honesty eval), `web` (tsc, vitest incl. axe, vite build,
  `npm audit --audit-level=moderate`), and `gitleaks` (full-history secret
  scan). Steps are written to match README/docs commands verbatim.
- Ruff ignores are deliberate and documented per-rule in `pyproject.toml`
  (e.g. `E731` for one-line lambda IDF weights, `RUF001-003` for intentional
  en/em dashes in prose, per-file `E501` allowance for `tests/*` fixtures and
  `classifier.py`'s long regex). No mypy/type-checker is configured for
  Python; `web/tsconfig.json` has `strict: true` plus `noUnusedLocals`,
  `noUnusedParameters`, and `noFallthroughCasesInSwitch`, enforced via
  `tsc --noEmit`.
