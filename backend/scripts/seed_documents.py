"""Write baseline operational policy documents for local retrieval ingestion."""

from pathlib import Path

DOCUMENTS = {
    "incident_response_policy.md": """# Incident Response Policy

## Purpose
This policy defines how the operations team declares, coordinates, and resolves production incidents.

## Severity and declaration
Declare a P1 when a customer-facing critical capability is unavailable, data integrity is at risk, or a security incident is suspected. The incident commander opens the incident channel, records the timeline, and assigns an on-call responder within ten minutes.

## Response expectations
Responders first stabilize impact, then investigate root cause. Do not make irreversible production changes without an approved change record. Update stakeholders every 30 minutes for P1 and every 60 minutes for P2 incidents.

## Closure
Close an incident only after customer impact has stopped, monitoring is stable, and the timeline includes the mitigation. P1 and P2 incidents require a postmortem.
""",
    "escalation_policy.md": """# Escalation Policy

## When to escalate
Escalate immediately to the incident commander for P1 incidents. Escalate to the service owner when a P2 remains unresolved for 60 minutes or when a mitigation requires their system knowledge.

## Leadership notification
The operations lead notifies engineering leadership within 15 minutes of declaring a P1. Customer Support receives an approved status summary before any external communication.

## Vendor escalation
Engage a vendor only after collecting timestamps, request identifiers, impact scope, and the current mitigation. The on-call engineer remains accountable for the incident while a vendor case is open.
""",
    "on_call_rotation.md": """# On-Call Rotation

## Coverage
Each service has one primary and one backup engineer. The weekly rotation starts Monday at 09:00 UTC and ends the following Monday at 09:00 UTC.

## Handoff
The outgoing primary records active alerts, ongoing maintenance, and known risks in the handoff note. The incoming primary acknowledges the handoff before the rotation changes.

## Responsibilities
The primary responds to pages, coordinates initial triage, and escalates according to the escalation policy. The backup assists when the primary requests help or a P1 is declared.
""",
    "sla_definitions.md": """# SLA Definitions

## Availability targets
payments-api and auth-service have a 99.95% monthly availability target. search-index, notification-worker, billing-sync, and admin-portal have a 99.9% monthly target.

## Incident targets
P1 acknowledgement is due within 10 minutes and mitigation within 60 minutes. P2 acknowledgement is due within 30 minutes and mitigation within four hours. P3 incidents are handled during business hours unless impact expands.

## Measurement
Availability excludes approved maintenance announced at least five business days in advance. Incident timing is measured from the first verified monitoring event.
""",
    "service_ownership.md": """# Service Ownership

## Services
The Payments team owns payments-api and billing-sync. Identity owns auth-service. Platform Search owns search-index. Communications owns notification-worker. Internal Tools owns admin-portal.

## Owner duties
Service owners maintain runbooks, dashboards, service-level objectives, and an active on-call rotation. They review recurring P1 or P2 patterns at the monthly reliability review.

## Dependencies
An incident commander may involve a dependency owner, but the affected service owner remains responsible for customer-impact communication and remediation tracking.
""",
    "postmortem_process.md": """# Postmortem Process

## Scope
Create a blameless postmortem for every P1 and every P2 with material customer impact. Publish the draft within five business days of resolution.

## Required sections
Include customer impact, detection, timeline, root cause, contributing factors, mitigation, and corrective actions. Each action has one owner and a due date.

## Follow-up
The incident commander reviews overdue corrective actions weekly. Close the postmortem only after actions are complete or a documented risk acceptance is approved by the service owner.
""",
}


def seed_documents() -> None:
    """Create or update baseline markdown policy documents in the application data directory."""
    target = Path(__file__).resolve().parents[1] / "app" / "data" / "documents"
    target.mkdir(parents=True, exist_ok=True)
    for filename, content in DOCUMENTS.items():
        (target / filename).write_text(content, encoding="utf-8")


if __name__ == "__main__":
    seed_documents()
