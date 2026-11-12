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
