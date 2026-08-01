from pistis.corpus.store import (
    Document,
    load_snapshot,
    passages_for,
    save_snapshot,
    split_sentences,
)
from pistis.models import SourceOrg


def make_doc(text, **overrides):
    defaults = {
        "doc_id": "d1",
        "title": "Doc",
        "org": SourceOrg.GOVUK,
        "url": "https://www.gov.uk/d1",
        "fetched_at": "2026-07-21",
        "last_updated": "2026-04-06",
    }
    defaults.update(overrides)
    return Document(text=text, **defaults)


def test_split_sentences_basic():
    assert split_sentences("One rule. Another rule. £20,000 is the limit.") == [
        "One rule.",
        "Another rule.",
        "£20,000 is the limit.",
    ]


def test_split_sentences_collapses_whitespace():
    assert split_sentences("  A  rule.\n\n Second   rule. ") == ["A rule.", "Second rule."]


def test_passages_chunked_in_threes():
    text = " ".join(f"Sentence number {i} is here." for i in range(7))
    passages = passages_for(make_doc(text))
    assert [p.id for p in passages] == ["d1#0", "d1#1", "d1#2"]
    assert passages[0].text.count(".") == 3
    assert passages[2].text.count(".") == 1


def test_passages_carry_citation_metadata():
    p = passages_for(make_doc("Only sentence."))[0]
    assert p.org is SourceOrg.GOVUK
    assert p.url == "https://www.gov.uk/d1"
    assert p.fetched_at == "2026-07-21"
    assert p.last_updated == "2026-04-06"


def test_snapshot_round_trip(tmp_path):
    doc = make_doc("First fact. Second fact.", last_updated=None)
    path = tmp_path / "snap.json"
    save_snapshot(path, [doc])
    passages = load_snapshot(path)
    assert len(passages) == 1
    assert passages[0].text == "First fact. Second fact."
    assert passages[0].last_updated is None


# A worked example's marker and its arithmetic routinely land in different
# chunks - PASSAGE_SENTENCES is 3 - and the later chunk carries no marker of its
# own. The gate searched each chunk in isolation, so that chunk shipped as an
# established fact: invented figures presented as GOV.UK rules.

def test_an_example_spanning_a_chunk_boundary_stays_marked() -> None:
    from pistis.corpus.store import EXAMPLE_MARK, Document, passages_for
    from pistis.models import SourceOrg

    doc = Document(
        doc_id="d", title="T", org=SourceOrg.GOVUK, url="u",
        fetched_at="2026-07-21", last_updated="2026-04-06",
        text=(
            "For example, take a basic rate taxpayer. "
            "They have wages and some savings interest. "
            "Their situation is set out below. "
            "You would pay tax on 500 pounds of savings interest. "
            "Your total taxable savings interest would be 500 pounds. "
            "That is the amount shown on the calculation. "
            "The personal savings allowance is 1000 pounds for basic rate taxpayers. "
            "It applies to interest from banks. "
            "It is set each tax year."
        ),
    )
    chunks = passages_for(doc)
    assert len(chunks) == 3

    # The chunk that introduces the example.
    assert chunks[0].in_example

    # The one carrying its arithmetic: no marker of its own, still illustrative.
    assert not EXAMPLE_MARK.search(chunks[1].text), "precondition: no marker here"
    assert chunks[1].in_example, "example arithmetic must not read as a rule"

    # And it must NOT latch forever - a real rule after the example is a rule.
    assert not chunks[2].in_example
