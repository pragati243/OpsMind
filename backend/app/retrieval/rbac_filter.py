"""Qdrant-native retrieval permission predicates."""

from typing import Protocol

from qdrant_client.models import FieldCondition, Filter, MatchValue, Range


class ClearancePrincipal(Protocol):
    """Define the identity attributes used by retrieval authorization."""

    clearance_level: int
    department: str


def build_permission_filter(user: ClearancePrincipal) -> Filter:
    """Build the ANN payload filter allowing chunks at or below the user's clearance.

    The clearance predicate is deliberately expressed for Qdrant execution rather than applied to
    retrieved results, preventing restricted chunks from entering the candidate set at all.
    """
    clearance_level = max(0, user.clearance_level)
    return Filter(
        must=[FieldCondition(key="required_clearance_level", range=Range(lte=clearance_level))],
        should=[
            FieldCondition(key="owning_department", match=MatchValue(value=user.department)),
            FieldCondition(key="owning_department", match=MatchValue(value="Operations")),
        ],
    )
