# Deadlock And Retry Storm
Signals: SQLSTATE 40P01, 40001, 55P03 or retry metric rise.

Read-only diagnostics:
```sh
docker compose logs --tail=100 api worker
docker compose exec -T db psql -U lab_owner -d banking_lab -c "SELECT pid,pg_blocking_pids(pid),state,wait_event FROM pg_stat_activity WHERE cardinality(pg_blocking_pids(pid))>0;"
```
Decisions and remediation: Canonical UUID account locks; UTC user-limit aggregation serializes same actor. Retry whole transaction at most three attempts with jitter. Reduce load if budget exhausted.

Expected: Opposite-direction tests complete within deadlines; reconciliation clean.

Rollback/safety: Restore known-good source; keep schema compatible and preserve keys.

Follow-up: retain sanitized evidence; run make ci and relevant scenario before promotion. Destructive reset requires `make reset-demo CONFIRM=DESTROY_LOCAL_DEMO`; never use it as incident mitigation for persistent data.
