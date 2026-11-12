# SRS acceptance matrix
Status refers to actual local implementation and evidence, not certification.

| Milestone/scope | Status | Evidence / limitation |
|---|---|---|
| 0: packaging, Compose, safety, health | Verified | Locked deps, native ARM64 build, live/ready, runtime DB role, safety unit checks |
| 1: domain, migrations, treasury ledger | Verified | Fresh 0001/0002 test DBs, DB guards, paired seed, BIGINT boundaries |
| 2: auth and ownership | Verified | Login/refresh/replay/logout/JWT/BOLA/rate-limit tests |
| 3: atomic posting | Verified | Exact balances, ledger/outbox/idempotency, stable rejection, constraints |
| 4: concurrency and process crash | Verified | 100 same-key calls, overspend/opposite tests, actual process exit at failpoints |
| 5: history and reconciliation | Verified | Equal timestamps, signed context cursor, tamper/owner rejection, drift detection, 1k history profile |
| 6: contracts / CI / baseline | Local verified | make ci and fresh startup passed; GitHub workflows unrun remotely |
| 7: RL-01 | Verified | Five baseline/golden seeds, 20 races + 20 opposite rounds per golden, eight negative controls, optimistic and lock-only alternatives |
| 8: RL-02/03 | Verified | Five baseline/golden seeds, cross-process replay/crash checks, eight negative controls each |
| 9: outbox | Verified local | Multiple workers, provider errors, lease expiry/budget, lost ACK, dedupe |
| 10: rich domain | Partial | Beneficiaries + UTC user/account limits + admin investigation/re-drive tested; no risk-review queue or full audit-search/export UI |
| 11: operations/telemetry | Partial | Eleven scenarios, runbooks, local traces/logs/metrics; collector/dashboard configs supplied but not executed; no all-incident catalog completion |
| 12: advanced tasks/performance | Partial | 1k history + controlled measured HTTP profile; RL-04–10 and 10k/100k profiles not published |
| 13: operator UI | Deferred optional | Swagger + CLI demo; no React/Playwright product UI claim |
| 14: hardening | Partial | Locked audit, leak guard, logical restore + digests; no remote CI, production deployment, external review, HA/PITR or complete release certification |

Intentional refinements: fewer cohesive modules than illustrative SRS tree; explicit SQLAlchemy SQL instead of one-implementation repository interfaces; synchronous terminal transfer insert instead of persisted PENDING; JSON reconciliation findings stored inside immutable run report rather than separate finding rows. Journal/owner/replay semantics remain tested.
The local core tag predates optional 0002 limits. Challenges pin that exact correct base, not moving HEAD. Golden fidelity and broad adjacent behavior are independently checked; full app suite is run on reference app, not repeated inside every task container.
