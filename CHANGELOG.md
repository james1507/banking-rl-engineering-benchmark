# Changelog
## 0.1.0 (local development)
- New synthetic banking/RL lab; verification checkpoints in docs/implementation-plan.md.
- P0 transactional core, immutable ledger guards, rotating authentication, concurrency/crash checks and independent reconciliation.
- Three patch-based challenges pinned to core-v1.0.0, external HTTP/SQL verifier, restricted candidate containers and eight negative controls each.
- Task version 1.0.2: synchronize before candidate transactions; accept lock-only and optimistic solutions while preserving deterministic stale-read failures.
- Selected P1: bounded leased outbox, beneficiaries/UTC limits/admin operations, trace propagation, eleven incident scenarios, restore drill and measured local load profile.
- English/Vietnamese startup guides and explicit SRS acceptance matrix; advanced tasks, optional UI, remote CI and full release qualification remain open.
