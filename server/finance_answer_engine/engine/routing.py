"""Defer-to-guidance routing.

Routing is a first-class outcome: it explains *why* regulated advice carries
protections guidance cannot (FOS complaints, FSCS compensation, adviser
accountability), then links the official next steps.
"""

from __future__ import annotations

from finance_answer_engine.models import Routing, RoutingLink

ROUTING_MESSAGE = (
    "Finance Answer Engine can explain how things work, but it cannot tell you what is right "
    "for your situation — that is regulated financial advice, and it comes "
    "with protections guidance cannot offer: an FCA-authorised adviser is "
    "accountable to you, you can complain to the Financial Ombudsman Service, "
    "and the FSCS may compensate you if things go wrong. Here is where to go "
    "next."
)

ABSTAIN_MESSAGE = (
    "Finance Answer Engine answers only what it can verify against its trusted UK sources — "
    "guessing is how money answers go wrong. These official services can help "
    "instead."
)

ROUTING_LINKS: tuple[RoutingLink, ...] = (
    RoutingLink(
        label="MoneyHelper — free, government-backed money guidance",
        url="https://www.moneyhelper.org.uk/en",
    ),
    RoutingLink(
        label="MoneyHelper — choosing a financial adviser",
        url="https://www.moneyhelper.org.uk/en/getting-help-and-advice/financial-advisers/choosing-a-financial-adviser",
    ),
    RoutingLink(
        label="FCA Register — check a firm or adviser is authorised",
        url="https://register.fca.org.uk/",
    ),
)


def default_routing() -> Routing:
    return Routing(message=ROUTING_MESSAGE, links=ROUTING_LINKS)


def abstain_routing() -> Routing:
    return Routing(message=ABSTAIN_MESSAGE, links=ROUTING_LINKS)
