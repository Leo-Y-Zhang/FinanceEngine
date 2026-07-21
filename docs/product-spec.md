# Pistis — Product Spec

*A trust-first UK personal-finance AI answer engine, defined by a default-deny honesty gate: it answers only when it can ground the claim in a reliable, cited source — otherwise it says so and defers.*

> Status: draft spec, built solely from the accompanying market and regulatory research. Nothing here is legal advice; the research explicitly recommends a regulatory lawyer / compliance sign-off before launch and before any monetisation touching specific products.

---

## 1. Problem & thesis

UK consumers have already adopted AI for money tasks at scale: Lloyds-cited figures put ~28.8m UK adults (~56% of adults) using AI for money, with ChatGPT the most popular tool, and OpenAI has launched a dedicated personal-finance experience. But adoption runs ahead of trust — **80% of UK AI-money users worry about inaccurate or outdated information** and **83% worry about privacy** (Lloyds/Fintech Times).

The trust gap is structural, not incidental:

- **General LLMs cite fluently but unreliably.** Perplexity cites live web sources yet shows a citation-mismatch failure rate reported at ~37% (CJR) — real URLs attached to claims the source never actually made. They are over-confident and rarely abstain, and they are not grounded in UK-authoritative sources.
- **The one credible grounded incumbent is single-source.** Ask MSE grounds only on MoneySavingExpert's own guides. It sensibly refuses product recommendations and disclaims fallibility, but offers no robust per-claim citations in-answer, no abstain-when-uncertain gate, and no HMRC/GOV.UK/FCA/MoneyHelper grounding.
- **The authoritative source has no AI layer.** MoneyHelper (statutory, gov-backed, 700+ guides) is trusted but static, with no conversational synthesis.

**Thesis:** the wedge is *verifiable trust*, not fluency. The defensible product is the one that (a) grounds every substantive claim in named, dated, UK-authoritative sources with a citation attached to *each* claim, and (b) **refuses to answer when it cannot** — turning refusal into a feature that directly targets the single biggest stated barrier (fear of wrong/stale answers). No incumbent occupies this position.

---

## 2. Target user & scope

**User:** UK adults who already use, or would use, an AI assistant for money questions but distrust its accuracy — people who want to *understand their options* and check the facts, not be sold a product.

**Domain scope — UK personal finance guidance:**
- Savings & ISAs (incl. LISA)
- Pensions (workplace/personal, state pension, drawdown/annuity concepts)
- Mortgages
- Tax (allowances, thresholds, HMRC rules)
- Budgeting

**In scope:** explaining how things work, comparing *types* of vehicle/option, objective calculations, factual limits/rules, and signposting to authoritative sources.

**Explicitly out of scope (see §4):** telling an individual which specific product/fund/provider/action is right for them; collecting personal circumstances and outputting a single "right for you" answer; any product promotion or "apply here" journey.

*Uncertain / undecided in research:* privacy is flagged as a top user concern (83%) but the research does not specify Pistis's data-handling model, and it does not resolve whether any personalisation over a user's own data would ever be offered. Treat as an open product decision (see §7).

---

## 3. Competitive landscape & the gap

| Name | What it is | Sourcing / trust approach | Weakness for a citation-first, honesty-gated engine |
|---|---|---|---|
| **Ask MSE** (MoneySavingExpert) | Free ChatGPT-API chatbot in the MSE app, grounded on MSE's own guides/blogs (re-indexed weekly) | Answers only from MSE content; refuses product recommendations ("how do I" not "what's best"); disclaims fallibility, points to full human guide | Single-source (MSE only); no robust per-claim in-answer citations/links; no explicit abstain-when-uncertain gate; no HMRC/GOV.UK/FCA/MoneyHelper grounding |
| **MoneyHelper** (Money & Pensions Service, gov-backed) | Free, impartial official guidance — 700+ guides, calculators, helplines, webchat/WhatsApp; includes Pension Wise | Highly authoritative and trusted; human specialists; but static content, no AI answer layer | Not an AI engine; slow to navigate. Better *cited by* Pistis than treated as a rival — but is also the obvious body to build an AI layer itself |
| **Cleo** | Conversational AI budgeting assistant; Plaid read-only bank link; "roast/hype" persona | Personalises over the user's own transaction data, not external knowledge; no external citations | Not a knowledge/answer engine; monetises via cash advances & subscription (incentive conflict); no sourcing on savings/ISA/pension/tax facts |
| **Plum** | Automated saving/investing app; AI agent (Google Gemini) on income/goals; Cash ISA & LISA | AI directs users toward products/actions | Product/upsell-driven, not neutral cited guidance; narrow to its own accounts |
| **Nutmeg (J.P. Morgan) / Moneyfarm / Wealthify** (robo-advisers) | Automated ETF portfolios from a risk questionnaire; FCA-regulated & FSCS-protected; Nutmeg pilots full regulated advice | Regulated advice/guidance with clear disclosures; trust via authorisation | Investment-only; tied to their own products; not a broad Q&A engine for tax/mortgages/budgeting |
| **General LLMs — ChatGPT / Perplexity / Gemini** | The de-facto incumbent; OpenAI launched a dedicated PF experience | Perplexity cites live web; ChatGPT/Gemini partly grounded | Citation mismatch/hallucination (Perplexity ~37% citation-accuracy failure, CJR); not UK-authoritative-grounded; over-confident, rarely abstains; users fear inaccuracy (80%) and privacy loss (83%) |

