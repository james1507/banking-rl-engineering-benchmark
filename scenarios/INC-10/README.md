# INC-10: Equal-timestamp pagination
Simulated production incident, synthetic money only.

Impact/symptom: Timestamp-only or offset pagination skips/duplicates history.
First alert: failed outcome assertion or reconciliation finding.

Reproduce: `make scenario SCENARIO=INC-10`. New disposable DB/evaluation cluster each time.
Expected: Signed compound cursor, context and upper key boundary.
Verifier: test_equal_timestamp_pages_and_tamper.
Evidence: artifacts/scenarios/INC-10.json and .log. These are real only after command executes.
Reset: automatic target DB/container cleanup; normal demo data untouched.
