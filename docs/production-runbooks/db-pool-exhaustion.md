# Db Pool Exhaustion
Signals: 503 TRANSIENT_DATABASE_ERROR, high latency, exhausted pool.

Read-only diagnostics:
```sh
docker compose logs --tail=100 api worker
docker compose exec -T db psql -U lab_owner -d banking_lab -c "SELECT state,wait_event_type,wait_event,count(*) FROM pg_stat_activity GROUP BY 1,2,3;"
```
Decisions and remediation: Bound client concurrency; inspect blockers and session lifetimes. Pool size is eight/no overflow, pool wait 3s, statement 10s, lock 3s. Do not increase pool blindly.

Expected: After held connection released, same-key retry succeeds; no partial effect.

Rollback/safety: Roll back leaking release; restart API gracefully only after blocking cause understood.

Follow-up: retain sanitized evidence; run make ci and relevant scenario before promotion. Destructive reset requires `make reset-demo CONFIRM=DESTROY_LOCAL_DEMO`; never use it as incident mitigation for persistent data.