**The gap (three unoccupied positions):**
1. **No neutral, multi-authoritative, per-claim-cited UK PF engine.** Nobody synthesises GOV.UK/HMRC, FCA, MoneyHelper/Pension Wise and reputable consumer bodies with a verifiable citation attached to *each* claim across all six domains.
2. **No "default-deny" honesty gate.** Every incumbent always answers, confidently. Abstaining-and-deferring when a claim can't be grounded is genuinely unoccupied — and targets the top user fear.
3. **Freshness + regulatory-safe framing between the two poles.** Gov guidance is authoritative but static and un-AI'd; LLMs are fluent but stale/ungrounded on fast-moving UK specifics (rate changes, HMRC allowances, ISA/LISA limits, benefit thresholds). A continuously-refreshed, guidance-not-advice engine with transparent dated sources fills the middle — especially as the FCA's "targeted support" regime takes effect 6 April 2026.

---

## 4. Regulatory guardrail — guidance, never advice

Pistis stays firmly on the **guidance** side of the advice/guidance boundary. The bright line is the **personal recommendation**: regulated advice is a personal recommendation about a specific investment; guidance is generic, non-personalised material. Crossing it as an unauthorised person is a criminal offence under FSMA.

**What makes a communication a regulated personal recommendation (all must hold — Art 53 RAO / MiFID; PERG 8.30B):** it is made to a person as an investor; it relates to a *specific/particular* investment (not just a product type); it is presented as suitable for them *or* based on their personal circumstances; and it is not issued exclusively to the public (i.e. individualised).

**Two traps to design against:**
- **Implicit suitability counts.** You needn't say "suitable." Framing like *"people like you tend to choose X"*, or narrowing to one product after collecting circumstances, is a personal recommendation. Substance over form.
- **Filtering vs recommending.** Filtering on a *single factual factor* (e.g. "ISAs with no platform fee") is generally not advice; combining *multiple personal-circumstance inputs* into a result presented as meeting the user's specific requirements tips into a personal recommendation.

**"Targeted support" is a separate, gated middle tier** (PS25/22): it lets firms suggest a course of action to a *segment* of similar consumers, but requires a specific FCA permission (final rules 26 Feb 2026; applications open 2 Mar 2026; live 6 Apr 2026). Pistis cannot lawfully do targeted-support-style suggestions without authorisation. Until/unless authorised, stay on pure guidance.

### Concrete design rules (from the regulatory research)

**A. MAY do (guidance side):**
- Purely factual information: ISA vs pension tax treatment, contribution/withdrawal limits, access rules, how compounding/drawdown works, objective calculations.
- Generic explanations: compare *types* of vehicle (ISA vs unit trust; single- vs joint-life annuity; equities vs bonds) without recommending one *for the user*.
- Non-directive prompts: flag scam risks, explain the *consequences* of an action — without directing the specific action.
- Signpost to authoritative regulated/official sources.

**B. NEVER (hard list):**
- Never name a specific product/fund/provider/share and say or imply the user should buy/sell/hold it.
- Never collect personal circumstances and output a single "right for you" answer.
- Never use "you should," "we recommend," "best option for you," "based on your situation, do X."
- Never present model/example outputs as personalised suitability.

**C. Source-citation policy (build in):** every substantive answer cites and defers to authoritative sources — **GOV.UK/HMRC** (tax, allowances, state pension, benefits), **MoneyHelper** (pensions/investment/debt guidance and the "get proper guidance" signpost), **FCA** (scam warnings, the FCA Register, consumer explainers). Prefer primary/official over secondary; show URL and date so users can verify. Aligns with Consumer Duty "support" and "consumer understanding" outcomes.

