# Finance Answer Engine — technical design

Derived from the code on 2026-08-03, not from the README.
Requirements: [PRD.md](PRD.md).

## Two gates, four checks

A question passes through two independent gates before anything is shown.

The **advice-boundary classifier** runs first, before any retrieval, and converts
personal-recommendation-shaped questions into routing events. What survives goes
to a pure-Python **BM25 index** over passages of a curated corpus snapshot, and
then to the **grounding gate**, which must clear four separate checks: absolute
retrieval score, IDF-weighted query coverage, topical aboutness of the source
document, and per-sentence faithfulness against the passage the sentence came
from.

Anything failing any of them becomes an abstention carrying a report of *which*
check failed and by how much. Claims are verbatim sentences; nothing is
generated, computed or paraphrased.

There is no database, no model, no API key and no network call at query time.
Every stage is a pure function over a JSON snapshot, which is why the honesty
numbers are reproducible from a committed fixture.

## The constants, all in one file

Calibration is per-corpus and is this project's core execution risk, so every
threshold lives visibly together in `engine/gate.py` rather than being scattered
where each is used.

| Constant | Value | What it gates |
|---|---|---|
| `MIN_TOP_SCORE` | 2.0 | Absolute BM25 score of the best hit |
| `MIN_COVERAGE` | 0.6 | IDF-weighted share of query terms found in one passage |
| `MIN_TOPIC_SHARE` | 0.5 | Share of the question's IDF meaning the document is *about* |
| `MIN_SENTENCE_OVERLAP` | 0.25 | Query-term overlap for a sentence to be quotable |
| `MAX_CLAIMS` | 6 | Claims per answer |
| `ABOUTNESS_PASSAGES` | 2 | Distinct passages using a term before the doc counts as about it, capped at `ceil(passages/2)` for short documents |
| `GROUNDED_TOKEN_FRACTION` | 0.85 | Faithfulness verdict `grounded` |
| `PARTIAL_TOKEN_FRACTION` | 0.5 | Faithfulness verdict `partial` |
| `AGING_DAYS` / `STALE_DAYS` | 180 / 365 | Snapshot-age freshness tiers |
| `RETENTION_DAYS` | 30 | Ask-log purge window |

## Three files carry all state

No database. Their shapes are the data model.

**`finance_answer_engine/corpus/manifest.json`** declares what the engine is
allowed to ground on: 55 live entries (26 GOV.UK, 21 HMRC, 8 FCA) plus an
`excluded` array of 21 curated-but-unfetchable MoneyHelper and Pension Wise
entries retained for provenance. Validated on load — duplicate ids and locators
rejected, `kind == "govuk"` requiring a path-shaped locator and a GOVUK or HMRC
org, `kind == "html"` requiring an https URL on the two-host allowlist.

**`data/corpus/snapshot.json`** (gitignored, rebuildable) holds documents, each
with `doc_id`, `title`, `org`, `url`, `fetched_at`, optional `last_updated` and
`text`.

**`logs/ask.jsonl`** (gitignored, never committed) holds one object per question:
`ts`, `question`, `kind`. Nothing else. No id, no account, no IP.

In memory, `models.py` is the whole vocabulary:

| Type | Notes |
|---|---|
| `Passage` | A chunk of 3 sentences with full citation metadata. `in_example: bool` is set by the **chunker**, not the gate — an example introduced in one chunk runs its arithmetic into the next, which carries no marker of its own, so the flag is carried exactly one chunk forward. |
| `Claim` | Verbatim text + `Citation` + confidence tier (`established` / `depends` / `uncertain`). |
| `ClaimVerdict` / `TrustReport` | Grounding verdict, 0–1 score, and the char span in the source passage. |
| `Freshness` / `FreshnessReport` | Per-claim verdict (`current` / `aging` / `stale`), snapshot age, detected tax year. |
| `SignalCheck` / `AbstentionReport` | The refusal proving itself: stage, explanation, each signal against its threshold, uncovered terms. |
| `Response = AnswerCard \| Abstention \| RoutingEvent` | The product's entire output surface. The two non-answers are first-class, not error states. |

Some fields are null on older data. `Citation.last_updated` is `None` whenever
the source declares no update date, and all FCA HTML entries are in that category
by construction, since `fetch_entry_text` returns `None` for `kind == "html"`.
Both consumers handle it: `_confidence_for` downgrades an undated source with no
checkable figure to `uncertain`, and the UI omits the "updated" element rather
than rendering an empty one. `AnswerCard.trust_report` and `.freshness` are
`Optional` so the layers could be added additively without breaking existing
constructions — though a real answer from `Engine.ask` always carries both.

