# Incident Response Policy

## Purpose
This policy defines how the operations team declares, coordinates, and resolves production incidents.

## Severity and declaration
Declare a P1 when a customer-facing critical capability is unavailable, data integrity is at risk, or a security incident is suspected. The incident commander opens the incident channel, records the timeline, and assigns an on-call responder within ten minutes.

## Response expectations
Responders first stabilize impact, then investigate root cause. Do not make irreversible production changes without an approved change record. Update stakeholders every 30 minutes for P1 and every 60 minutes for P2 incidents.

## Closure
Close an incident only after customer impact has stopped, monitoring is stable, and the timeline includes the mitigation. P1 and P2 incidents require a postmortem.
