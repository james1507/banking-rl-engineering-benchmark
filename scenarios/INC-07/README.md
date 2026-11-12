# INC-07: Provider outage after posting
Simulated production incident, synthetic money only.

Impact/symptom: Fake provider returns 500/429/timeout.
First alert: failed outcome assertion or reconciliation finding.

Reproduce: `make scenario SCENARIO=INC-07`. New disposable DB/evaluation cluster each time.
Expected: Outbox retries after commit; receiver deduplicates; financial state unaffected.
Verifier: test_provider_failure_recovery.
Evidence: artifacts/scenarios/INC-07.json and .log. These are real only after command executes.
Reset: automatic target DB/container cleanup; normal demo data untouched.
