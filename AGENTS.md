# Project Instructions

- Python runtime is 3.12.
- Keep route handlers thin; business logic belongs in services.
- Use async clients for PostgreSQL, Redis, and third-party HTTP APIs.
- Never log API keys, raw images, complete Base64 payloads, raw browser fingerprints, or provider response bodies.
- Only poems with `verification_status = verified` may be returned by matching APIs.
- The canonical poem text stored locally is the product source of truth. Online candidates must not overwrite it.
- Browser fingerprint limiting is best-effort abuse prevention: 100 requests per fingerprint per `Asia/Hong_Kong` day.
- Redis quota updates must remain atomic through Lua; do not replace them with separate check/increment calls.
- Do not add IP-based quotas unless the product decision changes explicitly.
- Use Alembic for every relational schema change.
- Do not add image persistence, login, Celery, or vector search to the MVP without an explicit scope change.

