"""Health endpoint definitions."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """Return service liveness without checking external dependencies."""
    return {"status": "ok"}
