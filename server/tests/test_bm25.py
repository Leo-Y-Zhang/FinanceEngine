from pistis.index.bm25 import Bm25Index, tokenize


def test_tokenize_drops_stopwords_keeps_figures():
    assert tokenize("What is the ISA allowance?") == ["isa", "allowance"]
    assert "£20" in tokenize("save up to £20,000 this year")


def test_tokenize_expands_uk_finance_synonyms():
    tokens = tokenize("How does a LISA work?")
    assert "lifetime" in tokens and "isa" in tokens
    # The abbreviation is REPLACED, not kept: a raw 'lisa' token is
    # out-of-vocabulary for official sources and would poison IDF-weighted
    # coverage into wrongly abstaining (2026-07-21 review finding).
    assert "lisa" not in tokens
    tokens = tokenize("When do I pay CGT?")
    # plural fold normalises "gains" -> "gain" on both query and corpus side
    assert "capital" in tokens and "gain" in tokens


def test_abbreviation_query_coverage_not_poisoned(index):
    q = "How does a LISA bonus work?"
    assert index.coverage(q, index.search(q)) >= 0.6


def test_isa_query_ranks_isa_passage_first(index):
    hits = index.search("What is the annual ISA allowance?")
    assert hits, "expected hits for an in-corpus query"
    assert hits[0].passage.doc_id in {"isa-overview", "lifetime-isa"}


def test_state_pension_query_ranks_pension_doc_first(index):
    hits = index.search("How much is the full new State Pension per week?")
    assert hits[0].passage.doc_id == "new-state-pension"


def test_synonym_query_finds_lifetime_isa(index):
    hits = index.search("How does a LISA bonus work?")
    assert hits[0].passage.doc_id == "lifetime-isa"


def test_search_is_deterministic(index):
    a = index.search("workplace pension employer contribution")
    b = index.search("workplace pension employer contribution")
    assert [(h.passage.id, h.score) for h in a] == [(h.passage.id, h.score) for h in b]


def test_empty_query_returns_nothing(index):
    assert index.search("") == []
    assert index.search("the and of") == []


def test_coverage_high_for_in_corpus_question(index):
    q = "How much is the new State Pension?"
    assert index.coverage(q, index.search(q)) >= 0.5


def test_coverage_zero_for_out_of_domain_question(index):
    q = "Who won the football world cup final?"
    assert index.coverage(q, index.search(q)) < 0.3


def test_uncovered_terms_names_out_of_domain_words(index):
    q = "How do I renew my passport?"
    uncovered = index.uncovered_terms(q, index.search(q))
    assert "passport" in uncovered
    assert "renew" in uncovered


def test_uncovered_terms_empty_for_in_corpus_question(index):
    q = "What is the annual ISA allowance?"
    assert index.uncovered_terms(q, index.search(q)) == []


def test_uncovered_terms_flag_out_of_domain_but_spare_in_corpus_words(index):
    # Independent oracle (not a re-derivation of the impl's own disjoint filter):
    # a query mixing out-of-domain concepts with genuine in-corpus finance terms
    # must flag the former and NOT the latter.
    q = "How do I install solar panels while keeping my ISA allowance?"
    uncovered = set(index.uncovered_terms(q, index.search(q)))
    assert {"solar", "panels", "install"} <= uncovered
    assert "isa" not in uncovered
    assert "allowance" not in uncovered


def test_uncovered_terms_is_deterministic(index):
    q = "Who won the football world cup final?"
    a = index.uncovered_terms(q, index.search(q))
    b = index.uncovered_terms(q, index.search(q))
    assert a == b and a


def test_function_words_never_become_uncovered_concepts(index):
    """A query word missing from STOPWORDS and absent from the corpus is scored
    at MAXIMUM idf and is then named to the user as a concept "no trusted source
    covers". Measured on the live 46-doc corpus, idf("am") was 6.966 — identical
    to idf("vat"), a concept genuinely missing — so the word "am" dragged coverage
    down as hard as a real gap AND explained the resulting refusal. Two real
    questions were refused for it."""
    for word in ("am", "were", "been", "being", "did", "done", "he", "she", "they", "them"):
        assert tokenize(f"What is an ISA and {word} I eligible?").count(word) == 0, word

    # End to end: the function word must not surface as a named gap.
    hits = index.search("What is an ISA and am I eligible")
    assert "am" not in index.uncovered_terms("What is an ISA and am I eligible", hits)


