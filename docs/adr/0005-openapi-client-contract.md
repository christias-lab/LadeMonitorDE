# ADR 0005: OpenAPI is the mobile contract

Status: accepted

FastAPI's versioned OpenAPI document is the source of truth. The repository keeps a normalized contract snapshot and a Dart client boundary. CI detects contract drift; Flutter does not depend on backend ORM models.

