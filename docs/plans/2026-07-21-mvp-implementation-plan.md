# Finance Answer Engine MVP — Implementation Plan (2026-07-21)

Design: `docs/superpowers/specs/2026-07-21-mvp-design.md`.
Each task = commit+push increment (resumability directive). Order chosen so
the repo is always green and the highest-risk piece (the gate) lands first.

## Tasks

1. **Scaffold + docs** — repo, README, .gitignore, design doc, this plan,
   SESSION_HANDOFF. Private GitHub repo `GreenPandaTech/FinanceAnswerEngine`. ✅ when pushed.
2. **Corpus curation (background workflow)** — 6 domain agents fan out over
   GOV.UK/FCA/MoneyHelper, verify each GOV.UK Content API path resolves,
   return manifest entries. Merge → `server/finance_answer_engine/corpus/manifest.json`.
3. **Core models + manifest** (`finance_answer_engine/models.py`, `corpus/manifest.py`) —
   dataclasses for Passage, Claim, Citation, AnswerCard, Abstention,
   RoutingEvent; manifest load/validate. Tests.
4. **Passage store + splitter** (`corpus/store.py`) — normalise docs into
   passages with source metadata; frozen fixtures. Tests.
5. **BM25 retrieval** (`index/bm25.py`) — tokeniser, UK-finance synonyms,
   deterministic ranking. Tests.
6. **Advice-boundary classifier** (`engine/classifier.py`) — rule patterns +
   red-team fixture suite (all must route). Tests.
7. **Grounding gate + composer + routing** (`engine/`) — thresholds,
   answer/abstain/route assembly, citation-integrity invariant. Tests.
8. **Fetchers** (`corpus/fetch.py`) — GOV.UK Content API + curated HTML,
   snapshot writer; `python -m finance_answer_engine.corpus.refresh`. Network code excluded
   from unit tests (fixture-driven); one manual smoke run.
9. **FastAPI app** (`api/app.py`) — /ask, /corpus/status, /health, JSONL
   outcome log, disclaimer in every response. Tests via TestClient.
10. **Web UI** (`web/`) — Vite React TS answer-card screen, three states,
    citations + dates + confidence chips, banner. Vitest + axe.
11. **Red-team + review pass** — adversarial workflow over the gate and
    classifier; fix findings; `pytest` + `npm test` green; final push.
12. **Real corpus smoke** — run refresh against live GOV.UK for the merged
    manifest; ask 10 golden questions end-to-end; record results in handoff.

## Risks / notes
- Locked-down box: pure-Python BM25 (no numpy dep needed), pip installs into
  `.venv` as with Triton.
- GOV.UK Content API is public/no-key; FCA/MoneyHelper fetched politely
  (few pages, one-shot snapshot).
- No deployment of any kind (deploy gate). Anonymity: no personal identifiers
  anywhere in repo.
