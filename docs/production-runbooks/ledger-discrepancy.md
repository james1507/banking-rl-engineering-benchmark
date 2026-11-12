# Ledger Discrepancy
Signals: Reconciliation HIGH finding or cache/ledger mismatch.

Read-only diagnostics:
```sh
docker compose logs --tail=100 api worker
docker compose exec -T db psql -U lab_owner -d banking_lab -c "SELECT a.id,a.balance_minor,coalesce(sum(p.signed_amount_minor),0) ledger FROM accounts a LEFT JOIN ledger_postings p ON p.account_id=a.id GROUP BY a.id HAVING a.balance_minor<>coalesce(sum(p.signed_amount_minor),0);"
```
Decisions and remediation: Pause API writes using docker compose stop api if financial corruption suspected. Preserve dump/logs. Run make reconcile. Compare projection and immutable journal; no automatic repair.

Expected: Clean data returns zero rows; isolated INC-05 returns drift finding.

Rollback/safety: Fix code; review repair separately. Correct immutable history through approved compensating postings, never editing ledger.

Follow-up: retain sanitized evidence; run make ci and relevant scenario before promotion. Destructive reset requires `make reset-demo CONFIRM=DESTROY_LOCAL_DEMO`; never use it as incident mitigation for persistent data.
