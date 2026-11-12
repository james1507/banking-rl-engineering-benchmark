# Outbox Backlog
Signals: Pending age grows, DEAD rows, provider retry logs.

Read-only diagnostics:
```sh
docker compose logs --tail=100 api worker
docker compose exec -T db psql -U lab_owner -d banking_lab -c "SELECT status,count(*),max(attempt_count),min(created_at) FROM outbox_events GROUP BY status;"
```
Decisions and remediation: Inspect fake provider mode and worker logs. Restart worker after provider recovers. 30s leases reclaim crashed work; lease token fences stale ACK. Admin retry endpoint only DEAD events, audited.

Expected: One notification_effect per event and one inbox receipt; money unchanged.

Rollback/safety: Stop faulty worker; events remain durable. Do not delete pending rows or reverse money for notification errors.

Follow-up: retain sanitized evidence; run make ci and relevant scenario before promotion. Destructive reset requires `make reset-demo CONFIRM=DESTROY_LOCAL_DEMO`; never use it as incident mitigation for persistent data.
