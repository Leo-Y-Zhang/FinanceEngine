"""Snapshot store: normalised documents split into citable passages.

A snapshot is a JSON file of documents; each document becomes passages of a
few sentences each, every passage carrying the full citation metadata so a
claim can always point back to a named, dated source.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from finance_answer_engine.models import Passage, SourceOrg

# Sentences per passage: small enough to cite precisely, large enough to rank.
PASSAGE_SENTENCES = 3

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9£])")


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    org: SourceOrg
    url: str
    fetched_at: str
    text: str
    last_updated: str | None = None


def split_sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    # HTML extraction leaves spaces before punctuation ("Lifetime ISA .")
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
    if not cleaned:
        return []
    return [s.strip() for s in _SENTENCE_END.split(cleaned) if s.strip()]


# Introductions to a worked example. Lives here rather than in the gate because
# it is used to mark a REGION of a document, and only the chunker sees document
# order. Deliberately broad: labelling a real rule illustrative costs one
# confidence tier, while failing to label an illustration states an invented
# number as fact.
EXAMPLE_MARK = re.compile(
    r"""
      \bfor\s+example\b
    | \be\.g\.
    | (?:^|[\n.:;!?]\s*|[#*>\-]\s*)(?:worked\s+)?examples?\b
    | \bexamples?\s*[.:](?=\s|$)
    """,
    re.IGNORECASE | re.VERBOSE,
)


def passages_for(doc: Document) -> list[Passage]:
    sentences = split_sentences(doc.text)
    chunks = [
        " ".join(sentences[i : i + PASSAGE_SENTENCES])
        for i in range(0, len(sentences), PASSAGE_SENTENCES)
    ]
    # A chunk is inside an example if it introduces one, OR if the chunk before it
    # did. The marker and the arithmetic it introduces routinely land in different
    # chunks -- PASSAGE_SENTENCES is 3 -- and the later chunk carries no marker of
    # its own, so it used to ship as an established fact. Carrying the flag ONE
    # chunk forward covers roughly six sentences from the marker, which is the
    # span a worked example occupies; it deliberately does NOT latch to the end of
    # the document, which would downgrade every real rule stated after an example.
    marked = [bool(EXAMPLE_MARK.search(c)) for c in chunks]
    out: list[Passage] = []
    for k, chunk in enumerate(chunks):
        i = k * PASSAGE_SENTENCES
        out.append(
            Passage(
                in_example=marked[k] or (k > 0 and marked[k - 1]),
                id=f"{doc.doc_id}#{i // PASSAGE_SENTENCES}",
                doc_id=doc.doc_id,
                text=chunk,
                doc_title=doc.title,
                org=doc.org,
                url=doc.url,
                fetched_at=doc.fetched_at,
                last_updated=doc.last_updated,
            )
        )
    return out


def load_snapshot(path: Path) -> list[Passage]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    passages: list[Passage] = []
    for d in raw["documents"]:
        doc = Document(
            doc_id=d["doc_id"],
            title=d["title"],
            org=SourceOrg(d["org"]),
            url=d["url"],
            fetched_at=d["fetched_at"],
            text=d["text"],
            last_updated=d.get("last_updated"),
        )
        passages.extend(passages_for(doc))
    return passages


def save_snapshot(path: Path, documents: list[Document]) -> None:
    payload = {
        "documents": [
            {
                "doc_id": d.doc_id,
                "title": d.title,
                "org": d.org.value,
                "url": d.url,
                "fetched_at": d.fetched_at,
                "last_updated": d.last_updated,
                "text": d.text,
            }
            for d in documents
        ]
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
