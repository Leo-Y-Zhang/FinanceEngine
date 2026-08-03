# Design Brief — Finance Answer Engine

**Date:** 2026-08-03 (retrospective, derived from `web/src/styles.css` and the
components) · **PRD:** [PRD.md](PRD.md) · **App Flow:** [APP_FLOW.md](APP_FLOW.md)

## Intent

It should feel like **a document, not a chat** — something with a fetch date on
it that you could print and hand to someone. Calm, dense, slightly bureaucratic
in the way an official form is bureaucratic: the trustworthiness comes from the
provenance being on the page, not from the interface reassuring you.

**What it must never feel like:** a conversation with a confident assistant. No
avatar, no typing indicator, no first-person voice, no streaming text arriving
word by word. Every one of those cues is borrowed authority — they make an
ungrounded answer feel exactly like a grounded one, which is the specific failure
this product exists to counter. A refusal must not feel like an apology either;
it is a result, and it is laid out with the same weight as an answer.

## Who is looking at it

Someone mid-task with a specific money question — often on a phone, often
mildly anxious, often about to make a decision with real money in it. They are
not exploring; they want a number and they want to know whether to trust it.
The design assumes they will read the claim, glance at the source badge and the
date, and leave. Everything else on the page is there for the moment they *do*
look closer.

## Precedents

- **GOV.UK** — the register line and the date stamp. GOV.UK puts "Last updated"
  on the page as a first-class element rather than as metadata in a footer, and
  that single habit is the whole idea behind the receipt line under every claim.
- **A financial statement / ledger** — one row per item, a left rule, and a
  running total. Borrowed literally: the claim ledger's `border-top: 2px solid`
  header rule, the per-row bottom rule, and the "N of N statements grounded"
  summary sitting where a total would.
- **Legal-document typography** — a monospace register line and small-caps-ish
  tracked labels signalling *this is a record*, while the body stays in a
  comfortable sans. The mixture is the point: the prose is readable, the
  metadata reads as metadata.

## Anti-patterns for this project

Specific enough to enforce in review:

- **No chat bubbles, no message list, no avatar, no "typing…" affordance.**
- **No streaming reveal.** Text appearing progressively implies thought in
  progress. This engine does lexical retrieval in milliseconds and has nothing
  to think about.
- **No confidence expressed as a percentage or a bar.** Confidence is a named
  tier with a defined meaning (`Established` / `Depends on your situation` /
  `Uncertain`); a number invites false precision the engine cannot support.
- **No green tick as the sole grounding signal.** Grounding is a chip with the
  words "Grounded in source" in it.
- **No dark pattern in the refusal.** No "try rephrasing" nudge that implies the
  user asked badly, and no greyed-out teaser of an answer. The refusal states
  what it could not verify and links out.
- **No dark theme.** `<meta name="color-scheme" content="light">` is set
  deliberately: the whole visual argument is *paper*, and there is no
  second-surface design. This is a real limitation, chosen rather than
  overlooked.

## Type

One sans for prose, one mono for anything that is a record. No third family.

| Role | Family | Size | Notes |
|---|---|---|---|
| Body / claims | `system-ui, "Segoe UI", Arial, sans-serif` | 1rem, line-height 1.55 | Line length capped by a 46rem shell |
| Wordmark | mono, 700 | `clamp(1rem, 4.6vw, 1.6rem)`, tracking 0.18em, uppercase | Tracking is deliberately modest: the name is three words and 21 characters, and the 0.35em a one-word mark could carry ran wider than the masthead |
| Register line, result kind | mono | 0.72rem, tracking 0.04–0.14em, uppercase | The "this is a record" signal |
| Receipt (citation line) | mono | 0.74rem | Deliberately quiet — present, not competing with the claim |
| Chips | mono, uppercase | 0.68rem, tracking 0.08em | |

## Colour

Roles first, values second. Every value is in `:root` in `styles.css`; nothing
is hard-coded at a call site.

