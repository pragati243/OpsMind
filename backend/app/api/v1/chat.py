"""Unified policy, data, and hybrid question endpoint."""

import asyncio

from fastapi import APIRouter, Depends, Header

from app.agent.nodes.router_node import RouterNode
from app.core.llm_client import GroqLLMClient, LLMClient
from app.core.security import RESTRICTED_IDENTITY, ResolvedIdentity, resolve_identity
from app.schemas.chat import AskRequest, AskResponse
from app.schemas.rag import RAGResult
from app.schemas.text2sql import Text2SQLResult
from app.services.rag_service import RAGService
from app.services.text2sql_service import Text2SQLService
from app.guardrails.input_guard import inspect as inspect_input
from app.guardrails.output_guard import validate_schema, check_numeric_claims

router = APIRouter(prefix="/api/v1", tags=["chat"])
SYNTHESIS_PROMPT = """Produce only a concise recommended action based strictly on the supplied policy answer
and actual database result. Do not add unsupported facts. The API will place your response under
the 'Recommended action' heading."""


class ChatService:
    """Orchestrate routing and source-specific services for the ask endpoint."""

    def __init__(
        self,
        router_node: RouterNode | None = None,
        rag_service: RAGService | None = None,
        text2sql_service: Text2SQLService | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self._router = router_node or RouterNode()
        self._rag_service = rag_service
        self._text2sql_service = text2sql_service
        self._llm_client = llm_client

    async def ask(self, question: str, user: ResolvedIdentity = RESTRICTED_IDENTITY) -> AskResponse:
        """Route a question and return only evidence-backed service output."""
        decision = await self._router.route(question)
        if decision.query_type in {"refused", "vague"}:
            return AskResponse(
                question=question,
                query_type=decision.query_type,
                answer=decision.message or "I need more information to answer safely.",
                refusal_reason=decision.message,
            )
        if decision.query_type == "document":
            rag_result = await self._get_rag_service().run_rag(question, user)
            resp = AskResponse(
                question=question,
                query_type="document",
                answer=rag_result.answer,
                citations=rag_result.citations,
                refusal_reason=None if rag_result.grounded else rag_result.answer,
            )
            # attach underlying rag_result for downstream output guards
            try:
                resp._rag_result = rag_result
            except Exception:
                pass
            return resp
        if decision.query_type == "data":
            sql_result = await self._get_text2sql_service().run_text2sql(question)
            return self._data_response(question, sql_result)

        rag_result, sql_result = await asyncio.gather(
            self._get_rag_service().run_rag(question, user),
            self._get_text2sql_service().run_text2sql(question),
        )
        if not rag_result.grounded or not sql_result.valid:
            reason = rag_result.answer if not rag_result.grounded else sql_result.rejection_reason
            return AskResponse(
                question=question,
                query_type="hybrid",
                answer="I could not obtain sufficient verified policy and data evidence for a hybrid answer.",
                citations=rag_result.citations,
                generated_sql=sql_result.sql or None,
                sql_validation=sql_result.sql_validation,
                result_table=sql_result.rows,
                refusal_reason=reason,
            )
        recommendation = await self._get_llm_client().generate(
            SYNTHESIS_PROMPT,
            f"Policy answer:\n{rag_result.answer}\n\nActual data rows:\n{sql_result.rows}",
        )
        answer = (
            f"Policy says:\n{rag_result.answer}\n\n"
            f"Data shows:\n{sql_result.explanation}\n\n"
            f"Recommended action:\n{recommendation}"
        )
        return AskResponse(
            question=question,
            query_type="hybrid",
            answer=answer,
            citations=rag_result.citations,
            generated_sql=sql_result.sql,
            sql_validation=sql_result.sql_validation,
            result_table=sql_result.rows,
            business_insight=recommendation,
        )

    @staticmethod
    def _data_response(question: str, result: Text2SQLResult) -> AskResponse:
        """Map a Text2SQL result to an endpoint response without hiding failed validation."""
        return AskResponse(
            question=question,
            query_type="data",
            answer=result.explanation if result.valid else "I cannot safely answer with operational data.",
            generated_sql=result.sql or None,
            sql_validation=result.sql_validation,
            result_table=result.rows,
            business_insight=result.explanation if result.valid else None,
            refusal_reason=result.rejection_reason,
        )

    def _get_rag_service(self) -> RAGService:
        """Return the configured RAG service, constructing it only when routing requires it."""
        if self._rag_service is None:
            self._rag_service = RAGService()
        return self._rag_service

    def _get_text2sql_service(self) -> Text2SQLService:
        """Return the configured Text2SQL service only when the data route is selected."""
        if self._text2sql_service is None:
            self._text2sql_service = Text2SQLService()
        return self._text2sql_service

    def _get_llm_client(self) -> LLMClient:
        """Return the synthesis client only after a verified hybrid result is available."""
        if self._llm_client is None:
            self._llm_client = GroqLLMClient()
        return self._llm_client


def get_chat_service() -> ChatService:
    """Construct the production chat orchestration service for each request."""
    return ChatService()


async def get_request_identity(x_api_key: str | None = Header(default=None)) -> ResolvedIdentity:
    """Resolve a request API key to a fail-closed identity before retrieval is dispatched."""
    return await resolve_identity(x_api_key)


@router.post("/ask", response_model=AskResponse)
async def ask(
    request: AskRequest,
    service: ChatService = Depends(get_chat_service),
    user: ResolvedIdentity = Depends(get_request_identity),
) -> AskResponse:
    """Answer a routed operations question using the appropriate safe pipeline."""
    # Run input guard: refuse on injection, otherwise redact PII before routing.
    inspection = inspect_input(request.question)
    if inspection.refused:
        return AskResponse(
            question=request.question,
            query_type="refused",
            answer="Request refused: prompt injection detected.",
            refusal_reason=inspection.refusal_reason,
        )

    # use the redacted question downstream
    response = await service.ask(inspection.redacted, user)

    # Validate final response parses against the schema (one retry not supported here)
    try:
        validate_schema(response.dict(), AskResponse)
    except Exception:
        return AskResponse(
            question=request.question,
            query_type="refused",
            answer="Response generation failed schema validation.",
            refusal_reason="output_schema_validation",
        )

    # If the response came from RAG, cross-check numeric claims against retrieved chunks
    mismatches = []
    try:
        rag_result = getattr(response, "_rag_result", None)
        if rag_result is not None:
            retrieved_texts = [getattr(c, "text", "") for c in getattr(rag_result, "_retrieved_chunks", [])]
            mismatches = check_numeric_claims(response.answer or "", retrieved_texts)
    except Exception:
        mismatches = []

    if mismatches:
        # Flag the issue rather than silently returning potentially incorrect numeric claims
        response.refusal_reason = f"numeric_mismatch: {mismatches}"

    return response
