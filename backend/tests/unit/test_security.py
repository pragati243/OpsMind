"""Fail-closed identity resolution tests."""

import asyncio

from app.core import security


def test_missing_api_key_returns_restricted_identity() -> None:
    """An absent credential must never resolve to an application user."""
    identity = asyncio.run(security.resolve_identity(None))

    assert identity == security.RESTRICTED_IDENTITY
    assert identity.clearance_level == 0


def test_identity_store_failure_returns_restricted_identity(monkeypatch) -> None:
    """A database failure must fail closed instead of propagating an unsafe identity."""
    class BrokenSessionContext:
        """Raise while opening a simulated database session."""

        async def __aenter__(self):
            raise RuntimeError("database unavailable")

        async def __aexit__(self, exc_type, exc_value, traceback):
            return False

    monkeypatch.setattr(security, "async_session_factory", lambda: BrokenSessionContext())

    identity = asyncio.run(security.resolve_identity("not-a-real-key"))

    assert identity == security.RESTRICTED_IDENTITY
    assert identity.clearance_level == 0
