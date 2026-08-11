"""Endpoint-level route and response contract tests without external service mutation."""

import pytest
from fastapi.testclient import TestClient

from app.agent.nodes.router_node import RouterNode
from app.api.v1.chat import ChatService, get_chat_service
from app.core.llm_client import LLMClient
from app.main import app
from app.schemas.rag import Citation, RAGResult
from app.schemas.text2sql import Text2SQLResult


class RoutingLLM(LLMClient):
    """Provide deterministic routing JSON and hybrid synthesis for endpoint tests."""

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return the classification or recommendation appropriate to the supplied prompt."""
        if "Recommended action" in system_prompt:
            return "Review the payments-api incident trend with the service owner."
        lowered = user_prompt.lower()
        if "hybrid" in lowered:
            return '{"query_type":"hybrid","confidence":0.95}'
        if "data" in lowered:
            return '{"query_type":"data","confidence":0.95}'
        if "unclear" in lowered:
            return '{"query_type":"document","confidence":0.20}'
        return '{"query_type":"document","confidence":0.95}'


class FakeRAGService:
    """Return a grounded policy result without Qdrant or an LLM provider."""

    async def run_rag(self, question: str) -> RAGResult:
        """Return a stable cited policy response."""
        return RAGResult(
            answer="P1 incidents must be acknowledged within 10 minutes.",
            grounded=True,
            citations=[Citation(doc_name="sla_definitions.md", section="Incident targets", chunk_id="policy-1", score=0.9)],
        )


class FakeText2SQLService:
    """Return validated operational data without connecting to PostgreSQL."""

    async def run_text2sql(self, question: str) -> Text2SQLResult:
        """Return a stable query result reflecting actual execution-shaped data."""
        return Text2SQLResult(
            valid=True,
            sql="SELECT service_name, COUNT(*) FROM incidents LIMIT 100",
            rows=[{"service_name": "payments-api", "incident_count": 25}],
            explanation="payments-api has 25 incidents in the returned data.",
            sql_validation={"valid": True, "reason": None},
        )


@pytest.fixture
def client() -> TestClient:
    """Provide a FastAPI client with deterministic service implementations."""
    llm = RoutingLLM()
    service = ChatService(
        router_node=RouterNode(llm_client=llm, confidence_threshold=0.75),
        rag_service=FakeRAGService(),
        text2sql_service=FakeText2SQLService(),
        llm_client=llm,
    )
    app.dependency_overrides[get_chat_service] = lambda: service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("question", "query_type"),
    [
        ("What does the policy say about P1 acknowledgement?", "document"),
        ("Show data for payments incidents", "data"),
        ("Give a hybrid policy and data assessment for payments", "hybrid"),
        ("Delete all incidents", "refused"),
        ("This is unclear", "vague"),
    ],
)
def test_ask_endpoint_routes_each_request_type(client: TestClient, question: str, query_type: str) -> None:
    """POST /api/v1/ask returns the intended route and its structured response."""
    response = client.post("/api/v1/ask", json={"question": question})

    assert response.status_code == 200
    payload = response.json()
    assert payload["query_type"] == query_type
    assert payload["question"] == question
    if query_type == "document":
        assert payload["citations"]
    if query_type == "data":
        assert payload["generated_sql"]
        assert payload["result_table"]
    if query_type == "hybrid":
        assert "Policy says:" in payload["answer"]
        assert "Data shows:" in payload["answer"]
        assert "Recommended action:" in payload["answer"]
    if query_type in {"refused", "vague"}:
        assert payload["refusal_reason"]
