"""HTTP surface: POST /ask, GET /corpus/status, GET /health.

Serves read-only over a corpus snapshot. Every question and outcome is
appended to a local JSONL log (spec §4F monitoring). No accounts, no
cookies, nothing leaves the machine — the MVP collects nothing.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from pistis.corpus.store import load_snapshot
from pistis.engine.answer import Engine
from pistis.index.bm25 import Bm25Index

DEFAULT_SNAPSHOT = Path(__file__).parents[3] / "data" / "corpus" / "snapshot.json"
DEFAULT_LOG = Path(__file__).parents[3] / "logs" / "ask.jsonl"


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


def create_app(
    snapshot_path: Path = DEFAULT_SNAPSHOT,
    log_path: Path | None = DEFAULT_LOG,
) -> FastAPI:
    if not snapshot_path.exists():
        raise FileNotFoundError(
            f"No corpus snapshot at {snapshot_path}. "
            "Run: python -m pistis.corpus.refresh"
        )
    passages = load_snapshot(snapshot_path)
    engine = Engine(Bm25Index(passages))

    app = FastAPI(title="Pistis", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    def log_outcome(question: str, kind: str) -> None:
        if log_path is None:
            return
        log_path.parent.mkdir(parents=True, exist_ok=True)
        record = {"ts": round(time.time(), 3), "question": question, "kind": kind}
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    @app.post("/ask")
    def ask(request: AskRequest) -> dict:
        if not request.question.strip():
            raise HTTPException(status_code=422, detail="question is empty")
        response = engine.ask(request.question)
        log_outcome(request.question, response.kind)
        return asdict(response)

    @app.get("/corpus/status")
    def corpus_status() -> dict:
        docs = {p.doc_id for p in passages}
        return {
            "documents": len(docs),
            "passages": len(passages),
            "orgs": sorted({p.org.value for p in passages}),
            "fetched_at": sorted({p.fetched_at for p in passages}),
        }

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    return app
