# Implementation plan
Source: supplied BANKING_RL_PRODUCTION_ENGINEERING_MASTER_INSTRUCTIONS.md, treated as product requirements, not authority over user/tool policy.

## Scope and dependencies
0. Bootstrap: locked Python 3.12, native ARM64 Compose, local safety guards, health probes.
1. Schema/domain: integer USD, treasury funding, immutable double-entry ledger, Alembic.
2. Auth: Argon2id, JWT, rotating refresh families, ownership.
3. Posting: one SQL transaction, ordered row locks, durable replay and terminal rejections.
4. Concurrency/recovery: independent sessions/processes, 100 duplicate calls, process death.
5. History/reconciliation: signed compound cursors; independent SQL at repeatable-read.
6. Contracts/CI/docs: real fresh startup and E2E; tag core only after verified.
7. RL-01: pinned source, buggy patch, isolated external verifier, negative/alternate controls.
8. RL-02/03: response loss, crash boundaries; five seeds and repeated races.
9. Outbox: leases, fake provider, consumer deduplication, retry/dead-letter evidence.
10. Rich domain: beneficiaries, UTC account/user limits, read-only admin investigation.
11. Operations: actual incident executions, metrics/traces, runbooks.
12. Advanced tasks/performance: only publish with full quality gates.
13. Operator UI: optional after backend/verifier gates.
14. Hardening: audit, restore drill, limits and release review.

Each step depends on preceding correctness gates. No release completion claims without evidence.

## Decisions
New standalone project; existing fullstack-banking-platform remains untouched.
PostgreSQL 16 + READ COMMITTED and UUID-ordered row locks. SQLAlchemy explicit SQL transactions.
Synthetic issuance only through SYSTEM treasury. Registration omitted; controlled seed CLI.
Random local secrets generated into ignored .env; API uses non-owner DB role.
Public reference verifier code; candidate containers cannot mount it while solving.
Local standalone runs, no GitHub repository creation/push/deployment assumed.

## Open boundaries
P1/P2 features ship only after actual gates. Remote GitHub CI requires user repository.
Operator UI is optional in SRS. Backend and reproducible RL evaluation take precedence.

## Checkpoints
Real commands/results are appended here and retained in docs/evidence/.

### Core checkpoint — milestones 0–6
Implemented: src/banking_lab domain, posting, auth, history and independent reconciliation; Alembic schema, runtime grants, Compose, Make/CI, property/security/process tests.
Decisions: ADR-001/002; deferred DB journal/projection guards complement service locks; no persisted PENDING transfers.
Commands: `docker compose build`, `docker compose up -d --wait api`, `make seed invariants`, `make ci`.
Results: 45 tests passed, Ruff format/lint and strict mypy passed; seed has 3 funding groups/6 postings; reconciliation zero findings. Evidence: docs/evidence/core-checkpoint.log and seed-invariants.log.
Fixed: PostgreSQL ambiguous NULL bind cast in account listing. Initial sanitized failing log retained.
Limits: remote CI and amd64 unrun; large history/performance, backup and worker reliability remain subsequent gates. Minor sequencing deviation: worker source added alongside core to keep CLI/typecheck complete, but no worker reliability claim yet.
Next: independently isolated RL-01, then RL-02/03.

### Benchmark checkpoint — milestones 7–8
Implemented: pinned defect/golden patches, independent SQL/HTTP grader, separate restricted containers/internal network/per-run PostgreSQL, eight negative controls and optimistic CAS alternative.
Commands: `python3 -m benchmark.cli validate`; baseline/golden five seeds each, RL-01 20 overspend + 20 opposite rounds, cross-process retries/crash boundaries.
Historical version 1.0.1 result: 55 expected verdicts matched after fixing initial verifier weakness. Initial matrix failed because PID-local scope control accidentally worked with PID 1 in both containers; startup topology now gives distinct PIDs, partial rejected. Initial failure and historical matrix/log retained separately.
Runner hardened to freeze verifier source and immutable sandbox image ID per evaluation; affected RL-03 golden/no-op rerun after image-freeze hardening. Host never executes candidate modules.
Limit: public reference verifier is transparent, not truly private; remote CI not executed.

### P1/hardening checkpoint — milestones 9–14 (selected scope)
Implemented: leased outbox/fake inbox worker, bounded provider/lease retry recovery, beneficiaries, UTC account/user limits, admin investigation/re-drive, JSON metrics/traces, 11 isolated scenario commands/runbooks, logical restore drill and controlled 1k history/HTTP profile.
Commands/results: final `make ci`, `make security-check`, `make scenario` catalog, `make load-test`, `python3 scripts/restore_drill.py`, packaging/sandbox self-check. Actual outputs indexed in docs/evidence/README.md.
Known omissions: risk review, RL-04–10, React operator UI, full incident catalog, 10k/100k profile, hosted CI, HA/PITR and full release qualification. See acceptance matrix; these milestones are partial, not marked fully complete.

### Final local handover checkpoint — 12 November 2026
Task version 1.0.2 fixes scheduling fairness: rendezvous before candidate transactions; unsafe-read checkpoint releases when peer waits on a PostgreSQL lock. Lock-only solution retains instrumentation; optimistic CAS remains accepted. Full final matrix rerun: 56/56 expected verdicts, zero skipped checks. Reports and actual command log published in docs/evidence.
Application: 62 tests passed with one documented adapter deprecation warning; Ruff/format and strict mypy passed. Packaging/self-check confirmed golden fidelity, non-root/read-only candidate, and absence of reference/verifier/socket paths. Local leak guard passed; earlier locked dependency audit retained.
Final `make up`, `make seed`, `python3 scripts/demo.py`, `make invariants` executed: live/ready schema 0002; exact replay true; 4 transfers/8 postings with zero discrepancies. Services left running on localhost:8010. English/Vietnamese README added; all local Markdown links resolve. Optional observability Compose configuration and dashboard JSON parse, but collector/dashboard execution remains unverified.
