# Security and privacy

- No provider credential is stored in the mobile app or committed to Git.
- Mobilithek machine certificates are mounted/injected into the ingestion service.
- `.env.example` contains local-only example values, never production secrets.
- Raw payload storage is disabled per publication when its licence does not permit retention.
- Logs contain hashes, publication IDs, and correlation IDs, not payloads, tokens, certificate keys, or user data.
- Phase 1 stores no user account, watchlist, precise user location, or notification token.
- Production authentication, GDPR, retention, threat modelling, and incident response are Phase 5 gates.

