# Project guidance
Synthetic money only. Never connect real banks or use customer data.
Keep core domain free of framework/DB imports. Services own SQL transactions.
Money uses strict signed 64-bit integer minor units. Preserve paired immutable postings,
owner authorization, atomic idempotency/outbox, ordered row locks, bounded retries.
Run make lint typecheck test invariants after money changes. Record actual output.
Challenge bugs belong only in patch-based snapshots, never in src/.
Do not expose verifier/reference files or Docker socket to candidate code.
Do not claim production readiness, regulatory compliance, remote CI, or unrun checks.