**D. Disclaimers & routing (necessary, not sufficient):**
- Persistent, prominent disclaimer: *"Pistis provides information and guidance, not regulated financial advice or a personal recommendation. It does not consider your individual circumstances. For advice tailored to you, speak to an FCA-authorised adviser."*
- Do **not** rely on the disclaimer to cure advice-like content — the FCA looks at substance; a disclaimer rarely prevents a personal recommendation if the messaging implies suitability.
- **Defer-to-adviser routing:** any "what should *I* do / which should *I* pick" is a routing event — decline to recommend and route to (i) MoneyHelper guidance and (ii) an FCA-authorised adviser (FCA Register + MoneyHelper "choosing a financial adviser"). Explain the *value* of regulated advice: it carries protections (FOS, FSCS, adviser accountability) guidance cannot.
- Make clear users bear responsibility for decisions made on guidance.

**E. Financial-promotions guardrails (separate s21 FSMA regime):** keep content product-neutral; no inducements to engage in a specific investment activity. Affiliate links, "apply here" journeys, or promoting specific products likely become financial promotions requiring an authorised communicator/approver — design to avoid this unless/until authorised. Follow FG24/1 principles if outputs are shareable.

**F. AI-specific governance:** clear model accountability/ownership; testing/monitoring for harmful or hallucinated outputs; guardrails/classifiers that block "personal recommendation"-shaped answers; human oversight and logging; treat accuracy of financial info as a Consumer Duty "avoid foreseeable harm / consumer understanding" obligation.

---

## 5. The differentiator — the honesty / citation gate

Pistis's defining mechanism is a **default-deny honesty gate**: the system's default posture is *not to answer*, and it earns the right to answer only when it can attach grounded, reliable citations to the claims it is about to make.

**How it decides to answer vs defer (conceptual):**
- **Ground-first, not generate-first.** For a given question, Pistis retrieves from a curated corpus of UK-authoritative sources (GOV.UK/HMRC, FCA, MoneyHelper/Pension Wise, reputable consumer bodies) *before* composing an answer. The answer is assembled from what the sources support, not the model's parametric memory.
- **Per-claim grounding check.** Each substantive claim in a candidate answer must map to a specific supporting source passage. Claims that cannot be tied to a source are not emitted. This directly targets the citation-mismatch failure that afflicts general LLMs (a real URL attached to a claim the source never made).
- **Abstain when unground-able.** If the corpus does not cover the question, or coverage is stale/ambiguous, Pistis states that plainly and defers — to MoneyHelper and/or an FCA-authorised adviser — rather than guessing. Refusal is the feature, not a failure mode.
- **Advice-boundary classifier as a second gate.** Independently of grounding, any answer shaped as a personal recommendation (specific product + implied suitability, or a personalised "right for you" narrowing) is blocked and converted into a routing event (per §4B/§4D). An answer must clear *both* gates — grounded *and* guidance-only — to be shown.

**How it cites:**
- Citations are **per-claim**, **named**, and **dated** — showing the source and the date so users can verify freshness (critical for fast-moving UK specifics: rate changes, HMRC allowances, ISA/LISA limits, benefit thresholds).
- Primary/official sources are preferred over secondary.
- The corpus is **continuously refreshed** so answers reflect current thresholds and rules, filling the middle ground between static gov guidance and stale ungrounded LLMs.

**The calibration principle:** the gate must be *trustworthy without being useless*. Too eager to answer, and Pistis inherits the hallucination problem that destroys its only USP; too eager to abstain, and it loses to a ChatGPT that always answers. Tuning this threshold is the product's core execution challenge (see §7), and the target is a defensible, honest calibration — not maximal answer coverage.

---

## 6. MVP scope — what to build first

Build the smallest thing that proves the two unoccupied positions (per-claim grounded citation + default-deny abstention) in the highest-trust way.

**Corpus (grounding foundation):**
- Curate and index a UK-authoritative source set: GOV.UK/HMRC, FCA (incl. Register + consumer explainers + scam warnings), MoneyHelper/Pension Wise, and reputable consumer bodies.
- Continuous refresh so dated figures (allowances, ISA/LISA limits, thresholds) stay current.
- *Licensing caution (from research):* some of the best UK content (e.g. MSE, Which?) is proprietary/licensed — the MVP corpus should lean on the official/open sources above; grounding on proprietary content may require licensing, not scraping.

