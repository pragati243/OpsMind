# SLA Definitions

## Availability targets
payments-api and auth-service have a 99.95% monthly availability target. search-index, notification-worker, billing-sync, and admin-portal have a 99.9% monthly target.

## Incident targets
P1 acknowledgement is due within 10 minutes and mitigation within 60 minutes. P2 acknowledgement is due within 30 minutes and mitigation within four hours. P3 incidents are handled during business hours unless impact expands.

## Measurement
Availability excludes approved maintenance announced at least five business days in advance. Incident timing is measured from the first verified monitoring event.
