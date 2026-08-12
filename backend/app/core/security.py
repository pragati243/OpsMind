"""Fail-closed API-key identity resolution."""

import asyncio
from dataclasses import dataclass

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.user import ApiKey, User


@dataclass(frozen=True, slots=True)
class ResolvedIdentity:
    """Represent the minimum identity information needed for authorization decisions."""

    user_id: int | None
    name: str
    role: str
    department: str
    clearance_level: int


RESTRICTED_IDENTITY = ResolvedIdentity(
    user_id=None,
    name="anonymous",
    role="none",
    department="none",
    clearance_level=0,
)


def hash_api_key(api_key: str) -> str:
    """Return a bcrypt hash suitable for storage; callers must never persist the raw key."""
    import bcrypt

    return bcrypt.hashpw(api_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


async def resolve_identity(api_key: str | None) -> ResolvedIdentity:
    """Resolve an API key to an identity, returning clearance zero for every failure mode.

    A failed lookup, invalid hash, unavailable database, or unexpected dependency error never
    propagates an identity that could be accidentally authorized.
    """
    if not api_key:
        return RESTRICTED_IDENTITY
    try:
        async with async_session_factory() as session:
            key_records = (await session.scalars(select(ApiKey))).all()
            for key_record in key_records:
                if await asyncio.to_thread(_matches_key, api_key, key_record.key_hash):
                    user = await session.get(User, key_record.user_id)
                    if user is None:
                        return RESTRICTED_IDENTITY
                    return ResolvedIdentity(
                        user_id=user.id,
                        name=user.name,
                        role=user.role,
                        department=user.department,
                        clearance_level=max(0, user.clearance_level),
                    )
    except Exception:
        return RESTRICTED_IDENTITY
    return RESTRICTED_IDENTITY


def _matches_key(api_key: str, key_hash: str) -> bool:
    """Compare an API key to one stored bcrypt hash without exposing either value."""
    import bcrypt

    return bcrypt.checkpw(api_key.encode("utf-8"), key_hash.encode("utf-8"))