**Answer engine:**
- Retrieval-grounded answers with **per-claim, dated citations** across the six domains (savings/ISAs, pensions, mortgages, tax, budgeting).
- **Default-deny gate** that abstains and defers when a claim can't be grounded.
- **Advice-boundary classifier** blocking personal-recommendation-shaped outputs and routing "which should I pick / what should I do" to MoneyHelper + an FCA-authorised adviser.

**Framing & safety:**
- Persistent guidance-not-advice disclaimer; product-neutral (no affiliate links, no "apply here" — avoids the s21 financial-promotion perimeter).
- Logging and monitoring of outputs for hallucinated/harmful/advice-shaped responses; red-team against "what should I invest in?" prompts.

**Deliberately NOT in the MVP:**
- No product recommendations, no personalised suitability, no targeted-support-style suggestions (requires FCA permission, live 6 Apr 2026 at earliest).
- No monetisation touching specific products.
- No personalisation over a user's own bank data (unresolved in research — see §7).

---

## 7. Key risks & open questions

**Risks (from the research):**
1. **Inadvertent personal recommendation (#1 risk).** LLMs naturally personalise ("based on what you've told me, I'd go with…"), which is regulated advice by an unauthorised person — a criminal offence. Mitigation: output guardrails that detect/block product-specific/personalised suitability; red-teaming.
2. **Financial-promotion breach (s21 FSMA)** — an independent offence. Affiliate links, "buy now" nudges, or promoting specific products can trigger it. Mitigation: stay product-neutral; legal review of any monetisation touching specific products.
3. **Accuracy liability & the honesty-gate paradox.** UK PF facts change constantly; one wrong cited answer on tax/pensions causes real harm and destroys the entire trust USP — yet an engine that abstains too often loses to always-answering rivals. Calibrating default-deny to be trustworthy without being useless is the core execution risk.
4. **Entrenched incumbents own trust, distribution, and source content.** MSE (brand + proprietary content), MoneyHelper (gov backing), OpenAI/Perplexity (default distribution) are hard to displace; the best content may need licensing.
5. **Consumer Duty exposure** if Pistis becomes/partners with an authorised firm — inaccurate info = foreseeable harm. (A purely unauthorised info service isn't directly under the Duty, but partnerships/promotions can pull it in.)
6. **A moving regulatory perimeter.** Targeted support live 6 Apr 2026; CP26/10 (simplifying pensions/investment advice) in consultation; the Mills Review recommends the FCA adapt the perimeter for AI. Treat compliance as a living process.

**Open questions / uncertainties the research left unresolved (flagged honestly):**
- **Advice classification is fact-specific.** Whether a *given* Pistis feature is "guidance," "targeted support," or a "personal recommendation" turns on exact wording/UX and needs a compliance lawyer against PERG 8 Annex 1 worked examples — which the regulatory research could not fully extract (the page renders via JS; analysis relied on PERG 8.30B + FCA "Helping firms…" guidance instead).
- **Consumer Duty applicability** depends on Pistis's authorisation/partnership structure, which is not specified — must be checked.
- **FG24/1 social-media detail** is summarised only at a high level here.
- **Privacy / personalisation model is undefined.** 83% of UK AI-money users worry about privacy, but the research does not specify Pistis's data handling, nor resolve whether any personalisation over a user's own data is in scope. This is an open product decision with direct trust implications.
- **OpenAI's PF experience** positioning is drawn from the announcement URL surfaced in search, not verified page content (the page returned HTTP 403). Treat competitor detail there as indicative, not confirmed.
- **Content licensing** for proprietary UK sources (MSE, Which?) is a commercial dependency the research flags but does not price or resolve.
- **Whether MoneyHelper builds its own AI layer** is named as an obvious threat (the authoritative body best placed to do so), but its intentions are unknown.

> **Bottom line:** ship Pistis as an information-and-guidance engine — generic, factual, product-neutral, per-claim source-cited, with hard guardrails against personalised/product-specific recommendations and against inducements to invest. Treat "which should I pick / what should I do" as a routing event, never an answer. Keep monitoring the moving perimeter and obtain compliance/legal sign-off before launch and before any monetisation touching specific products.

---

*Compiled 2026-07-19 from a multi-agent web-research pass over public sources (FCA, GOV.UK, MoneyHelper, provider sites). Figures and citations are research-derived — verify before external use; obtain a regulated compliance sign-off before any launch touching specific financial products.*