| Role | Token | Value |
|---|---|---|
| Surface | `--paper` | `#fcfbf7` (warm off-white — paper, not screen) |
| Text | `--ink` | `#1a1a18` |
| Muted text | `--ink-soft` | `#4c4c47` |
| Hairline | `--rule` | `#d8d5cc` |
| Grounded / established | `--verified` on `--verified-tint` | `#0b6b5d` on `#e7f2ef` |
| Conditional | `--depends` on `--depends-tint` | `#7a4d00` on `#f6ecdb` |
| Uncertain | `--uncertain` on `--uncertain-tint` | `#5c5c56` on `#ebeae5` |
| Refusal | `--refusal` on `--refusal-tint` | `#a33b2e` on `#f7e9e6` |

**Measured contrast** (computed against the real values, not assumed):

| Pair | Ratio | Verdict |
|---|---|---|
| ink on paper | 16.83 | pass |
| ink-soft on paper | 8.34 | pass |
| verified on its tint | 5.60 | pass |
| depends on its tint | 6.21 | pass |
| uncertain on its tint | 5.59 | pass |
| refusal on its tint | 5.51 | pass |
| verified on paper (focus ring, links) | 6.19 | pass — well over the 3:1 UI-boundary floor |
| rule on paper | 1.42 | **decorative only** — hairlines carry no information that is not also carried by layout or text |

Note that the refusal colour is a muted brick rather than a warning red. A
refusal is not an error, and it should not be coloured like one.

## Spacing and layout

A single centred column, `max-width: 46rem`, `padding: 0 1.25rem 5rem`. Stack,
not grid — every element is full-width and vertical order is reading order,
which is also the screen-reader order. Spacing runs on rough 0.3/0.45/0.6/0.9/
1.1/1.6/2.5rem steps. The masthead's 6px top rule is the heaviest element on the
page and does the same job a masthead rule does on a newspaper: it says the page
has started.

## Components touched

Four, all existing, none near-duplicates:

- `App` — shell, masthead, disclaimer banner, form, live region, footer.
- `AnswerLedger` + its internal `Receipt` — the signature element.
- `RefusalCard` + its internal `RefusalDiagnostics` — serves both abstentions and
  routing events, differing only in the stamp text and whether a report exists.
  One component, because they are the same shape of thing.
- `PrivacyNotice` — reuses `.shell`, `.masthead`, `.wordmark`, `.question-echo`.

## States

- **Hover** — links underline; nothing else moves.
- **Focus** — `outline: 3px solid var(--verified); outline-offset: 2px` on
  inputs, the button and every link, via `:focus-visible`. There is no
  `outline: none` anywhere in the stylesheet.
- **Active** — no separate treatment; the button is a hard-edged block already.
- **Disabled** — the submit button uses `aria-disabled` with `opacity: 0.45`,
  never the `disabled` attribute, so it stays focusable and announceable. The
  real guard lives in the submit handler.
- **Loading** — three grey skeleton rows, animated, inside the live region.
- **Error** — a single `role="alert"` line, no card, no illustration.

## Accessibility floor

- Contrast: measured above; body text and every chip clear 4.5:1, the focus ring
  clears 3:1.
- Full keyboard operation with visible focus and reading-order tab order.
- Colour is never the only signal — every state is also a word.
- `@media (prefers-reduced-motion: reduce)` disables both the skeleton pulse and
  the result-enter animation.
- Single-column layout works at 320px; the form stacks below 30rem.
- Gated by `jest-axe` assertions in the test suite rather than by inspection.

**Two honest gaps, named rather than smoothed over:**

1. **Touch targets.** The citation links in the receipt line sit at 0.74rem
   inline text — comfortably under the 44px target guidance. They are secondary
   affordances (the claim itself is the content), but that is a mitigation, not
   a pass.
2. **Small type.** The receipt at 0.74rem and the chips at 0.68rem are small in
   absolute terms. They survive 200% zoom because the layout is a single stack
   with no fixed heights, but the resting size is at the edge of comfortable and
   would be the first thing to revisit for a real audience.

## Done means

- [x] Matches intent — reads as a record, not a conversation
- [x] Every state designed, including empty (the form *is* the empty state) and
      error
- [x] Contrast checked against the real hex values, and the one failing pair
      identified as decorative
- [x] Keyboard path walked; focus visible on every interactive element
- [x] Works at 320px and at 200% zoom
- [ ] Touch targets at 44px — **not met**, see above
