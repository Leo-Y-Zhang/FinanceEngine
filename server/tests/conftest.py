from pathlib import Path

import pytest

from finance_answer_engine.corpus.store import load_snapshot
from finance_answer_engine.engine.answer import Engine
from finance_answer_engine.index.bm25 import Bm25Index

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def passages():
    return load_snapshot(FIXTURES / "snapshot.json")


@pytest.fixture(scope="session")
def index(passages):
    return Bm25Index(passages)


@pytest.fixture(scope="session")
def engine(index):
    return Engine(index)