def test_a_genuinely_missing_concept_still_surfaces(index):
    """The positive control for the test above — the stoplist must not be so
    broad that real gaps stop being named. Without this, silencing every term
    would pass."""
    query = "Do I need to register for cryptocurrency"
    hits = index.search(query)
    assert "cryptocurrency" in index.uncovered_terms(query, hits)


# ── the relevance signal: is this document ABOUT the question? ────────────────
#
# A third signal, independent of retrieval strength and coverage. Both of those
# ask whether the question's WORDS are present; the faithfulness verifier asks
# whether a claim is supported by the passage it came from. None of them asks
# whether the source addresses the SUBJECT, which is how a grounded, correctly
# cited claim about inheritance-tax taper relief came back for "how is
# cryptocurrency taxed?".


def _doc(doc_id, title, *texts):
    from pistis.models import Passage, SourceOrg

    return [
        Passage(
            id=f"{doc_id}#{i}",
            doc_id=doc_id,
            text=text,
            doc_title=title,
            org=SourceOrg.GOVUK,
            url="https://www.gov.uk/x",
            fetched_at="2026-07-27",
        )
        for i, text in enumerate(texts)
    ]


def test_a_passing_mention_is_not_aboutness():
    # The exact shape of the crypto failure: one incidental mention inside a
    # document about something else entirely.
    passages = _doc(
        "iht", "Inheritance Tax",
        "Gifts given 3 to 7 years before death are taxed on a sliding scale.",
        "Chargeable assets include property, shares and cryptocurrency.",
        "The threshold is set each tax year.",
        "Taper relief reduces the tax due.",
    )
    index = Bm25Index(passages)
    assert not index.is_about("iht", "cryptocurrency")
    # positive control: the subject the document actually covers
    assert index.is_about("iht", "tax")


def test_a_title_makes_a_document_about_its_subject():
    index = Bm25Index(_doc("ctf", "Child Trust Fund", "Some text.", "More text."))
    assert index.is_about("ctf", "child")


def test_aboutness_is_relative_to_document_length():
    """In a two-passage document, one passage IS half the subject matter.

    A fixed passage count silently became unsatisfiable for short sources —
    live documents run to a median of 32 passages, but some hold only two.
    """
    short = Bm25Index(_doc("s", "A title", "Annuity rates vary by provider.", "Other text."))
    assert short.is_about("s", "annuity")
    long_doc = Bm25Index(
        _doc("l", "A title", "Annuity rates vary.", *["Unrelated text."] * 9)
    )
    assert not long_doc.is_about("l", "annuity")


def test_topic_share_is_not_hijacked_by_one_rare_junk_term():
    """"each" outranks "isa" on IDF in the live corpus — rarity alone is no guide.

    Any rule keyed on a question's single rarest token would put the whole
    decision on a function word. Weighting by share of total meaning does not.
    """
    passages = _doc(
        "isa", "Individual Savings Accounts ISA",
        "You can pay in up to the allowance each year.",
        "There are four types of ISA account.",
    ) + _doc("x", "Something else", "Filler text here.", "More filler text.")
    index = Bm25Index(passages)
    assert index.topic_share("How much can I pay into an ISA each year?", "isa") >= 0.5
    assert index.topic_share("How much can I pay into an ISA each year?", "x") < 0.5


def test_topic_share_of_an_unknown_document_is_zero():
    index = Bm25Index(_doc("d", "Title", "Text one.", "Text two."))
    assert index.topic_share("anything at all", "no-such-doc") == 0.0
    # An empty question has no meaning to be about, and must not divide by zero.
    assert index.topic_share("", "d") == 0.0


def test_reflexive_pronouns_are_stopwords():
    """A pronoun must not be able to veto a correct source.

    "How do I protect myself from financial scams?" was REFUSED against the FCA
    scam-protection page — the strongest hit in the corpus — because coverage
    came to 0.5962 against a 0.6 threshold, and the single uncovered term was
    "myself". The refusal card then told the user that no trusted source covers
    "myself". The stoplist already held every other pronoun form; the reflexives
    were simply missed. Same defect class as the "am" bug in session 8.
    """
    assert tokenize("How do I protect myself from financial scams?") == [
        "protect", "financial", "scam",
    ]
    for word in ("yourself", "himself", "herself", "itself", "ourselves", "themselves"):
        assert tokenize(f"protect {word} from scams") == ["protect", "scam"]
    # Positive control: this is a narrow addition, not a broadening. Content
    # words that merely look small must survive — session 8 measured that a
    # wider stoplist shifts BM25 globally and regressed real answers.
    for word in ("early", "gift", "rate", "bonus"):
        assert word in tokenize(f"what about the {word}")
