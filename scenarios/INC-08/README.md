# INC-08: Worker loses acknowledgement
Simulated production incident, synthetic money only.

Impact/symptom: Receiver commits effect, worker crashes before outbox ACK.
First alert: failed outcome assertion or reconciliation finding.

Reproduce: `make scenario SCENARIO=INC-08`. New disposable DB/evaluation cluster each time.
Expected: Lease expiry plus atomic inbox/effect prevents duplicate semantic effect.
Verifier: test_worker_crash_lease_expiry_dedupe.
Evidence: artifacts/scenarios/INC-08.json and .log. These are real only after command executes.
Reset: automatic target DB/container cleanup; normal demo data untouched.
