# Three reproducible walkthroughs
All incidents are simulated. No claim of having operated this system in a real bank.

## A: Concurrent transfers (6–8 min)
```sh
make up seed
make scenario SCENARIO=INC-01
make challenge TASK=RL-01 MODE=baseline
make challenge TASK=RL-01 MODE=golden
make challenge TASK=RL-01 MODE=alternative
make invariants
```
Seed CLI prints exact Alice/Bob/treasury UUIDs; pinned fixture IDs are documented in seed evidence. Inspect src/banking_lab/application/transfers.py and infrastructure/repository.py, then solution/golden.patch. Independent benchmark uses randomized UUIDs, balances and separate API processes; reports record seed 101. Read counts/assertion failures in artifacts/challenges/RL-01-*.json and scenario logs. A process-local mutex cannot coordinate different APIs; database account locks protect the shared state. Canonical UUID order prevents opposite-direction lock cycles, while whole-transaction retries cover classified transient failures. Current P1 additionally serializes actor requests for user-wide quotas; task pins earlier correct P0 core so stale-account defects remain observable. Reconciliation checks money independently rather than trusting HTTP success.

## B: Response lost after commit (5–7 min)
```sh
python3 scripts/demo.py
make scenario SCENARIO=INC-02
make challenge TASK=RL-02 MODE=baseline
make challenge TASK=RL-02 MODE=golden
```
Demo output includes real transfer ID and exact replay result, never token. External verifier kills candidate at AFTER_SQL_COMMIT_BEFORE_HTTP_RESPONSE, waits for restart, and retries from other process. Inspect record through SQL:
```sh
docker compose exec -T db psql -U lab_owner -d banking_lab -c "SELECT id,status,response_status,transfer_id FROM idempotency_records ORDER BY created_at DESC LIMIT 5;"
```
A timeout means client lacks outcome, not that server rolled back. Unique actor/operation/key and canonical request hash bind one financial intent. Response and money commit atomically, so retry recovers original transfer/status/body. Different payload under same key returns stable 409. A terminal insufficient-funds rejection also replays after later funding. Transport correlation ID must never become idempotency namespace.

## C: Incident recovery (6–8 min)
```sh
make scenario SCENARIO=INC-07
make scenario SCENARIO=INC-08
python3 scripts/restore_drill.py
make invariants
```
Read actual worker retry/published JSON in artifacts/scenarios logs; correlation spans propagate through outbox payload. Inspect operational state:
```sh
docker compose exec -T db psql -U lab_owner -d banking_lab -c "SELECT status,count(*),max(attempt_count) FROM outbox_events GROUP BY status;"
docker compose exec -T db psql -U lab_owner -d banking_lab -c "SELECT (SELECT count(*) FROM inbox_receipts) receipts,(SELECT count(*) FROM notification_effects) effects;"
```
Money commits before any provider attempt. A worker can lose acknowledgement after receiver commits, so exactly-once network delivery is not assumed. Atomic inbox receipt plus effect makes repeated attempts harmless. Lease expiry recovers crashed worker; token fencing rejects stale acknowledgement. Retry budget and dead-letter require controlled operator re-drive after recovery. Restore drill uses a new database, compares ledger/replay digests, reconciles, and leaves original data intact.

## Concise engineering answers
- Correctness: one SQL unit of work, strict amounts, owner checks, ordered locks, paired immutable journal, deferred constraints and independent verifier.
- Commit then crash: retry same body/key, read persisted original result.
- Isolation: READ COMMITTED with locked re-read; optimistic CAS alternative also verified.
- Drift: preserve evidence, pause unsafe writes if needed, compare cache/journal/status; no silent destructive repair.
- Event semantics: at-least-once attempts, one deduplicated fake consumer effect.
- Deployment: additive 0002 before new app; readiness requires compatible revision; no destructive downgrade in live data.
- Verifier fairness: randomized deterministic fixtures, adjacent healthy paths, negative controls and true alternate implementation; initial PID weakness preserved in evidence and fixed.
- Performance: report measured local samples and actual EXPLAIN, never extrapolate laptop tests to production SLA.
