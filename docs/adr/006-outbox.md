# ADR-006: At-least-once attempts, deduplicated effect
Context: Notification acknowledgement can be lost after receiver commits.

Decision: Write event with transfer. SKIP LOCKED lease, lease token fencing, bounded retries. Fake provider atomically inserts inbox receipt and effect.

Consequences: No global ordering guarantee; independent notifications tolerate reordering. Lease expiry permits safe retry.

Rejected alternatives: Network call inside money transaction, exactly-once network claims.

Evidence: Worker reliability tests and INC-07/08 when executed.
