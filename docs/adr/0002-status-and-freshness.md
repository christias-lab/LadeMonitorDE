# ADR 0002: Separate physical status from freshness

Status: accepted

Persist the last normalized physical state and observation time. Derive stale/unknown at query or snapshot time using the publication threshold. A feed that stops reporting must never create a physical outage event.

