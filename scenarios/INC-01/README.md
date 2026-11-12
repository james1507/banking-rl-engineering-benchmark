# INC-01: Concurrent overspend
Simulated production incident, synthetic money only.

Impact/symptom: Same-source withdrawals could overspend stale balance.
First alert: failed outcome assertion or reconciliation finding.

Reproduce: `make scenario SCENARIO=INC-01`. New disposable DB/evaluation cluster each time.
Expected: Canonical account locks and projection guards; serialized UTC actor aggregate in current P1.
Verifier: tests/concurrency/test_concurrency.py.
Evidence: artifacts/scenarios/INC-01.json and .log. These are real only after command executes.
Reset: automatic target DB/container cleanup; normal demo data untouched.
