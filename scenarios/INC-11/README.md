# INC-11: Cross-user resource access
Simulated production incident, synthetic money only.

Impact/symptom: Actor changes foreign account UUID in nested resource request.
First alert: failed outcome assertion or reconciliation finding.

Reproduce: `make scenario SCENARIO=INC-11`. New disposable DB/evaluation cluster each time.
Expected: Owner-scoped account/statement and source debit validation.
Verifier: test_bola_every_object.
Evidence: artifacts/scenarios/INC-11.json and .log. These are real only after command executes.
Reset: automatic target DB/container cleanup; normal demo data untouched.
