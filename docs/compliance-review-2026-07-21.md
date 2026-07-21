# Pre-Launch Legal/Compliance Review (informal, non-lawyer pass)

**Date:** 2026-07-21
**Reviewer:** Claude (agent), acting as a free "lawyer function" first pass
**Scope:** MVP scope decision in `docs/superpowers/specs/2026-07-21-pistis-mvp-design.md`
§1 (gate-first, extractive-core, LLM-optional) and §4 (regulatory posture), and
the live code in `server/pistis/` and `web/` as of this date.

## THIS IS NOT LEGAL ADVICE

I am not a solicitor and this is not a substitute for one. This is a
**free, automated triage pass** intended only to give a real, qualified
solicitor (UK financial-services / FCA-perimeter specialist, ideally also
familiar with UK GDPR and content-licensing) a head start before any real
launch, monetisation, or exposure to real users. **A qualified solicitor
must review this product before any of those things happen** — this
document does not discharge that requirement and should not be treated as
sign-off. Where I flag something as "likely fine," read that as "did not
find an obvious problem," not as clearance.

I did not call any paid legal-research tool. Findings on FCA/MoneyHelper
reuse terms below are based on live web searches of the regulator's and
MaPS's own published terms pages, done today; terms can change and should
be re-checked at review time.

---

## Executive summary

The architecture is unusually well set up for this review: two hard,
testable gates (advice-boundary classifier, then a default-deny grounding
gate) sit in front of every answer, both are exercised by an automated
red-team test suite, and the disclaimer is a structural field on every
response object rather than UI decoration. That is a genuinely strong
starting posture relative to most "AI answers your money questions" products.

That said, I found and fixed one real code bug (a licence-mislabelling
issue, below) during this review, and there are several items a solicitor
will want to look at closely before any real-user exposure. None of these
looked like "kill the project" issues; they are the kind of things that
turn into "add three sentences of copy" or "narrow this regex set" once a
lawyer has actually looked.

**Top items for a real lawyer's attention, ranked:**

1. **Content licensing for FCA (and, when re-added, MoneyHelper) HTML
   pages** (§2) — the manifest was silently labelling FCA content "OGL
   v3.0," which it is not. I patched the labelling bug, but whether the
   *actual reuse pattern* (extracting and republishing verbatim sentences
   with attribution) is within what FCA's copyright notice permits is a
   judgement call a lawyer should make, not code.
2. **Residual advice-boundary risk from a rule-based classifier** (§1) —
   the two-gate design is sound, but a regex classifier has an unbounded
   tail of paraphrases it cannot catch. This needs a lawyer's view on
   what red-team coverage is "enough" before real users can reach it,
   and probably a live-monitoring commitment as a condition of launch.
3. **No UK GDPR transparency notice for the local question log** (§3) —
   low current real-world risk (build-only, no deployment, log is
   gitignored and stays on the dev machine), but the moment this is
   deployed for real users, logging free-text financial questions without
   a privacy notice is a straightforward, well-known gap to close.

---

## 1. FCA regulatory perimeter — personal recommendation (Art 53 RAO) and financial promotions (s21 FSMA 2000)

### What exists

- `server/pistis/engine/classifier.py`: a rule-based classifier
  (`classify()`) runs **before retrieval** on every question. It matches
  14 named regex patterns (direct "should I", suitability framing,
  product superlatives, "people like me" implicit-suitability framing,
  named-provider + decision-verb combinations, etc.) plus a
  named-commercial-provider list (Vanguard, Nutmeg, Halifax, Monzo, …).
  A match returns a `RoutingEvent` — never an answer.
- `server/pistis/engine/answer.py` (`Engine.ask`): the classifier gate
  runs strictly before the grounding gate. Confirmed by
  `test_engine.py::test_personal_rec_wins_even_when_corpus_could_answer` —
  a question the corpus *could* answer still routes if it's
  personal-rec-shaped.
