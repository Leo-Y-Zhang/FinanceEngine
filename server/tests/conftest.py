from pathlib import Path
from urllib.parse import urlsplit

import pytest

from finance_engine.corpus.store import load_snapshot
from finance_engine.engine.answer import Engine
from finance_engine.index.bm25 import Bm25Index

FIXTURES = Path(__file__).parent / "fixtures"


def host_is(url: str, domain: str) -> bool:
    """True when the URL's host IS domain, or a subdomain of it.

    Host assertions go through the parsed hostname rather than `domain in url`
    because a substring is also satisfied by a look-alike: the string
    "moneyhelper.org.uk" is inside https://moneyhelper.org.uk.example.com/,
    which is not MoneyHelper. Routing links and manifest locators are exactly
    the places where that distinction is the whole point of the assertion.
    """
    host = (urlsplit(url).hostname or "").lower()
    return host == domain or host.endswith(f".{domain}")


@pytest.fixture(scope="session")
def passages():
    return load_snapshot(FIXTURES / "snapshot.json")


@pytest.fixture(scope="session")
def index(passages):
    return Bm25Index(passages)


@pytest.fixture(scope="session")
def engine(index):
    return Engine(index)
