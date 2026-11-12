# Actual task validation
Task version 1.0.2; pinned base commit in each metadata.json. See [complete matrix](evidence/validation-matrix.json) and [individual reports](evidence/challenges/).

| Task | Baseline five seeds | Golden five seeds | 8 negative controls | Alternative |
|---|---|---|---|---|
| RL-01 | FAIL × 5 expected | PASS × 5 | FAIL × 8 expected | optimistic CAS PASS; lock-only PASS |
| RL-02 | FAIL × 5 expected | PASS × 5 | FAIL × 8 expected | not required |
| RL-03 | FAIL × 5 expected | PASS × 5 | FAIL × 8 expected | not required |

56 actual evaluations matched expected verdicts; no skipped checks. Baseline candidate FAIL is expected data, never presented as a solved candidate. CLI rejects environment/timeouts/verifier errors as successful gates.

Seeds: 101, 202, 303, 404, 505. RL-01 golden has 20 synchronized overspend and 20 opposite-direction rounds per seed, plus unrelated-account liveness. RL-01/RL-02 have 100 same-key retry calls per run across two separate API processes. RL-03 checks actual process exit before posting, after source update, before commit and after commit/response loss. Independent SQL checks ledger/cache/status/idempotency/outbox; serial/authorization/strict validation regressions also tested.

Initial validation correctly remained FAIL when PID-namespaced partial RL-02 unexpectedly passed: both containers used PID 1. Initial failed matrix/log are preserved under evidence/initial-validation. Startup topology now uses direct and child-process launch, so PIDs differ; partial is rejected. Verifier and candidate image are frozen per run.

The successful historical 55-run version 1.0.1 matrix/log are preserved under evidence/pre-fairness-validation. Version 1.0.2 moves request synchronization before candidate transactions and releases the unsafe-read checkpoint when the peer is waiting on a PostgreSQL lock. This accepts correct implementations that retain the public callback or serialize the actor before account locking. The added lock-only solution changes only FOR UPDATE and keeps that callback. All 56 required evaluations were rerun against this final driver.

Reports include actual measured duration, dependency/image/environment digests, failure codes and SQL findings. Public source/solutions are transparent portfolio artifacts, not a secret internet benchmark. Runtime grading does not mount them into candidate containers.
