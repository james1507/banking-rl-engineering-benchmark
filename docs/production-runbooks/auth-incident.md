# Auth Incident
Signals: Refresh replay, suspicious 401/429 or unauthorized resource attempts.

Read-only diagnostics:
```sh
docker compose logs --tail=100 api worker
docker compose exec -T db psql -U lab_owner -d banking_lab -c "SELECT action,outcome,count(*) FROM audit_events WHERE action IN ('REFRESH_REPLAY','LOGIN','LOGOUT') GROUP BY action,outcome;"
```
Decisions and remediation: Logout revokes refresh family; reuse also revokes family under user lock. Disable compromised synthetic user through controlled owner procedure. No tokens/passwords in diagnostics.

Expected: Reused rotated token and successor both rejected; foreign resource remains masked 404.

Rollback/safety: Bearer access expires after 15 min; no instant per-access-session revocation, MFA or public account recovery system.

Follow-up: retain sanitized evidence; run make ci and relevant scenario before promotion. Destructive reset requires `make reset-demo CONFIRM=DESTROY_LOCAL_DEMO`; never use it as incident mitigation for persistent data.
