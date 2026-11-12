# Architecture
```mermaid
flowchart TD
  API[FastAPI: validation/auth] --> Service[Application: transaction boundary]
  Service --> Domain[Pure domain rules]
  Service --> PG[(PostgreSQL ledger/idempotency/outbox)]
  Worker[Leased worker] --> PG
  Worker --> Fake[Idempotent fake provider]
  Reconcile[Independent read-only SQL] --> PG
  Runner[Host challenge runner] --> Candidate[Restricted candidate container]
  Verifier[Separate verifier container] --> Candidate
  Verifier --> Fresh[(Per-run disposable PostgreSQL)]
```
One modular monolith keeps financial effects inside one ACID boundary.
Module layout is intentionally smaller than the illustrative SRS tree; modules remain cohesive.
See ADRs for guarantees and rejected alternatives.
