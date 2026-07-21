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

from pistis.models import Passage, SourceOrg

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
    if not cleaned:
        return []
    return [s.strip() for s in _SENTENCE_END.split(cleaned) if s.strip()]


def passages_for(doc: Document) -> list[Passage]:
    sentences = split_sentences(doc.text)
    out: list[Passage] = []
    for i in range(0, len(sentences), PASSAGE_SENTENCES):
        chunk = " ".join(sentences[i : i + PASSAGE_SENTENCES])
        out.append(
            Passage(
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
