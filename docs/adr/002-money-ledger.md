# ADR-002: Integer double-entry ledger
Context: floats round and cached balances alone cannot explain changes.
Decision: signed BIGINT minor units, paired postings, negative SYSTEM treasury only.
Consequences: strict API validation, overflow checks and independent reconciliation required.
Rejected: floating point, nonzero opening balance without postings, editable ledger.
Evidence: boundary/property and immutable-journal tests when executed.
