# INC-06: Connection pool exhaustion
Simulated production incident, synthetic money only.

Impact/symptom: One-slot test engine has its only connection held.
First alert: failed outcome assertion or reconciliation finding.

Reproduce: `make scenario SCENARIO=INC-06`. New disposable DB/evaluation cluster each time.
Expected: Bounded 503; release connection then same-key retry succeeds.
Verifier: test_pool_exhaustion_is_bounded_and_recovers.
Evidence: artifacts/scenarios/INC-06.json and .log. These are real only after command executes.
Reset: automatic target DB/container cleanup; normal demo data untouched.