## Interfaces

**HTTP** — `api/app.py`, FastAPI, created by the factory
`create_app(snapshot_path, log_path)`.

| Endpoint | Contract |
|---|---|
| `POST /ask` | `{"question": str}`, 1–500 chars enforced by Pydantic; whitespace-only rejected 422. Returns `asdict(Response)` — the discriminant is `kind`. Appends one log line. |
| `GET /corpus/status` | Document count, passage count, sorted org list, sorted fetch dates. Provenance, not telemetry. |
| `GET /health` | `{"status": "ok"}`. |

CORS is allowed for `http://localhost:5173` and `http://127.0.0.1:5173` only,
methods `GET` and `POST`. `create_app` raises `FileNotFoundError` at startup if
the snapshot is missing, naming the command that builds one: the server refuses
to run without a corpus rather than serving an empty one.

**Engine** — `Engine(index).ask(question, reference_date=None) -> Response`.
`reference_date` is injected so freshness has no hidden clock; production passes
`date.today()`, tests pin it.

**Index** — `Bm25Index(passages)` with `search(query, k=8)`,
`coverage(query, hits, top_n=4)`, `topic_share(query, doc_id)`,
`is_about(doc_id, term)` and `uncovered_terms(query, hits, top_n=4)`. BM25 with
`K1 = 1.5`, `B = 0.75`, Lucene-style smoothed IDF that is never negative. Pure
Python on purpose: no native dependency, and scoring stays reproducible, which
the gate's calibration tests rely on.

**CLIs** — `python -m finance_answer_engine.{corpus.refresh, eval, bench, gaps,
privacy.retention}`. All stdout-only, all offline except `corpus.refresh`.

**Web** — `POST /api/ask` through the Vite dev proxy to `127.0.0.1:8000`.
`web/src/types.ts` mirrors the server's dataclasses by hand. There is no codegen,
so the two can drift, and the mirror is the thing to update when a model changes.

## No access control, and the gaps that would matter

There is none, and that is a design position rather than an omission. The service
has no accounts, no sessions, no roles and no per-user data. It serves a
read-only corpus of entirely public information, so there is nothing to scope a
policy by, and no database means no RLS, no grants and no security-definer
functions.

What *is* enforced:

- **Input is validated at the boundary**, by schema — Pydantic
  `Field(min_length=1, max_length=500)` — rather than hand-rolled checks. That
  500-character cap is the only thing standing between the engine and an
  unbounded tokenisation cost.
- **The corpus fetcher is host-allowlisted and re-checks after redirects.** `_get`
  compares `response.geturl()` against the allowlist, so a compromised or
  misconfigured source cannot bounce the fetch off the list. 30-second timeout,
  deliberate inter-fetch delay, declared User-Agent.
- **CORS is pinned to the two localhost dev origins.**
- **No secrets exist.** Nothing keyed, nothing to leak, no `.env` in any commit
  that has ever existed.
- **The ask log is gitignored** and purged at every startup.

And the gaps that would matter if this were ever deployed, listed rather than
glossed. No rate limiting on `/ask`, where the tokenisation and BM25 scan are the
expensive part. No authentication anywhere. The ask log is world-readable to
anything that can read the filesystem. And there is no alerting, so the honest
answer to "how would we know if we were attacked" is that we would not.

None of these is acceptable for a public deployment, and all of them are why the
project is build-only.

## Failure modes

| What breaks | Who notices | How we detect it | How we undo it |
|---|---|---|---|
| Snapshot missing or unreadable | Whoever starts the server | `create_app` raises at startup naming the refresh command; the CLIs print how to build one instead of a traceback | Run `python -m finance_answer_engine.corpus.refresh` |
| A source page changes shape and extracts as navigation chrome | Nobody, without the benchmark — this actually happened | `python -m finance_answer_engine.bench --validate` re-checks every label against the current corpus; a before/after character count per document catches it | Fix the extraction rule in `corpus/fetch.py` and re-fetch |
| A source's URL dies | The refresh run | Named in the failure list at the end of the run; the corpus is still written from what succeeded | Fix or remove the manifest entry |
| Thresholds drift out of calibration as the corpus grows | Nobody automatically | The 131-question benchmark, scoring false answers and false refusals **separately** — a single accuracy figure would average a serious failure against a mild one | Revert the change; the constants are all in one file |
| Labels rot as the corpus grows | The benchmark itself | `--validate` refuses to score against labels known to be broken | Re-derive the labels in `tests/fixtures/bench_build.py`; never hand-edit `bench.json`, which a test pins to the build script's output |
| Corrupt byte in the ask log at startup | Nobody — deliberately | `purge_expired` warns and changes nothing, rather than raising (which would stop the server) or rewriting a file it could not fully read (which would silently drop exactly the lines it could not decode) | Delete or repair the log file |
| A claim is grounded but irrelevant | The benchmark's `near_miss` class | The known residual: 6 of 50, all `near_miss`. Topical aboutness cannot separate "covers the subject" from "covers the specific fact asked for" | Not fixable by tuning — needs a question-type signal |