- `server/tests/test_classifier.py`: 27 positive (must-route) and 13
  negative (must-not-route) fixture questions, explicitly labelled as a
  "red-team suite," including 8 cases the file says were "escapes found
  by the 2026-07-21 adversarial review" — i.e. this has already been
  through one round of adversarial hardening.
- The corpus is **entirely** GOV.UK/HMRC/FCA/MoneyHelper/Pension Wise —
  no commercial provider content is ever ingested, so an answer can
  never cite or promote a specific firm, fund, or product. This is a
  strong structural mitigant against the s21 financial-promotion risk:
  there is no promotional content in the system to promote.
- The routing/abstain paths only ever link to MoneyHelper and the FCA
  Register (`engine/routing.py`) — never to a firm's own site or an
  affiliate link.
- I checked whether the LLM-composer path described in design doc §2.4
  (`providers/base.py`, `extractive.py`, `claude.py`) actually exists:
  **it does not.** `server/pistis/providers/` is an empty directory (no
  files at all, not even `__init__.py`). The live MVP is 100% extractive
  — there is no code path today that could have an LLM rephrase or
  generate suitability-adjacent language. This is reassuring from a
  determinism/compliance standpoint, but it means design-doc §2.3–2.4 is
  **aspirational**, not a description of the shipped code; worth
  correcting the doc or noting it clearly as "not yet built" so nobody
  reviews the wrong thing later.

### Gaps / residual risk

