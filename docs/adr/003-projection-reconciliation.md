# ADR-003: Balance projection and immutable history
Context: Fast balance reads need an explainable source.

Decision: Update cache and paired ledger in one transaction; deferred DB triggers reject drift. Independent repeatable-read SQL detects historical corruption.

Consequences: More write checks; reconciliation never edits evidence.

Rejected alternatives: Bare cache, mutable journal, silent repair.

Evidence: test_database_guards_and_drift_detector; reconcile CLI.
