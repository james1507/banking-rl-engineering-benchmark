# INC-02: Lost response after commit
Simulated production incident, synthetic money only.

Impact/symptom: Client loses HTTP response after DB commits and retries from another process.
First alert: failed outcome assertion or reconciliation finding.

Reproduce: `make scenario SCENARIO=INC-02`. New disposable DB/evaluation cluster each time.
Expected: Durable idempotency with atomic response; original key replays, never new key.
Verifier: RL-02 independent external verifier.
Evidence: artifacts/scenarios/INC-02.json and .log. These are real only after command executes.
Reset: automatic target DB/container cleanup; normal demo data untouched.
