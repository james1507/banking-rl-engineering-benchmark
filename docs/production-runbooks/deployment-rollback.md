# Deployment Rollback
Signals: Readiness schema mismatch or transfer error regression.

Read-only diagnostics:
```sh
docker compose logs --tail=100 api worker
docker compose exec -T db psql -U lab_owner -d banking_lab -c "SELECT version_num FROM alembic_version;"
```
Decisions and remediation: Apply migrations before code. 0002 is additive; pinned 0001 core remains compatible with extra table/indexes. Current app readiness requires 0002. Roll back app only to compatible code.

Expected: /health/ready returns 200 with expected revision; same-key replay still exact.

Rollback/safety: Alembic destructive downgrade intentionally refused. Restore new DB for destructive rehearsal; never drop money history.

Follow-up: retain sanitized evidence; run make ci and relevant scenario before promotion. Destructive reset requires `make reset-demo CONFIRM=DESTROY_LOCAL_DEMO`; never use it as incident mitigation for persistent data.
