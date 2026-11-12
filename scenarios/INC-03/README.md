# INC-03: Mid-posting process death
Simulated production incident, synthetic money only.

Impact/symptom: Defective snapshot commits debit in independent transaction, then process exits.
First alert: failed outcome assertion or reconciliation finding.

Reproduce: `make scenario SCENARIO=INC-03`. New disposable DB/evaluation cluster each time.
Expected: One SQL unit of work and restored projection guards.
Verifier: RL-03 independent external verifier.
Evidence: artifacts/scenarios/INC-03.json and .log. These are real only after command executes.
Reset: automatic target DB/container cleanup; normal demo data untouched.
