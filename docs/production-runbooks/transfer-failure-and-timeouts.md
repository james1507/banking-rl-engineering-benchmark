# Transfer Failure And Timeouts
Signals: 503, client timeout or missing transfer response.

Read-only diagnostics:
```sh
docker compose logs --tail=100 api worker
docker compose exec -T db psql -U lab_owner -d banking_lab -c "SELECT id,status,response_status,transfer_id FROM idempotency_records ORDER BY created_at DESC LIMIT 10;"
```
Decisions and remediation: Inspect idempotency and transfer under same actor/key; repeat identical body/key. Never infer rollback from timeout. If DB unavailable, preserve request intent and retry after recovery.

Expected: Original response/status replayed; exactly one transfer and two postings.

Rollback/safety: Stop newly generated attempts; no blind different-key retry.

Follow-up: retain sanitized evidence; run make ci and relevant scenario before promotion. Destructive reset requires `make reset-demo CONFIRM=DESTROY_LOCAL_DEMO`; never use it as incident mitigation for persistent data.
