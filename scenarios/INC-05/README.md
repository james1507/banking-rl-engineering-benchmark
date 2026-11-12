# INC-05: Ledger projection drift
Simulated production incident, synthetic money only.

Impact/symptom: Disposable owner-only fixture bypasses trigger to corrupt cached balance.
First alert: failed outcome assertion or reconciliation finding.

Reproduce: `make scenario SCENARIO=INC-05`. New disposable DB/evaluation cluster each time.
Expected: Read-only independent reconciliation detects drift; no silent repair.
Verifier: test_database_guards_and_drift_detector.
Evidence: artifacts/scenarios/INC-05.json and .log. These are real only after command executes.
Reset: automatic target DB/container cleanup; normal demo data untouched.
