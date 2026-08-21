# ADR 0004: Synthetic and live data isolation

Status: accepted

All records and responses carry a data mode. Synthetic publications use a dedicated source and immutable seed/reference time. The mobile app renders a persistent demo label. Synthetic and live observations cannot be silently combined.

