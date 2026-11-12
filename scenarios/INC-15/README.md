# INC-15: UTC midnight transfer limit
Simulated production incident, synthetic money only.

Impact/symptom: Outgoing quota race across accounts and replay across midnight.
First alert: failed outcome assertion or reconciliation finding.

Reproduce: `make scenario SCENARIO=INC-15`. New disposable DB/evaluation cluster each time.
Expected: Per-user SQL lock, source locks, UTC ledger sums; replay precedes quota evaluation.
Verifier: tests/integration/test_limits.py.
Evidence: artifacts/scenarios/INC-15.json and .log. These are real only after command executes.
Reset: automatic target DB/container cleanup; normal demo data untouched.
