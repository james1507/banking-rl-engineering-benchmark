# ADR-005: Durable replay scope and lifetime
Context: Client timeout cannot establish SQL outcome.

Decision: Unique actor/operation/key; canonical SHA256 body; claim, final response and money commit together. Retain keys indefinitely; expires_at records minimum 24h guarantee, no automatic eviction.

Consequences: Identical retry returns original body/status, including original rejection request_id. X-Request-ID always describes current request.

Rejected alternatives: Process cache, transport-ID namespace, cache TTL as truth.

Evidence: test_transfer_and_durable_replay, test_persisted_rejection; RL-02.
