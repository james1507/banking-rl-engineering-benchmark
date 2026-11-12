# ADR-008: Prefer bounded uncertainty over false success
Context: Database commit acknowledgement or HTTP response may disappear.

Decision: Return retryable 503 for ambiguous infrastructure outcome; caller must retain same key. Rollback before commit; replay after commit. Separate operational lag from money correctness.

Consequences: No automatic repair or non-idempotent blind retry. Default local ports bind loopback; no production HA claims.

Rejected alternatives: Return failure as proof of rollback; provider outage reversing posted money.

Evidence: Crash tests, RL-02/03; runbooks.
