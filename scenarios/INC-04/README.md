# INC-04: Opposite transfer lock contention
Simulated production incident, synthetic money only.

Impact/symptom: Reversed lock order may deadlock in naive service.
First alert: failed outcome assertion or reconciliation finding.

Reproduce: `make scenario SCENARIO=INC-04`. New disposable DB/evaluation cluster each time.
Expected: Canonical UUID order and whole-transaction retry budget.
Verifier: tests/concurrency/test_concurrency.py.
Evidence: artifacts/scenarios/INC-04.json and .log. These are real only after command executes.
Reset: automatic target DB/container cleanup; normal demo data untouched.
