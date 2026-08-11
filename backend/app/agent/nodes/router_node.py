"""Two-layer deterministic and LLM-backed request router."""

import json
import re
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from app.config import get_settings
from app.core.llm_client import GroqLLMClient, LLMClient

QueryType = Literal["document", "data", "hybrid", "vague", "refused"]
DESTRUCTIVE_INTENT = re.compile(r"\b(?:delete\s+all|drop\s+table|truncate|delete\s+(?:the|an?|all))\b", re.IGNORECASE)
SPECULATIVE_INTENT = re.compile(r"\b(?:guess\s+why|without\s+data|make\s+up)\b", re.IGNORECASE)
ROUTER_PROMPT = """Classify the user question as exactly one of document, data, hybrid, or vague.
document: asks about a policy or process. data: asks about incident or on-call records.
hybrid: requires both policy and operational data. vague: lacks necessary specificity.
Return strict JSON only: {\"query_type\": \"...\", \"confidence\": 0.0}."""


class RouterClassification(BaseModel):
    """Represent an LLM's constrained routing classification."""

    query_type: Literal["document", "data", "hybrid", "vague"]
    confidence: float = Field(ge=0, le=1)


class RouterDecision(BaseModel):
    """Represent a routing decision and any safe user-facing clarification."""

    query_type: QueryType
    confidence: float
    message: str | None = None


class RouterNode:
    """Route requests, applying deterministic refusal checks before any LLM call."""

    def __init__(self, llm_client: LLMClient | None = None, confidence_threshold: float | None = None) -> None:
        settings = get_settings() if llm_client is None or confidence_threshold is None else None
        self._llm_client = llm_client or GroqLLMClient()
        self._confidence_threshold = (
            confidence_threshold if confidence_threshold is not None else settings.router_confidence_threshold
        )

    async def route(self, question: str) -> RouterDecision:
        """Return a safe route; deterministic unsafe requests never invoke the LLM."""
        if DESTRUCTIVE_INTENT.search(question):
            return RouterDecision(query_type="refused", confidence=1, message="I cannot help perform destructive actions.")
        if SPECULATIVE_INTENT.search(question):
            return RouterDecision(
                query_type="refused",
                confidence=1,
                message="I cannot speculate without verified policy or operational data.",
            )
        try:
            response = await self._llm_client.generate(ROUTER_PROMPT, question)
            classification = RouterClassification.model_validate(json.loads(_strip_code_fence(response)))
        except (json.JSONDecodeError, ValidationError, RuntimeError, ValueError):
            return self._vague()
        if classification.confidence < self._confidence_threshold:
            return self._vague(classification.confidence)
        return RouterDecision(query_type=classification.query_type, confidence=classification.confidence)

    @staticmethod
    def _vague(confidence: float = 0) -> RouterDecision:
        """Return the fail-closed clarification route for ambiguous classification."""
        return RouterDecision(
            query_type="vague",
            confidence=confidence,
            message="Could you clarify whether you need a policy answer, incident data, or both?",
        )


def _strip_code_fence(value: str) -> str:
    """Remove a surrounding markdown fence from an otherwise JSON-only response."""
    value = value.strip()
    if value.startswith("```") and value.endswith("```"):
        return "\n".join(value.splitlines()[1:-1]).strip()
    return value