## Rollback, and the one irreversible step

There is no database and no schema, so nothing migrates. Every part of this
system rolls back by `git revert` plus at most one command, and no persistent
state can be corrupted by a code change.

**Code and thresholds** revert cleanly. The gate constants live in one file; no
migration, no stored derived data, nothing to backfill.

**The corpus** is rebuilt by re-running
`python -m finance_answer_engine.corpus.refresh`. It takes a few minutes, because
of the deliberate inter-fetch delay, and needs network. The refresh is safe by
construction: it writes only if at least one document was fetched, individual
failures are reported and skipped rather than aborting the run, and any document
extracting fewer than 300 characters is treated as a failed extraction rather
than a short source. The snapshot is derived data and gitignored, so a bad
snapshot is never a bad commit.

That refresh is nonetheless **the one irreversible step in the system**: it
overwrites the previous snapshot in place, and the previous *fetch dates* cannot
be recovered. Acceptable, because the snapshot is reconstructible from the
manifest and the sources, and because a stale snapshot is exactly what freshness
assessment exists to flag. If a specific snapshot ever mattered, copy it aside
before refreshing.

**The ask log** is destructive by design when purged — that is the privacy
promise — and correctly not undoable. **Deployment** has nothing to roll back,
because there is no deployment.

## Test plan

283 pytest plus 17 vitest, 95.21% line coverage against a 90% floor. The floor is
a floor rather than a target: the network fetch paths are deliberately outside
the unit suite, so chasing 100% would mean testing `urllib` rather than this
product.

**Positive.** Golden questions still answer, with every claim cited and grounded
(`test_engine`, `test_eval`, `tests/fixtures/golden.json`). The relevance guard
carries a test pinning that it can only ever *remove* hits, so it can never turn
a refusal into an answer.

**Negative.** `AnswerCard` refuses construction with no claims, with an uncited
claim, or with a trust report that is not fully grounded (`test_models`). The
classifier's red-team suite of 72 cases asserts *which* rule fired, so a case
cannot silently be caught by an unrelated pattern; each new fixture was verified
against the pre-fix pattern set first, to confirm it was a genuine escape rather
than a relabelled existing catch.

**Boundary.** Every abstention stage, including the two easy to conflate
(`off_topic` against `no_groundable_statement`). The signal-display invariant, so
a shown value can never contradict its own pass/fail glyph. Short documents where
`ABOUTNESS_PASSAGES` must scale with length. Worked examples spanning a chunk
boundary. Malformed and undecodable log lines. Missing snapshot and missing log.

**Privacy invariants.** The gap report's serialised field surface is pinned,
which kills any mutant that adds a question field, and every absence assertion
carries a positive control. This exists because an earlier version of that test
asserted a tokenizer tautology and passed with the entire privacy layer deleted.

**Accessibility.** `jest-axe` assertions in the web suite, so a11y is gated
rather than inspected.

## Build order — every instrument found a defect

1. Models, corpus manifest, fetch and store, BM25 index.
2. Advice-boundary classifier, then the grounding gate, then the engine
   orchestrator; FastAPI surface; React claim ledger.
3. Faithfulness verifier and trust report; freshness; honesty eval.
4. Explainable refusal (the abstention report), server then web.
5. Corpus-gap report; privacy notice and retention purge.
6. Answerability benchmark — which then found the relevance gap and an
   advice-boundary escape, both fixed.

The ordering has a point. Every measurement instrument was built **after** the
thing it measures, and immediately found a defect in it: the benchmark caught the
`worth it for me` classifier escape on its first run.

## Two open questions

A question-type signal — does this passage state the *kind* of fact asked for, a
rate, a threshold, a deadline? — is the only credible route past the residual six
false answers. It must be measured on questions drawn from a real ask log; 131
authored questions cannot show how it generalises.

The hand-maintained mirror between `models.py` and `web/src/types.ts` is a drift
risk with no test. Generating the TypeScript from the dataclasses would close it.
