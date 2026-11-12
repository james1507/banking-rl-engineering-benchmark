# Readiness review
**Local synthetic engineering portfolio. Not a financial service, regulated deployment, externally reviewed bank security system or production-ready release.**

Verified: fresh local migrations/build, integer money and deferred journal/projection guards, ownership/auth/token rotation, exact durable replay and terminal rejection, actual process crashes, cross-process concurrency, independent reconciliation, 3 isolated task families, worker recovery, UTC limits, 11 scenarios, logical restore counts/digests, local telemetry, dependency/leak checks and small controlled performance profile. Raw evidence under docs/evidence.

Known ceilings:
- Same actor's transfers serialize for correct user-wide UTC quota; account pairs additionally lock in UUID order. Revisit only with measured demand and a transactionally reserved quota design.
- Projection trigger recomputes account ledger sum. Useful safety guard at demonstrated size; cost at 100k is unmeasured. Profile before replacing with stronger aggregate/reservation design.
- Access JWT survives refresh logout until expiry (15 min maximum default). No MFA/public recovery or real registration.
- Logical keyset upper boundary excludes later larger keys; backdated inserts below boundary can appear. No cross-request MVCC snapshot claim.
- Local demo DB owner has full privileges. Candidate migrations have owner rights only in per-run disposable cluster before verifier fixtures. API has non-owner runtime role.
- Public verifier/solutions are public on internet; runtime separation does not create unseen benchmark secrecy. Docker shares kernel; use disposable VM for hostile candidates.
- Source Docker images are pinned; optional observability examples were not run. ARM64 local evidence does not establish amd64 remote results.
- Outbox fake provider proves deduplicated semantic effect, not exactly-once network transport or global event order.
- One restore drill and three small HTTP samples do not establish production RPO/RTO, availability or latency SLO. No HA, replicas, WAL/PITR, public deployment or external security review.
- A Starlette warning remains: HTTPX TestClient adapter is deprecated in installed stack; HTTPX is explicitly required by SRS. Tests pass; migrate test adapter when compatibility demands it.

No v1.0.0 application release tag is created because full P1/P2 scope and remote quality gates remain open. Core/challenge tags identify local verified snapshots only.
