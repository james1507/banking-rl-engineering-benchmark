# ADR-004: Ordered locks with bounded retries
Context: Concurrent withdrawals and reversed account pairs can race/deadlock.

Decision: READ COMMITTED; SELECT FOR UPDATE in UUID order; check locked state; retry entire transaction for 40001/40P01/55P03 up to three attempts.

Consequences: Short transactions, bounded waits. Pool/statement/connection errors become explicit retryable outcomes.

Rejected alternatives: Global Python mutex cannot span processes; SERIALIZABLE needs retries; optimistic CAS accepted by verifier as alternate.

Evidence: 100 same-key tests, overspend/opposite tests, process crash tests; RL-01 independent verifier.

P1 refinement: daily limits span a user's multiple accounts, so current main app locks actor FOR NO KEY UPDATE before account locks. This serializes same actor only and protects concurrent limit configuration. Pinned P0 challenge retains original FOR SHARE actor read to isolate account-lock task.