- **Regex classifiers have an unbounded false-negative tail.** Natural
  language has effectively infinite ways to phrase a personal-suitability
  question; the current 14-pattern set plus provider list is well
  thought through (it explicitly covers the PERG 8.30B "implicit
  suitability" and "people like you" traps) but *cannot* be
  exhaustive by construction. A paraphrase the red-team suite hasn't
  seen yet could slip through and receive a factual, correctly-cited,
  but contextually suitability-adjacent answer. This is not a coding
  defect — it's the structural limit of the "gate-first, extractive"
  shape chosen in the design doc — but a lawyer/compliance reviewer
  should decide how much red-team coverage, and what ongoing monitoring
  commitment (see next point), is required before this is safe to expose
  to real users.
- **The question log exists but nothing currently reviews it for
  classifier misses.** `server/pistis/api/app.py` already writes every
  `{ts, question, kind}` to `logs/ask.jsonl` (spec §4F "monitoring"), so
  the raw material for a misses-review process exists — there's just no
  process, cadence, or owner defined yet for actually looking at
  `"answer"`-kind outcomes to catch classifier escapes before they
  compound. Recommend this becomes an explicit, written condition of any
  launch (e.g. "N random answer-kind log lines reviewed weekly").
- **Verbatim second-person source text.** Because claims are extracted
  sentences from GOV.UK/HMRC prose, some cited text is itself phrased
  imperatively ("You must register for Self Assessment if…"). That's the
  source instructing the reader, not Pistis recommending a course of
  action, and each claim carries a visible citation "receipt" (org badge,
  link, dates) that should make the quotation nature clear — but a lawyer
  should sanity-check that the visual design (`web/src/components/AnswerLedger.tsx`)
  makes the "this is a quotation, not Pistis's advice" framing
  unambiguous enough, especially for the `depends`-confidence tier which
  sits directly next to factual content.

**Overall assessment:** the *architecture* is sound and unusually
testable for this kind of risk. The residual risk is the ordinary one for
any rule-based gate: coverage is a spectrum, not a binary, and a lawyer
needs to set the bar for "enough" before real users arrive.

---

## 2. Content licensing (GOV.UK / HMRC / FCA / MoneyHelper)

### GOV.UK / HMRC (`kind: "govuk"`)

Fetched via the official GOV.UK Content API
(`server/pistis/corpus/fetch.py`) and correctly licensed: GOV.UK/HMRC
content is published under the **Open Government Licence v3.0**, which
permits copying, adapting, and commercial or non-commercial use, subject
to attribution. This is genuinely clean.

**One real gap found and fixed:** OGL v3.0 requires the reuser to
*acknowledge the source*, and where no attribution statement is specified,
suggests wording such as *"Contains public sector information licensed
under the Open Government Licence v3.0."* That acknowledgement currently
appears **only in `README.md`** (a developer-facing file real end users of
the deployed product will never see) — it does not appear anywhere in the
live UI (`web/`) or API response. The per-claim citation shows org badge,
title, link, and dates, which is good practice and probably satisfies the
spirit of "acknowledge the source," but it does not contain the words
"Open Government Licence" anywhere a user can see. **Recommend:** add a
short, permanent OGL acknowledgement line somewhere on the product surface
(e.g. a footer) before any public launch — this is a small, cheap fix a
lawyer will likely ask for anyway.

### FCA and MoneyHelper (`kind: "html"`)

These are **not** under OGL, and I found a real bug during this review:
`server/pistis/corpus/manifest.py`'s loader was defaulting **every**
manifest entry's `licence` field to `"OGL v3.0"` regardless of `org` or
`kind` (`e.get("licence", "OGL v3.0")`), which silently mislabelled FCA
(and previously MoneyHelper) entries. **I fixed this** in the same commit
as this review: `_default_licence()` now returns an OGL label only for
`kind == "govuk"` entries, and a distinct, more cautious label for
FCA/MoneyHelper entries (with a pointer to their real terms pages), backed
by new regression tests (`server/tests/test_manifest.py`). This field
isn't currently surfaced to end users, so the live product wasn't
misrepresenting anything to a real person — but if it's ever wired into
the UI (e.g. "content licensed under X"), it would have been wrong for
every non-GOV.UK source.

Live-checked today (2026-07-21) via web search of the regulator's/MaPS's
own published terms:

- **FCA** (`fca.org.uk/panels/legal` — FCA's copyright notice): permits
  personal/internal use and short extracts "incidental to advice or other
  activities" with source acknowledgement, but states re-use "otherwise
  than as explicitly permitted... is prohibited unless prior written
  permission... has been obtained," and specifically calls out that
  reproducing material on external websites or "creating data feeds"
  requires prior written permission. **Pistis's actual pattern —
  extracting and republishing verbatim sentences from FCA pages, with
  attribution, as part of a structured product — is arguably closer to
  "a data feed" than "a short incidental extract."** This is the single
  content-licensing item most worth a lawyer's direct read: is what
  Pistis does within FCA's permitted-use carve-outs, or does it need
  the FCA's written permission? I can't make that call; a lawyer should.
- **MoneyHelper/MaPS**: downloadable materials are under
  **CC BY-NC-ND 2.0 UK** (non-commercial, no-derivatives) per MoneyHelper's
  own terms page; non-downloadable page content requires written consent
  for commercial reproduction. However, MoneyHelper also runs a
  **"Using MoneyHelper content on your website and digital channels"**
  partnership programme (`moneyhelper.org.uk/en/about-us/partnerships/overview`)
  that appears to offer free republishing of guidance/articles for
  qualifying uses. This is genuinely useful context for Job 2 below —
  see the recommendation there. Right now this is moot for the live
  product since MoneyHelper is unreachable (WAF) and its entries have
  just been excluded from the fetchable manifest (Job 2), but it's
  relevant to note that the **NC (non-commercial)** restriction on
  downloadable material would conflict with any future monetisation of
  a product surface that reproduces MoneyHelper content, even under the
  partnership programme — worth flagging now while the design decision
  is still reversible, per the standing "no monetisation without a
  compliance/lawyer pass" gate.

**Overall assessment:** GOV.UK/HMRC content is on solid, standard ground.
FCA (and any future MoneyHelper) HTML content sits in genuinely more
ambiguous territory that a lawyer should resolve — this is not a "stop the
project" finding since the current use is a build-only, undeployed MVP
with no revenue and effectively no reach, but it is a real pre-launch gate.

---

## 3. UK GDPR / Data Protection Act 2018

### What the MVP actually collects

Checked `web/src/` (no cookies, no `localStorage`/`sessionStorage`, no
analytics/tracking scripts — `index.html` and `main.tsx` load nothing
beyond the app bundle) and `server/pistis/api/app.py`. The only
persistence anywhere in the system is:

```python
record = {"ts": round(time.time(), 3), "question": question, "kind": kind}
```

appended to `logs/ask.jsonl` on every `/ask` call. No accounts, no
session IDs, no client-side storage, no IP address captured by the
application layer (uvicorn's own console access logging may include
client IP by default at the transport layer, but that's ephemeral console
output, not something the app persists).

### Does this engage UK GDPR?

Yes, potentially, once this is a live product with real users — and the
"no accounts, no cookies" framing in `api/app.py`'s own docstring
("nothing leaves the machine — the MVP collects nothing") slightly
understates this. **Personal data isn't only names/emails/identifiers —
UK GDPR's definition is broad, and a free-text financial question can
easily contain personal data by its content alone** ("I'm 67 with a
£40k SIPP and want to retire next year," "I've just been made redundant
and can't pay my mortgage"). Logging that verbatim, indefinitely (there's
no rotation, expiry, or purge logic in `refresh.py`/`app.py`), with a
timestamp, is processing of personal data — and in some cases could touch
special-category data if a question mentions health (e.g. in a
debt/vulnerability context).

**What would be needed before real deployment** (not needed for the
current build-only local MVP, but worth having ready):

1. A short, plain-language **privacy notice** (Art. 13) — what's logged,
   why, for how long, and that users shouldn't include identifying
   details if they'd rather not. Currently there is none anywhere in the
   product.
2. A defined **lawful basis** — most likely legitimate interests
   (product monitoring / classifier-miss review, see §1), which needs a
   documented legitimate-interests assessment, especially given the
   sensitivity of financial (and potentially health-adjacent) content in
   free-text questions.
3. A **retention/purge policy** for `logs/ask.jsonl` — currently
   append-only forever. Storage-limitation is one of the UK GDPR
   principles most likely to be an easy, concrete finding.
4. Since this is a UK-only, UK-government-content product with (per the
   design doc) no accounts and no cross-border processing currently
   planned, this looks tractable — a lawyer's job here is mostly
   confirming the above four items and checking there's no ICO
   registration/notification obligation triggered by the eventual scale
   of processing.

**Overall assessment:** low current real-world risk (nothing is deployed,
the log is gitignored and stays on one developer's machine), but this is
exactly the kind of gap that's invisible until the day of a real launch
and cheap to close now. Recommend closing items 1–3 as part of any
deploy-gate checklist, not left until the day of.

---

## 4. Consumer protection / accuracy — is the disclaimer adequate and prominent?

### What exists

- `DISCLAIMER` (`server/pistis/models.py`) is a field with a default
  value on **all three** response dataclasses (`AnswerCard`, `Abstention`,
  `RoutingEvent`) — meaning it is structurally impossible for an API
  response to omit it, not just a UI convention. `test_engine.py::test_no_response_ever_lacks_disclaimer`
  enforces this.
- The web UI (`web/src/App.tsx`) renders a persistent
  `.disclaimer-banner` above the ask form, present in the idle state and
  updated to the live server-supplied text once a response arrives —
  confirmed by `App.test.tsx`'s first test,
  `"renders the persistent guidance-not-advice banner before any question."`
- The banner is not hidden, collapsed, or in a footer — it sits directly
  under the masthead, before the input box, so a user sees it before
  asking anything.

### Gaps

- **Visual prominence is modest, not high.** From `styles.css`: the
  disclaimer banner is `font-size: 0.8rem` with `color: var(--ink-soft)`
  (a muted grey, not the primary ink colour), inside a thin bordered box.
  It is *present* and *unavoidable* (structurally, not just by page
  position), which is the important property, but it does not stand out
  visually — a user could plausibly skim past it without reading it. A
  lawyer/compliance reviewer (and separately, a designer) may want a
  stronger visual treatment (higher contrast, or a one-time
  interstitial/acknowledgement on first use) given the subject matter.
  This is a judgement call about "prominent enough," not a clear-cut
  failure — flagging for a second opinion rather than asserting it's
  wrong.
- **No accuracy/staleness signal beyond the raw date.** Every claim shows
  `fetched_at` and, when the source provides it, `last_updated` — good,
  honest practice. But there's no enforced staleness policy: nothing in
  `refresh.py` or the gate flags or downgrades a claim if its snapshot is,
  say, a year old and the source may have changed (tax bands and
  allowances change yearly). A user has to notice and interpret the date
  themselves. **Recommend:** define a staleness threshold (e.g. "if
  `fetched_at` is more than N days old, either block on refresh or
  visibly flag the claim as unverified-recently") before real launch —
  this is a straightforward accuracy/consumer-protection strengthening,
  not a legal blocker today.

**Overall assessment:** the disclaimer's *structural* guarantee (cannot be
omitted from any response) is strong and worth highlighting to the
lawyer as a genuine positive; its *visual* prominence is reasonable but
not maximal, and staleness handling is a real product gap worth closing
regardless of what a lawyer says, since it's core to the "provably
accurate" pitch.

---

## 5. Accessibility

### What exists (positive signal)

- `web/src/__tests__/App.test.tsx` runs `jest-axe` against the idle,
  loading, answer, and routing/abstain states — 7 tests, all passing.
- Confidence and source information is conveyed with **text labels, not
  colour alone** (`CONFIDENCE_LABEL`/`ORG_LABEL` maps in
  `AnswerLedger.tsx`) — satisfies WCAG 1.4.1 (Use of Color) properly,
  this is a common real-world miss that's been avoided here.
- `:focus-visible` states are defined with a 3px outline
  (`styles.css`), the loading state uses `role="status"` +
  `aria-live="polite"`, errors use `role="alert"`, and
  `@media (prefers-reduced-motion: reduce)` disables the skeleton/entry
  animations. `index.html` sets `lang="en-GB"`.

### What axe won't catch — flagged per the task brief

- **Automated tools like axe catch roughly a third to half of real
  WCAG issues** (this is a widely cited industry figure, not a Pistis-
  specific measurement) — a clean axe run is a good baseline signal, not
  a WCAG conformance claim. Before any real launch, recommend an actual
  manual keyboard-only pass and a real screen-reader pass (NVDA/JAWS/
  VoiceOver), which nothing in the current test suite does.
- **Plain-language reading level of cited content.** This is the item
  the task brief specifically asked about, and it's real: Pistis quotes
  GOV.UK/HMRC prose verbatim. GOV.UK content is generally written to a
  plain-English house style, which helps, but HMRC guidance in
  particular can still be technical (SDLT bands, MPAA taper rules,
  National Insurance categories) and axe has no concept of reading level
  at all — it's a WCAG-adjacent but not WCAG-tested concern (closest is
  WCAG 3.1.5 Reading Level, AAA, rarely tested automatically). Given the
  target audience explicitly includes people in financial difficulty
  (the `budgeting`/`scams_protection` domains), and that low
  financial/digital literacy correlates with vulnerability, this is
  worth a genuine plain-language/readability review — possibly informal
  (a readability-score pass, e.g. Flesch-Kincaid, on the corpus text) —
  before launch, separate from and in addition to WCAG conformance.
- **Reflow/zoom at 400%** (WCAG 1.4.10) and **text-spacing overrides**
  (1.4.12) are not exercised by the vitest/jsdom axe tests (jsdom doesn't
  really do layout/zoom). The CSS uses relative units and a mobile
  breakpoint, which is a good sign, but this needs an actual browser
  check, not just axe.
- **Cognitive load / refusal-card styling**: the rotated "stamp" visual
  treatment on the abstain/routing card (`transform: rotate(-1.5deg)`) is
  a nice brand touch but worth a manual check that it doesn't reduce
  legibility for users with low vision or in Windows High Contrast Mode.

**Overall assessment:** genuinely above-average accessibility hygiene for
an MVP (the axe-in-CI habit plus text-not-colour-alone discipline are the
two things most projects get wrong, and this one didn't). The gaps above
are the standard "automated testing is necessary but not sufficient"
gaps, plus one domain-specific one (reading level) worth taking seriously
given the intended audience.

---

## Summary table

| # | Area | Finding | Severity | Status |
|---|---|---|---|---|
| 1 | FCA perimeter | Rule-based classifier has an inherent, unbounded false-negative tail; no defined red-team-coverage bar or ongoing misses-review process | Medium — architecture is sound, coverage is a judgement call | Needs lawyer + product decision on acceptable coverage/monitoring |
| 2 | FCA perimeter | Verbatim second-person source text sits in the answer ledger; visual framing as "quotation" should be lawyer-checked | Low–Medium | Needs lawyer read |
| 3 | FCA perimeter | Design doc describes an LLM-composer path (`providers/`) that does not exist in code (empty dir) | Informational (doc/code mismatch, not a risk) | Recommend correcting docs |
| 4 | Licensing | Manifest silently mislabelled FCA (and would have mislabelled MoneyHelper) content as OGL v3.0 | Medium (data-hygiene bug; not yet user-facing) | **Fixed this session** — `manifest.py` `_default_licence()` + regression tests |
| 5 | Licensing | OGL acknowledgement text exists only in README, not on the live product surface | Low–Medium | Open — recommend a footer credit line before launch |
| 6 | Licensing | Whether verbatim-sentence extraction/republication of FCA content is within FCA's permitted "incidental extract" use or needs written permission | **Highest** — genuine legal judgement call | **Needs lawyer** |
| 7 | Licensing | MoneyHelper's NC (non-commercial) licence terms would conflict with future monetisation of any product surface reproducing its content | Low now (no MoneyHelper content live; informational for future) | Noted for the record |
| 8 | GDPR | Free-text question log (`logs/ask.jsonl`) can capture personal (possibly special-category) data by content; no privacy notice, no defined retention/purge | Medium for any real deployment; low today (local, gitignored, undeployed) | Open — add before any real launch |
| 9 | Consumer protection | Disclaimer is structurally unavoidable (strong) but visually modest (small, muted grey text) | Low–Medium | Open — design/lawyer second opinion |
| 10 | Consumer protection | No staleness policy — old snapshots aren't flagged differently from fresh ones beyond the raw date | Medium (accuracy/product gap, not strictly legal) | Open — recommend before launch |
| 11 | Accessibility | Axe-clean is a floor, not proof of WCAG conformance; no manual keyboard/screen-reader pass done yet | Medium | Open — recommend before any conformance claim |
| 12 | Accessibility | No plain-language/reading-level review of cited government prose, relevant given the vulnerable-user domains (debt, scams) | Medium | Open — recommend an informal readability pass |

---

## What I changed during this review

To avoid shipping a known-wrong labelling bug while writing this document,
I fixed finding #4 in the same session (small, low-risk, test-covered):
`server/pistis/corpus/manifest.py` now computes a licence label based on
`kind`/`org` instead of defaulting everything to `"OGL v3.0"`, with new
tests in `server/tests/test_manifest.py`. I did **not** attempt to resolve
findings #6, #8, #9, #10, #11, or #12 — those need either a lawyer's
judgement or a product/design decision, not a unilateral code change.
