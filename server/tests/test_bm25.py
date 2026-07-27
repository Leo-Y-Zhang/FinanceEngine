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
