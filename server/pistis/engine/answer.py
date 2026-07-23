"""Engine orchestrator: classifier gate, then grounding gate.

Both gates must pass — guidance-only AND grounded — before an AnswerCard is
shown (spec §5). Everything else is an honest non-answer with routing.
"""

from __future__ import annotations

from pistis.engine.classifier import classify
from pistis.engine.gate import decide
from pistis.engine.routing import abstain_routing, default_routing
from pistis.index.bm25 import Bm25Index
from pistis.models import Abstention, AnswerCard, Response, RoutingEvent, TrustReport


class Engine:
    def __init__(self, index: Bm25Index) -> None:
        self._index = index

    def ask(self, question: str) -> Response:
        question = question.strip()
        if not question:
            return Abstention(
                question=question,
                reason="Ask a question about UK personal finance.",
                routing=abstain_routing(),
            )

        verdict = classify(question)
        if verdict.is_personal_rec:
            return RoutingEvent(
                question=question,
                reason=verdict.reason,
                routing=default_routing(),
                matched=verdict.matched,
            )

        decision = decide(question, self._index)
        if not decision.answerable:
            return Abstention(
                question=question,
                reason=decision.reason,
                routing=abstain_routing(),
            )

        return AnswerCard(
            question=question,
            claims=decision.claims,
            trust_report=TrustReport.from_verdicts(decision.verdicts),
        )
