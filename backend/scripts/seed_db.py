"""Seed deterministic, realistic operational data for local development."""

import asyncio
from datetime import timedelta

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models import utcnow
from app.models.incident import Incident
from app.models.on_call_schedule import OnCallSchedule

SERVICES = (
    "payments-api",
    "auth-service",
    "search-index",
    "notification-worker",
    "billing-sync",
    "admin-portal",
)

ENGINEERS = ("Ava Patel", "Noah Kim", "Mia Chen", "Liam Okafor", "Sofia Garcia", "Ethan Brooks")

TITLES = {
    "payments-api": ("Payment authorization latency elevated", "Card capture requests returning 5xx"),
    "auth-service": ("Token refresh failures increased", "Login callback latency elevated"),
    "search-index": ("Indexing backlog exceeded threshold", "Search shard replication delayed"),
    "notification-worker": ("Email delivery queue delayed", "Webhook retries above normal"),
    "billing-sync": ("Invoice synchronization delayed", "Subscription reconciliation mismatch detected"),
    "admin-portal": ("Administrative dashboard unavailable", "Role-management requests timing out"),
}


def build_incidents() -> list[Incident]:
    """Create 150 incidents across 90 days with elevated P1 frequency for payments-api."""
    now = utcnow()
    incidents: list[Incident] = []
    for number in range(150):
        service = SERVICES[number % len(SERVICES)]
        created_at = now - timedelta(days=(number * 7) % 90, hours=(number * 5) % 24)
        if service == "payments-api" and number % 12 in {0, 6}:
            severity = "P1"
        elif number % 31 == 0:
            severity = "P1"
        elif number % 5 == 0:
            severity = "P2"
        elif number % 3 == 0:
            severity = "P3"
        else:
            severity = "P4"
        status = "open" if number % 17 == 0 else "resolved"
        title = TITLES[service][number % 2]
        incidents.append(
            Incident(
                title=f"{title} ({number + 1:03d})",
                description=(
                    f"Synthetic development incident for {service}. "
                    "Monitoring alerted the on-call engineer and the incident was triaged using the standard runbook."
                ),
                severity=severity,
                service_name=service,
                status=status,
                created_at=created_at,
                resolved_at=None if status == "open" else created_at + timedelta(hours=(number % 12) + 1),
            )
        )
    return incidents


async def seed() -> None:
    """Insert development incidents and current-week on-call assignments if absent."""
    async with async_session_factory() as session:
        existing = await session.scalar(select(Incident.id).limit(1))
        if existing is None:
            session.add_all(build_incidents())

        week_start = (utcnow().date() - timedelta(days=utcnow().weekday()))
        for index, service in enumerate(SERVICES):
            assignment = await session.scalar(
                select(OnCallSchedule).where(
                    OnCallSchedule.service_name == service,
                    OnCallSchedule.week_start == week_start,
                )
            )
            if assignment is None:
                session.add(OnCallSchedule(service_name=service, engineer_name=ENGINEERS[index], week_start=week_start))
        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
