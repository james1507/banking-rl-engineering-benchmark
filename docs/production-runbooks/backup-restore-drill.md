# Backup Restore Drill
Signals: Recovery rehearsal or incident evidence preservation.

Read-only diagnostics:
```sh
docker compose logs --tail=100 api worker
docker compose exec -T db psql -U lab_owner -d banking_lab -c "SELECT count(*) FROM transfers;"
```
Decisions and remediation: Run python3 scripts/restore_drill.py. It pauses only this Compose API/worker, dumps local synthetic DB, restores new lab_test_restore_* database and compares counts/hashes plus reconciliation, then cleans target and resumes.

Expected: Actual JSON report and logical dump in ignored artifacts/backup. RPO/RTO are not production claims.

Rollback/safety: Drill never overwrites source. Logical pg_dump is not PITR/WAL archiving or HA proof.

Follow-up: retain sanitized evidence; run make ci and relevant scenario before promotion. Destructive reset requires `make reset-demo CONFIRM=DESTROY_LOCAL_DEMO`; never use it as incident mitigation for persistent data.
